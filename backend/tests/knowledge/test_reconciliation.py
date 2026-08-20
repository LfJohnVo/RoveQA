"""What a verified run is allowed to say about stored memory.

The rule these enforce: memory is corrected by comparison, never by attribution. The
system never asks whether an item "helped" — it checks whether what the item claimed
matches what a deterministic assertion just observed.
"""

from datetime import UTC, datetime

from agentic_qa.domain.knowledge.experience import (
    CandidateKind,
    CandidateStatus,
    KnowledgeExperienceCandidate,
    Provenance,
    Quality,
    Validity,
)
from agentic_qa.domain.knowledge.reconciliation import contradicted_by
from agentic_qa.domain.qa.verification import CriterionOutcome, CriterionResult, FailureKind

NOW = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)


def candidate(
    kind: CandidateKind = CandidateKind.ACCEPTANCE_FACT,
    *,
    criterion_id: str | None = "ac-1",
    status: CandidateStatus = CandidateStatus.TRUSTED,
) -> KnowledgeExperienceCandidate:
    payload: dict[str, object] = {"summary": "checkout reaches confirmation"}
    if criterion_id is not None:
        payload["criterion_id"] = criterion_id
    return KnowledgeExperienceCandidate(
        candidate_id=f"cand-{kind.value}-{criterion_id}",
        project_id="proj-1",
        environment_id="staging",
        kind=kind,
        observed=True,
        model_derived=False,
        created_at=NOW,
        provenance=Provenance(source_run_id="run-1"),
        validity=Validity(valid_from=NOW),
        payload=payload,
        status=status,
        quality=Quality(support_count=6, success_count=6, last_verified_at=NOW),
    )


def result(
    outcome: CriterionOutcome,
    *,
    criterion_id: str = "ac-1",
    model_derived: bool = False,
) -> CriterionResult:
    return CriterionResult(
        criterion_id=criterion_id,
        outcome=outcome,
        observation="what the page showed",
        model_derived=model_derived,
        failure_kind=FailureKind.PRODUCT if outcome is CriterionOutcome.NOT_MET else None,
        model_invocation_id="inv-1" if model_derived else None,
        model_name="qwen" if model_derived else None,
    )


class TestAFactIsWithdrawnWhenTheCheckFails:
    def test_a_deterministic_failure_contradicts_a_remembered_success(self) -> None:
        found = contradicted_by([candidate()], results=[result(CriterionOutcome.NOT_MET)])
        assert [item.candidate_id for item in found] == ["cand-acceptance_fact-ac-1"]

    def test_a_deterministic_success_leaves_the_fact_alone(self) -> None:
        # Agreement is counted by merging the candidate this run produced. Recording
        # it here as well would let one run vote twice.
        assert contradicted_by([candidate()], results=[result(CriterionOutcome.MET)]) == []


class TestAFixedBugStopsBeingRemembered:
    def test_a_passing_criterion_contradicts_a_remembered_failure(self) -> None:
        # An agent still expecting the failure would spend its next run working
        # around something that no longer exists.
        signature = candidate(CandidateKind.FAILURE_SIGNATURE)
        found = contradicted_by([signature], results=[result(CriterionOutcome.MET)])
        assert found == [signature]

    def test_the_failure_still_happening_is_not_a_contradiction(self) -> None:
        signature = candidate(CandidateKind.FAILURE_SIGNATURE)
        assert contradicted_by([signature], results=[result(CriterionOutcome.NOT_MET)]) == []


class TestOnlyDeterministicEvidenceWithdrawsAnything:
    def test_a_model_judgement_cannot_invalidate_a_verified_fact(self) -> None:
        # Losing trust is deliberately cheap, which is exactly why the evidence
        # allowed to trigger it has to be something that can be reproduced.
        assert (
            contradicted_by(
                [candidate()], results=[result(CriterionOutcome.NOT_MET, model_derived=True)]
            )
            == []
        )

    def test_an_unverified_criterion_says_nothing(self) -> None:
        assert contradicted_by([candidate()], results=[result(CriterionOutcome.UNVERIFIED)]) == []

    def test_a_run_with_no_results_withdraws_nothing(self) -> None:
        assert contradicted_by([candidate()], results=[]) == []


class TestOnlyKnowledgeThisRunActuallySpokeTo:
    def test_another_criterion_is_untouched(self) -> None:
        other = candidate(criterion_id="ac-2")
        assert contradicted_by([other], results=[result(CriterionOutcome.NOT_MET)]) == []

    def test_a_route_the_run_never_visited_is_not_disproved(self) -> None:
        # Not going somewhere is not evidence that it is unreachable.
        route = candidate(CandidateKind.ROUTE, criterion_id=None)
        assert contradicted_by([route], results=[result(CriterionOutcome.NOT_MET)]) == []

    def test_something_already_invalidated_is_not_reported_again(self) -> None:
        # It would be recorded as a second contradiction on every subsequent run and
        # its reliability would keep sinking for one original fault.
        gone = candidate(status=CandidateStatus.INVALIDATED)
        assert contradicted_by([gone], results=[result(CriterionOutcome.NOT_MET)]) == []
