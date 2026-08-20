"""What later runs do to knowledge they used.

Consolidation is only half a learning system. Without these transitions, memory grows
forever and nothing in it can ever be found to be wrong — which is worse than no
memory, because the agent acts on it.
"""

from datetime import UTC, datetime, timedelta

import pytest

from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.domain.knowledge.experience import (
    CandidateKind,
    CandidateStatus,
    KnowledgeExperienceCandidate,
    Provenance,
    Quality,
    Validity,
)
from agentic_qa.domain.knowledge.feedback import (
    FeedbackKind,
    MemoryFeedback,
    apply_feedback,
)

NOW = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)
LATER = NOW + timedelta(hours=1)


def candidate(**overrides: object) -> KnowledgeExperienceCandidate:
    defaults: dict[str, object] = {
        "candidate_id": "cand-1",
        "project_id": "proj-1",
        "environment_id": "staging",
        "kind": CandidateKind.PLAYBOOK,
        "observed": True,
        "model_derived": False,
        "created_at": NOW,
        "provenance": Provenance(source_run_id="run-1"),
        "validity": Validity(valid_from=NOW),
        "payload": {"criterion_id": "ac-1", "summary": "log in through the header form"},
        "status": CandidateStatus.TRUSTED,
        "quality": Quality(support_count=6, success_count=6, last_verified_at=NOW),
    }
    defaults.update(overrides)
    return KnowledgeExperienceCandidate(**defaults)  # type: ignore[arg-type]


def feedback(kind: FeedbackKind, **overrides: object) -> MemoryFeedback:
    defaults: dict[str, object] = {
        "feedback_id": "fb-1",
        "candidate_id": "cand-1",
        "run_id": "run-2",
        "kind": kind,
        "created_at": LATER,
        "observed": True,
        "episode_id": "ep-0",
    }
    defaults.update(overrides)
    return MemoryFeedback(**defaults)  # type: ignore[arg-type]


class TestOnlyVerifiedOutcomesMoveTheNumbers:
    def test_a_model_conclusion_is_recorded_but_not_counted(self) -> None:
        # Otherwise a model that likes its own suggestions can promote them.
        original = candidate(
            status=CandidateStatus.CANDIDATE, quality=Quality(support_count=1, success_count=1)
        )
        unchanged = apply_feedback(
            original, feedback(FeedbackKind.SUCCESS, observed=False), now=LATER
        )
        assert unchanged == original

    def test_a_verified_success_counts(self) -> None:
        original = candidate(
            status=CandidateStatus.CANDIDATE, quality=Quality(support_count=1, success_count=1)
        )
        updated = apply_feedback(original, feedback(FeedbackKind.SUCCESS), now=LATER)

        assert updated.quality.success_count == 2
        assert updated.status is CandidateStatus.PROMOTED
        assert updated.quality.last_verified_at == LATER

    def test_a_model_doubting_a_fact_cannot_invalidate_it(self) -> None:
        trusted = candidate()
        still_trusted = apply_feedback(
            trusted, feedback(FeedbackKind.CONTRADICTION, observed=False), now=LATER
        )
        assert still_trusted.status is CandidateStatus.TRUSTED


class TestLosingTrustIsEasierThanGainingIt:
    def test_one_verified_contradiction_invalidates_even_a_trusted_playbook(self) -> None:
        # Promotion took six agreeing runs; being false once is enough. Acting on
        # something false corrupts the next run, while re-learning costs one run.
        invalidated = apply_feedback(candidate(), feedback(FeedbackKind.CONTRADICTION), now=LATER)

        assert invalidated.status is CandidateStatus.INVALIDATED
        assert invalidated.quality.contradiction_count == 1

    def test_a_single_failure_does_not_invalidate_something_well_supported(self) -> None:
        # "It did not work this time" is not "it is false".
        after = apply_feedback(candidate(), feedback(FeedbackKind.FAILURE), now=LATER)

        assert after.status is CandidateStatus.TRUSTED
        assert after.quality.failure_count == 1

    def test_repeated_failure_stops_it_being_offered_without_declaring_it_false(self) -> None:
        unreliable = candidate(
            status=CandidateStatus.PROMOTED,
            quality=Quality(support_count=4, success_count=2, failure_count=2),
        )
        after = apply_feedback(unreliable, feedback(FeedbackKind.FAILURE), now=LATER)

        # Back to `candidate`, not `invalidated`: still recoverable, so later
        # verified successes can promote it again.
        assert after.status is CandidateStatus.CANDIDATE
        assert not after.is_actionable

    def test_something_invalidated_is_not_promoted_back_by_a_success(self) -> None:
        # Re-validation is a decision, not a side effect of one run getting lucky.
        invalidated = candidate(status=CandidateStatus.INVALIDATED)
        after = apply_feedback(invalidated, feedback(FeedbackKind.SUCCESS), now=LATER)

        assert after.status is CandidateStatus.INVALIDATED
        # The evidence is still recorded, so a human can see the disagreement.
        assert after.quality.success_count == 7


class TestContextAndSafetyAreNotReliability:
    def test_stale_knowledge_is_invalidated_not_marked_unreliable(self) -> None:
        # The page changed. The knowledge may well have been true; counting it as a
        # failure would blame the memory for the application being redesigned.
        after = apply_feedback(candidate(), feedback(FeedbackKind.STALE), now=LATER)

        assert after.status is CandidateStatus.INVALIDATED
        assert after.quality.failure_count == 0

    def test_unsafe_knowledge_is_rejected_whatever_its_support(self) -> None:
        after = apply_feedback(candidate(), feedback(FeedbackKind.UNSAFE), now=LATER)

        assert after.status is CandidateStatus.REJECTED
        assert not after.is_actionable

    def test_a_rejected_candidate_stays_rejected_after_a_success(self) -> None:
        rejected = candidate(status=CandidateStatus.REJECTED)
        after = apply_feedback(rejected, feedback(FeedbackKind.SUCCESS), now=LATER)
        assert after.status is CandidateStatus.REJECTED


def test_feedback_for_another_candidate_is_refused() -> None:
    # A mismatched id would silently move the wrong candidate's numbers.
    with pytest.raises(InvalidEntityError):
        apply_feedback(
            candidate(), feedback(FeedbackKind.SUCCESS, candidate_id="cand-other"), now=LATER
        )


def test_feedback_must_name_the_run_that_produced_it() -> None:
    with pytest.raises(InvalidEntityError):
        feedback(FeedbackKind.SUCCESS, run_id="")
