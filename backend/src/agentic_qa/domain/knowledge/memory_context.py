"""What memory hands to a planner.

Mirrors `contracts/memory-context.schema.json`. Everything here exists to make one
thing impossible: memory arriving in a prompt as a bare assertion. Each item carries
where it came from, how well it has held up, whether it still applies, and why it was
chosen — so a planner (and a human reading the trace afterwards) can weigh it instead
of believing it.

Bounded on purpose. Dumping a whole subgraph into a prompt costs the tokens the memory
was supposed to save and buries the two items that mattered.

Ranking is deterministic and lives here rather than in a query. The order memory is
offered in changes what the agent does, so it has to be reproducible from the data
alone: the same candidates and the same scope must always produce the same context,
or a warm-vs-cold benchmark measures noise.
"""

import math
from dataclasses import dataclass
from datetime import datetime

from agentic_qa.domain.knowledge.compatibility import (
    Compatibility,
    MemoryScope,
    compatibility_of,
)
from agentic_qa.domain.knowledge.experience import (
    ACTIONABLE_STATUSES,
    KnowledgeExperienceCandidate,
    summarize,
)

SCHEMA_VERSION = "roveqa.memory-context.v1"

MAX_CONTEXT_ITEMS = 50
"""The contract's ceiling. The default below is far lower on purpose."""

DEFAULT_CONTEXT_ITEMS = 8
"""Few, high-value items. Memory that fills the context window has spent the budget
it was meant to save."""

FRESHNESS_HALF_LIFE_DAYS = 30.0
"""How fast unverified knowledge decays in the ranking.

Not an expiry: an old fact is not wrong, it is just less recently checked. Decay makes
the agent prefer knowledge somebody confirmed lately, without discarding anything.
"""

_COMPATIBILITY_WEIGHT = {
    Compatibility.EXACT: 1.0,
    Compatibility.COMPATIBLE: 0.8,
    # Usable, but only after checking preconditions — so it should lose to anything
    # that needs no check at all.
    Compatibility.REVALIDATE: 0.4,
    Compatibility.INCOMPATIBLE: 0.0,
}

_OBSERVED_WEIGHT = 1.0
_MODEL_DERIVED_WEIGHT = 0.6
"""A hypothesis is worth offering and worth ranking below an observation of equal
reliability. The planner is told which is which regardless; this only decides order."""


@dataclass(frozen=True)
class MemoryItem:
    memory_id: str
    candidate_id: str
    kind: str
    summary: str
    observed: bool
    model_derived: bool
    reliability: float
    freshness: float
    compatibility: Compatibility
    source_run_id: str
    valid_from: datetime
    valid_to: datetime | None = None
    last_verified_at: datetime | None = None
    evidence_set_id: str | None = None
    selection_reason: str = ""
    """Why this item is in the context. Written for a human reading a trace who is
    asking why the agent believed something."""

    @property
    def score(self) -> float:
        """Deterministic rank. No model is consulted about what memory is worth."""
        return round(
            _COMPATIBILITY_WEIGHT[self.compatibility]
            * (_OBSERVED_WEIGHT if self.observed else _MODEL_DERIVED_WEIGHT)
            * self.reliability
            # Freshness scales only half the weight. Age lowers an item's priority;
            # it never removes something that has held up and was never contradicted.
            * (0.5 + 0.5 * self.freshness),
            6,
        )

    @property
    def requires_revalidation(self) -> bool:
        return self.compatibility is Compatibility.REVALIDATE


@dataclass(frozen=True)
class MemoryContext:
    query_id: str
    project_id: str
    environment_id: str
    items: tuple[MemoryItem, ...] = ()

    @property
    def is_cold(self) -> bool:
        """No usable memory. The run explores as if it were the first one."""
        return not self.items


def freshness_at(moment: datetime, *, last_verified_at: datetime | None) -> float:
    """1.0 when just verified, halving every `FRESHNESS_HALF_LIFE_DAYS`.

    Reaches zero in practice after enough half-lives, which is fine: `score` only
    lets freshness scale the second half of an item's weight, so knowledge that was
    verified once and never contradicted keeps its floor rather than disappearing.
    Making decay alone able to eliminate an item would mean a long-stable fact
    eventually ranked below nothing at all.
    """
    if last_verified_at is None:
        return 0.0
    age_days = max((moment - last_verified_at).total_seconds() / 86400.0, 0.0)
    return round(math.pow(0.5, age_days / FRESHNESS_HALF_LIFE_DAYS), 6)


def build_item(
    candidate: KnowledgeExperienceCandidate,
    *,
    compatibility: Compatibility,
    now: datetime,
) -> MemoryItem:
    reason = _selection_reason(candidate, compatibility)
    return MemoryItem(
        # The candidate is the memory: one durable row, one identity, so feedback
        # about what the planner used lands back on the thing it used.
        memory_id=candidate.candidate_id,
        candidate_id=candidate.candidate_id,
        kind=candidate.kind.value,
        summary=summarize(candidate),
        observed=candidate.observed,
        model_derived=candidate.model_derived,
        reliability=candidate.quality.reliability,
        freshness=freshness_at(now, last_verified_at=candidate.quality.last_verified_at),
        compatibility=compatibility,
        source_run_id=candidate.provenance.source_run_id,
        valid_from=candidate.validity.valid_from,
        valid_to=candidate.validity.valid_to,
        last_verified_at=candidate.quality.last_verified_at,
        evidence_set_id=candidate.provenance.evidence_set_id,
        selection_reason=reason,
    )


def select(
    candidates: list[KnowledgeExperienceCandidate],
    *,
    scope: MemoryScope,
    query_id: str,
    now: datetime,
    limit: int = DEFAULT_CONTEXT_ITEMS,
) -> MemoryContext:
    """Filter, rank and bound. The last gate before memory reaches a prompt.

    Scope is re-checked here even though retrieval already filtered it in SQL. The
    duplication is deliberate: this function is also fed by graph traversal and by
    rebuild paths, and a single missing filter in any one of them is a cross-project
    leak. Checking cheaply in the one place everything converges is worth more than
    the elegance of trusting the caller.
    """
    bound = max(0, min(limit, MAX_CONTEXT_ITEMS))

    items: list[MemoryItem] = []
    for candidate in candidates:
        if candidate.status not in ACTIONABLE_STATUSES:
            # Only what has earned a status a planner may act on. Everything else is
            # history, and history in a prompt reads as advice.
            continue
        verdict = compatibility_of(candidate, scope, now=now)
        if verdict is Compatibility.INCOMPATIBLE:
            continue
        items.append(build_item(candidate, compatibility=verdict, now=now))

    # Ties broken by candidate id so the same inputs always produce the same order —
    # a benchmark comparing warm against cold must not measure dictionary ordering.
    items.sort(key=lambda item: (-item.score, item.candidate_id))
    return MemoryContext(
        query_id=query_id,
        project_id=scope.project_id,
        environment_id=scope.environment_id,
        items=tuple(items[:bound]),
    )


def _selection_reason(candidate: KnowledgeExperienceCandidate, compatibility: Compatibility) -> str:
    source = "observed" if candidate.observed and not candidate.model_derived else "model-derived"
    detail = (
        f"{source} {candidate.kind.value}, {candidate.status.value}, "
        f"{candidate.quality.support_count} support, "
        f"reliability {candidate.quality.reliability:.2f}, {compatibility.value}"
    )
    if compatibility is Compatibility.REVALIDATE:
        detail += " — preconditions must be verified before acting"
    return detail
