"""Comparing what memory claims against what a run deterministically observed.

This is what makes memory self-correcting without asking a model whether its own
suggestions helped. Attribution — "the agent succeeded *because of* this item" — is
a judgement call and would have to be model-derived. A comparison is not: memory said
criterion X passes, this run checked X with a deterministic assertion and it failed.
That is verified evidence against the memory, and it needs nobody's opinion.

Only contradictions are found here, on purpose. Agreement is already counted where it
belongs: a run that re-observes a fact produces a candidate with the same identity,
and merging it adds one support. If this module also reported that agreement, one run
would vote twice — and support is meant to count independent runs.
"""

from collections.abc import Iterable, Sequence

from agentic_qa.domain.knowledge.experience import (
    CandidateKind,
    CandidateStatus,
    KnowledgeExperienceCandidate,
)
from agentic_qa.domain.qa.verification import CriterionOutcome, CriterionResult

_TERMINAL = frozenset({CandidateStatus.INVALIDATED, CandidateStatus.REJECTED})


def contradicted_by(
    candidates: Iterable[KnowledgeExperienceCandidate],
    *,
    results: Sequence[CriterionResult],
) -> list[KnowledgeExperienceCandidate]:
    """Stored knowledge this run's verified results disprove.

    A model-derived result is ignored as evidence, whichever way it points. A model
    that misjudges a page could otherwise invalidate a fact five earlier runs
    established — and losing trust is deliberately cheap, which is exactly why the
    evidence allowed to trigger it has to be deterministic.
    """
    verified = {
        result.criterion_id: result
        for result in results
        if not result.model_derived and result.outcome is not CriterionOutcome.UNVERIFIED
    }
    if not verified:
        return []

    return [
        candidate
        for candidate in candidates
        if candidate.status not in _TERMINAL and _is_contradicted(candidate, verified)
    ]


def _is_contradicted(
    candidate: KnowledgeExperienceCandidate, verified: dict[str, CriterionResult]
) -> bool:
    criterion_id = candidate.payload.get("criterion_id")
    if not isinstance(criterion_id, str):
        # Nothing this run checked speaks to it. A route the run never visited is not
        # evidence against the route.
        return False

    result = verified.get(criterion_id)
    if result is None:
        return False

    met = result.outcome is CriterionOutcome.MET
    if candidate.kind is CandidateKind.ACCEPTANCE_FACT:
        # It said the criterion holds, and a deterministic check says it does not.
        return not met
    if candidate.kind is CandidateKind.FAILURE_SIGNATURE:
        # It said the criterion fails here. It passes now — the bug is fixed, and an
        # agent still expecting the failure would waste its next run working around
        # something that no longer exists.
        return met
    return False
