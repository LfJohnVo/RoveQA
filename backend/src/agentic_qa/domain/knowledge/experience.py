"""Knowledge candidates: what a run learned, durably (Knowledge bounded context).

Mirrors `contracts/knowledge-experience.schema.json`. PostgreSQL owns these rows;
the graph is a projection that can be rebuilt from them (ADR 0008), so nothing here
knows Graphiti or FalkorDB exists.

Three invariants shape the whole file, and each exists because breaking it turns a
learning system into a confidently wrong one:

**Provenance is mandatory.** A memory item that cannot name the run it came from
cannot be audited, invalidated or rebuilt. There is no constructor path without it.

**An observation and a hypothesis never merge.** A candidate is `observed` when a
deterministic check produced it and `model_derived` when a model did. The labels are
not decoration: a model-derived candidate can never reach `trusted`, because trusting
a guess is exactly how a memory poisons the runs that come after it.

**Trust is earned from verified outcomes, never asserted.** Status moves through
explicit transitions driven by recorded evidence, not by whoever constructs the object.
"""

import hashlib
import json
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from typing import Any

from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.domain.validation import require_identifier, require_text

SCHEMA_VERSION = "roveqa.knowledge-experience.v1"


class CandidateKind(StrEnum):
    ROUTE = "route"
    PAGE_STATE = "page_state"
    TRANSITION = "transition"
    PLAYBOOK = "playbook"
    FAILURE_SIGNATURE = "failure_signature"
    ACCEPTANCE_FACT = "acceptance_fact"
    API_RELATION = "api_relation"
    ROLE_CONSTRAINT = "role_constraint"
    LOCATOR_HINT = "locator_hint"


class CandidateStatus(StrEnum):
    CANDIDATE = "candidate"
    """Recorded, not yet worth acting on."""

    PROMOTED = "promoted"
    """Enough verified support to offer to a planner as a suggestion."""

    TRUSTED = "trusted"
    """Repeatedly confirmed. Still never bypasses RunPolicy or verify-before-retry."""

    INVALIDATED = "invalidated"
    """Contradicted by verified evidence, or its context no longer applies."""

    REJECTED = "rejected"
    """Refused at capture: unsafe, unusable, or nothing anyone should learn."""

    PENDING_SYNC = "pending_sync"
    """Durable here, not yet materialized in the graph.

    Part of the published contract, and never written by this system: whether a row
    reached the graph is tracked in `graph_sync_state`, not here. Overwriting a
    promotion tier with it would make an outage look like a loss of confidence — the
    graph being down says nothing about whether the knowledge is true (docs/26)."""


ACTIONABLE_STATUSES = frozenset({CandidateStatus.PROMOTED, CandidateStatus.TRUSTED})
"""Statuses retrieval may offer to a planner. Everything else is history."""


@dataclass(frozen=True)
class Provenance:
    """Where a candidate came from. Without it, nothing here can be audited."""

    source_run_id: str
    source_episode_id: str | None = None
    evidence_set_id: str | None = None
    test_plan_version: str | None = None
    model_invocation_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "source_run_id", require_identifier(self.source_run_id, field="source_run_id")
        )


@dataclass(frozen=True)
class Validity:
    """The context in which the knowledge held.

    Retrieval hard-filters on these before ranking anything: knowledge observed on
    another origin, under another policy or against another app version is not weaker
    evidence, it is evidence about something else.
    """

    valid_from: datetime
    valid_to: datetime | None = None
    app_version: str | None = None
    page_fingerprint: str | None = None
    role: str | None = None
    origin: str | None = None
    policy_id: str | None = None

    def is_expired_at(self, moment: datetime) -> bool:
        return self.valid_to is not None and self.valid_to <= moment


@dataclass(frozen=True)
class Quality:
    """Evidence counts and the reliability derived from them.

    `reliability` is computed, never set: a number somebody chose is a number that can
    disagree with the evidence beside it.
    """

    support_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    contradiction_count: int = 0
    last_verified_at: datetime | None = None

    def __post_init__(self) -> None:
        for name in ("support_count", "success_count", "failure_count", "contradiction_count"):
            if getattr(self, name) < 0:
                raise InvalidEntityError(f"{name} must not be negative")

    @property
    def reliability(self) -> float:
        """Successes against everything that went wrong, with contradictions counted
        double: a contradiction is evidence the knowledge is *false*, not merely that
        it did not work this time."""
        against = self.failure_count + 2 * self.contradiction_count
        total = self.success_count + against
        if total == 0:
            return 0.0
        return round(self.success_count / total, 4)

    def with_success(self, at: datetime) -> "Quality":
        return replace(
            self,
            success_count=self.success_count + 1,
            support_count=self.support_count + 1,
            last_verified_at=at,
        )

    def with_failure(self, at: datetime) -> "Quality":
        return replace(self, failure_count=self.failure_count + 1, last_verified_at=at)

    def with_contradiction(self, at: datetime) -> "Quality":
        return replace(self, contradiction_count=self.contradiction_count + 1, last_verified_at=at)

    def combined_with(self, other: "Quality") -> "Quality":
        """Two sightings of the same fact, added together.

        Counts add rather than replace: support is how many independent runs agreed,
        and that number is the only thing promotion is allowed to depend on.
        """
        verified_at = self.last_verified_at
        if other.last_verified_at is not None and (
            verified_at is None or other.last_verified_at > verified_at
        ):
            verified_at = other.last_verified_at
        return Quality(
            support_count=self.support_count + other.support_count,
            success_count=self.success_count + other.success_count,
            failure_count=self.failure_count + other.failure_count,
            contradiction_count=self.contradiction_count + other.contradiction_count,
            last_verified_at=verified_at,
        )


MIN_SUPPORT_TO_PROMOTE = 2
"""One observation is a coincidence. Promotion needs the app to agree twice."""

MIN_RELIABILITY_TO_TRUST = 0.9
MIN_SUPPORT_TO_TRUST = 5


@dataclass(frozen=True)
class KnowledgeExperienceCandidate:
    candidate_id: str
    project_id: str
    environment_id: str
    kind: CandidateKind
    observed: bool
    model_derived: bool
    created_at: datetime
    provenance: Provenance
    validity: Validity
    payload: dict[str, Any] = field(default_factory=dict)
    status: CandidateStatus = CandidateStatus.CANDIDATE
    quality: Quality = field(default_factory=Quality)

    def __post_init__(self) -> None:
        for name in ("candidate_id", "project_id", "environment_id"):
            object.__setattr__(self, name, require_identifier(getattr(self, name), field=name))

        if not self.observed and not self.model_derived:
            # Something with neither source is knowledge from nowhere.
            raise InvalidEntityError("a candidate must be observed, model-derived, or both")
        if self.model_derived and self.status is CandidateStatus.TRUSTED:
            # The rule the whole design rests on: a guess never becomes a fact by
            # being repeated. Only deterministic evidence can earn trust.
            raise InvalidEntityError("a model-derived candidate cannot be trusted")

    @property
    def is_actionable(self) -> bool:
        return self.status in ACTIONABLE_STATUSES

    @property
    def dedup_key(self) -> str:
        """Identity of the *fact*, so a second run that sees the same thing adds
        support instead of adding a row.

        Without one identity per fact, "how many independent runs agree" — the only
        number promotion is allowed to depend on — degenerates into "how many times
        did anything get written", and one flaky run repeated five times would look
        exactly like five runs agreeing.

        `model_derived` is part of the identity on purpose: a model's guess about a
        page and a deterministic check of the same page are two different claims that
        happen to be about the same subject. Folding them together would let a
        hypothesis inherit an observation's support and, from there, its trust.

        Context is part of it too — the same claim under a different role, app version,
        page fingerprint or policy is a claim about a different situation.
        """
        subject = (
            self.payload.get("subject")
            or self.payload.get("criterion_id")
            or self.payload.get("url")
            # A playbook names neither a criterion nor a URL, so its summary is the
            # fact. Ending the chain at "" instead would make every playbook in a
            # scope one identity, and the second one would silently absorb the first.
            or self.payload.get("summary")
            or ""
        )
        identity = json.dumps(
            [
                self.kind.value,
                self.model_derived,
                subject,
                self.validity.role,
                self.validity.app_version,
                self.validity.page_fingerprint,
                self.validity.policy_id,
            ],
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:32]
        # The kind stays readable so a human reading the table can tell rows apart
        # without recomputing hashes.
        return f"{self.kind.value}:{digest}"

    def promoted(self) -> "KnowledgeExperienceCandidate":
        """Move up as far as the recorded evidence allows, and no further."""
        if self.status in {CandidateStatus.INVALIDATED, CandidateStatus.REJECTED}:
            raise InvalidEntityError(f"a {self.status} candidate cannot be promoted")

        if (
            self.observed
            and not self.model_derived
            and self.quality.support_count >= MIN_SUPPORT_TO_TRUST
            and self.quality.reliability >= MIN_RELIABILITY_TO_TRUST
        ):
            return replace(self, status=CandidateStatus.TRUSTED)
        if self.quality.support_count >= MIN_SUPPORT_TO_PROMOTE:
            return replace(self, status=CandidateStatus.PROMOTED)
        return self

    def invalidated(self) -> "KnowledgeExperienceCandidate":
        """Contradicted or out of context. Kept, not deleted: why something stopped
        being true is worth as much as the fact was."""
        return replace(self, status=CandidateStatus.INVALIDATED)

    def rejected(self) -> "KnowledgeExperienceCandidate":
        """Unsafe or unusable. Terminal, and not a matter of degree — something that
        should never have been stored does not get to be weighed against its support."""
        return replace(self, status=CandidateStatus.REJECTED)

    def demoted(self) -> "KnowledgeExperienceCandidate":
        """Stop offering it, without declaring it false.

        Repeated failure is weaker evidence than contradiction. Sending it back to
        `candidate` keeps the door open for later verified successes instead of
        writing it off on evidence that only says "this did not work"."""
        return replace(self, status=CandidateStatus.CANDIDATE)

    def with_quality(self, quality: Quality) -> "KnowledgeExperienceCandidate":
        return replace(self, quality=quality)

    def reinforced_by(
        self, sighting: "KnowledgeExperienceCandidate"
    ) -> "KnowledgeExperienceCandidate":
        """Fold another run's sighting of the same fact into this one.

        Identity, provenance and `valid_from` stay with the first sighting — the
        stored candidate is the fact, and later runs are evidence about it rather
        than replacements for it.

        This lives here, not in the repositories, because it is the rule that decides
        what becomes trusted. Two adapters each with their own copy of it would be two
        rules that can disagree, and the one that disagrees quietly is the one that
        promotes something it should not.
        """
        if sighting.dedup_key != self.dedup_key:
            raise InvalidEntityError("a sighting of a different fact cannot reinforce this one")

        reinforced = self.with_quality(self.quality.combined_with(sighting.quality))
        if reinforced.status in {CandidateStatus.INVALIDATED, CandidateStatus.REJECTED}:
            # Support is still recorded, but something invalidated or refused does not
            # climb back on its own: resurrecting it is a re-validation decision, not a
            # side effect of being seen again.
            return reinforced
        return reinforced.promoted()


def summarize(candidate: KnowledgeExperienceCandidate) -> str:
    """One line a planner can read. Never the raw payload.

    Payloads hold captured detail; a summary is what crosses into a prompt, and
    bounding it here keeps page content out of the context window by construction.
    """
    subject = candidate.payload.get("summary") or candidate.payload.get("url") or candidate.kind
    return require_text(str(subject), field="summary", max_length=4000)
