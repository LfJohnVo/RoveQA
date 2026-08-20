"""What a candidate is allowed to become.

These are the rules that decide what a later run will act on, so each test names the
failure it prevents rather than the method it calls.
"""

from datetime import UTC, datetime, timedelta

import pytest

from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.domain.knowledge.experience import (
    MIN_SUPPORT_TO_TRUST,
    CandidateKind,
    CandidateStatus,
    KnowledgeExperienceCandidate,
    Provenance,
    Quality,
    Validity,
    summarize,
)

NOW = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)


def candidate(**overrides: object) -> KnowledgeExperienceCandidate:
    defaults: dict[str, object] = {
        "candidate_id": "cand-1",
        "project_id": "proj-1",
        "environment_id": "staging",
        "kind": CandidateKind.ACCEPTANCE_FACT,
        "observed": True,
        "model_derived": False,
        "created_at": NOW,
        "provenance": Provenance(source_run_id="run-1"),
        "validity": Validity(valid_from=NOW),
        "payload": {"criterion_id": "ac-1", "summary": "checkout reaches confirmation"},
    }
    defaults.update(overrides)
    return KnowledgeExperienceCandidate(**defaults)  # type: ignore[arg-type]


def test_a_candidate_from_nowhere_is_refused() -> None:
    with pytest.raises(InvalidEntityError):
        candidate(observed=False, model_derived=False)


def test_provenance_without_a_run_is_refused() -> None:
    # Memory that cannot name where it came from cannot be audited or invalidated.
    with pytest.raises(InvalidEntityError):
        Provenance(source_run_id="")


class TestModelDerivedNeverBecomesFact:
    """The single rule that keeps a guess from turning into something acted upon."""

    def test_it_cannot_be_constructed_as_trusted(self) -> None:
        with pytest.raises(InvalidEntityError):
            candidate(observed=False, model_derived=True, status=CandidateStatus.TRUSTED)

    def test_repetition_stops_at_promoted(self) -> None:
        # Overwhelming support: everything an observed candidate would need to be
        # trusted, and then some.
        hypothesis = candidate(
            observed=False,
            model_derived=True,
            quality=Quality(
                support_count=MIN_SUPPORT_TO_TRUST * 10,
                success_count=MIN_SUPPORT_TO_TRUST * 10,
                last_verified_at=NOW,
            ),
        )
        assert hypothesis.promoted().status is CandidateStatus.PROMOTED

    def test_an_observed_candidate_with_the_same_support_is_trusted(self) -> None:
        # Same numbers, different source. Only the label separates them, which is
        # what makes it worth defending.
        observed = candidate(
            quality=Quality(
                support_count=MIN_SUPPORT_TO_TRUST * 10,
                success_count=MIN_SUPPORT_TO_TRUST * 10,
                last_verified_at=NOW,
            )
        )
        assert observed.promoted().status is CandidateStatus.TRUSTED


class TestPromotion:
    def test_one_sighting_is_not_enough(self) -> None:
        once = candidate(quality=Quality(support_count=1, success_count=1))
        assert once.promoted().status is CandidateStatus.CANDIDATE

    def test_a_second_independent_run_promotes(self) -> None:
        twice = candidate(quality=Quality(support_count=2, success_count=2))
        assert twice.promoted().status is CandidateStatus.PROMOTED

    def test_support_alone_does_not_trust_something_that_keeps_failing(self) -> None:
        unreliable = candidate(
            quality=Quality(
                support_count=MIN_SUPPORT_TO_TRUST + 5, success_count=5, failure_count=5
            )
        )
        assert unreliable.promoted().status is CandidateStatus.PROMOTED

    def test_something_invalidated_is_not_promoted_again(self) -> None:
        with pytest.raises(InvalidEntityError):
            candidate(status=CandidateStatus.INVALIDATED).promoted()


class TestReliability:
    def test_no_evidence_is_zero_not_one(self) -> None:
        # An unproven claim must not start out looking perfect: ranking would put it
        # above everything that has actually been tested.
        assert Quality().reliability == 0.0

    def test_a_contradiction_counts_double(self) -> None:
        # A failure means "it did not work this time"; a contradiction means "this is
        # false". Weighing them the same would let contradicted knowledge survive.
        failed = Quality(success_count=3, failure_count=1)
        contradicted = Quality(success_count=3, contradiction_count=1)
        assert contradicted.reliability < failed.reliability


class TestIdentity:
    def test_the_same_fact_from_two_runs_shares_one_identity(self) -> None:
        first = candidate(candidate_id="cand-1", provenance=Provenance(source_run_id="run-1"))
        second = candidate(candidate_id="cand-2", provenance=Provenance(source_run_id="run-2"))
        assert first.dedup_key == second.dedup_key

    def test_an_observation_and_a_hypothesis_are_different_facts(self) -> None:
        # Folding them together would let a guess inherit an observation's support,
        # and from there its trust.
        observed = candidate()
        guessed = candidate(observed=False, model_derived=True)
        assert observed.dedup_key != guessed.dedup_key

    def test_two_playbooks_in_one_scope_are_two_facts(self) -> None:
        # Regression: a playbook names neither a criterion nor a URL, so an identity
        # built only from those made every playbook in a scope one fact — the second
        # silently absorbed the first's support instead of being stored.
        first = candidate(kind=CandidateKind.PLAYBOOK, payload={"summary": "log in via header"})
        second = candidate(kind=CandidateKind.PLAYBOOK, payload={"summary": "log in via /login"})
        assert first.dedup_key != second.dedup_key

    def test_a_different_role_is_a_different_situation(self) -> None:
        admin = candidate(validity=Validity(valid_from=NOW, role="admin"))
        guest = candidate(validity=Validity(valid_from=NOW, role="guest"))
        assert admin.dedup_key != guest.dedup_key


class TestReinforcement:
    def test_support_accumulates_across_runs(self) -> None:
        stored = candidate(quality=Quality(support_count=1, success_count=1, last_verified_at=NOW))
        later = candidate(
            candidate_id="cand-2",
            provenance=Provenance(source_run_id="run-2"),
            quality=Quality(
                support_count=1, success_count=1, last_verified_at=NOW + timedelta(hours=1)
            ),
        )

        reinforced = stored.reinforced_by(later)

        assert reinforced.quality.support_count == 2
        assert reinforced.status is CandidateStatus.PROMOTED
        # Identity and origin stay with the first sighting: later runs are evidence
        # about the fact, not replacements for it.
        assert reinforced.candidate_id == "cand-1"
        assert reinforced.provenance.source_run_id == "run-1"
        assert reinforced.quality.last_verified_at == NOW + timedelta(hours=1)

    def test_reinforcing_a_different_fact_is_refused(self) -> None:
        with pytest.raises(InvalidEntityError):
            candidate().reinforced_by(candidate(kind=CandidateKind.ROUTE))

    def test_something_invalidated_does_not_resurrect_itself(self) -> None:
        invalidated = candidate(
            status=CandidateStatus.INVALIDATED,
            quality=Quality(support_count=9, success_count=9),
        )
        again = invalidated.reinforced_by(
            candidate(quality=Quality(support_count=1, success_count=1))
        )
        assert again.status is CandidateStatus.INVALIDATED
        # The support is still recorded — re-validation is a decision, not an accident.
        assert again.quality.support_count == 10


def test_a_summary_never_carries_the_whole_payload() -> None:
    # The summary is what crosses into a prompt; the payload is what stays in the
    # database. Bounding it here keeps page content out of the context window.
    wordy = candidate(payload={"summary": "x" * 10_000})
    with pytest.raises(InvalidEntityError):
        summarize(wordy)


def test_expiry_is_a_question_about_a_moment() -> None:
    validity = Validity(valid_from=NOW, valid_to=NOW + timedelta(days=1))
    assert not validity.is_expired_at(NOW)
    assert validity.is_expired_at(NOW + timedelta(days=2))
