"""What happens to knowledge after a later run uses it.

Consolidation writes what a run learned. This is the other half: what the *next* run
discovered about that knowledge when it acted on it. Without it, memory only ever
grows and nothing it contains can ever be found to be wrong — which is the failure
mode that makes a learning system worse than no memory at all.

Two rules govern every transition here, and both exist because breaking them lets bad
memory outlive the evidence against it:

**Only verified outcomes move reliability.** A model's opinion about whether a
playbook worked is recorded and labelled, never counted. Otherwise a model that likes
its own suggestions can promote them.

**Losing trust is easier than gaining it.** Promotion needs repeated agreement;
a single verified contradiction is enough to stop something being trusted. The costs
are asymmetric: acting on knowledge that is false wastes a run and can corrupt the
next one, while re-learning something true costs one more observation.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.domain.knowledge.experience import (
    CandidateStatus,
    KnowledgeExperienceCandidate,
)
from agentic_qa.domain.validation import require_identifier


class FeedbackKind(StrEnum):
    SUCCESS = "success"
    """The knowledge was used and the run verified it held."""

    FAILURE = "failure"
    """It was used and did not work this time. Not proof that it is false."""

    CONTRADICTION = "contradiction"
    """Verified evidence that it is false, not merely unhelpful."""

    STALE = "stale"
    """Its context no longer exists — the page, route or fingerprint changed."""

    UNSAFE = "unsafe"
    """It should never have been stored. Refused rather than demoted."""


COUNTED_KINDS = frozenset({FeedbackKind.SUCCESS, FeedbackKind.FAILURE, FeedbackKind.CONTRADICTION})
"""Kinds that move the reliability counters, and only when observed.

`stale` and `unsafe` are statements about context and safety rather than about whether
the knowledge worked, so folding them into a success ratio would mean a page that was
merely redesigned had made the old knowledge look *unreliable* instead of *outdated*.
"""


@dataclass(frozen=True)
class MemoryFeedback:
    feedback_id: str
    candidate_id: str
    run_id: str
    kind: FeedbackKind
    created_at: datetime
    observed: bool = True
    """False when a model concluded this. Recorded, labelled, and never counted."""

    episode_id: str | None = None
    """The unit of use. Two episodes using the same knowledge are two data points; a
    retried episode is one, which is what makes recording idempotent."""

    detail: str | None = None

    def __post_init__(self) -> None:
        for name in ("feedback_id", "candidate_id", "run_id"):
            object.__setattr__(self, name, require_identifier(getattr(self, name), field=name))

    @property
    def counts_toward_reliability(self) -> bool:
        return self.observed and self.kind in COUNTED_KINDS


MIN_RELIABILITY_TO_STAY_PROMOTED = 0.5
"""Below an even chance, offering knowledge to a planner costs more than it saves."""


def apply_feedback(
    candidate: KnowledgeExperienceCandidate, feedback: MemoryFeedback, *, now: datetime
) -> KnowledgeExperienceCandidate:
    """Fold one verified outcome into a candidate and re-derive its status.

    Pure and total: the caller persists whatever comes back. Keeping the decision here
    rather than in a service means every path that records feedback — an activity, an
    admin command, a rebuild — reaches the same verdict about the same evidence.
    """
    if feedback.candidate_id != candidate.candidate_id:
        raise InvalidEntityError("feedback belongs to a different candidate")

    if feedback.kind is FeedbackKind.UNSAFE:
        # Safety is not a matter of degree. Something that should never have been
        # stored is refused outright, whatever its support count says.
        return candidate.rejected()

    if feedback.kind is FeedbackKind.STALE:
        # The knowledge may well have been true; the world it described is gone.
        return candidate.invalidated()

    if not feedback.counts_toward_reliability:
        # A model's opinion is kept as a record (the row is still written) but must not
        # move the numbers a later run trusts.
        return candidate

    if feedback.kind is FeedbackKind.SUCCESS:
        reinforced = candidate.with_quality(candidate.quality.with_success(now))
        if reinforced.status in {CandidateStatus.INVALIDATED, CandidateStatus.REJECTED}:
            return reinforced
        return reinforced.promoted()

    if feedback.kind is FeedbackKind.CONTRADICTION:
        contradicted = candidate.with_quality(candidate.quality.with_contradiction(now))
        # Verified evidence that it is false. Whatever it was before, it is not that now.
        return contradicted.invalidated()

    failed = candidate.with_quality(candidate.quality.with_failure(now))
    if failed.is_actionable and failed.quality.reliability < MIN_RELIABILITY_TO_STAY_PROMOTED:
        # Repeated failures without an outright contradiction: stop offering it, but
        # keep it as a candidate rather than declaring it false on weaker evidence.
        return failed.demoted()
    return failed
