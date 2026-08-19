"""Verdict derivation: what a run is allowed to conclude, and from what.

The rule this file exists to defend: a model's opinion never becomes a defect report.
Only a deterministic check can make a run `failed`, because only a deterministic check
produces a claim someone can reproduce without the model.
"""

import pytest

from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.domain.qa.verification import (
    CriterionOutcome,
    CriterionResult,
    FailureKind,
    derive_verdict,
)
from agentic_qa.domain.runs.run import Verdict


def met(criterion_id: str = "ac-1") -> CriterionResult:
    return CriterionResult(
        criterion_id=criterion_id,
        outcome=CriterionOutcome.MET,
        observation="the page contains 'Order #'",
    )


def not_met(
    criterion_id: str, kind: FailureKind, *, model_derived: bool = False
) -> CriterionResult:
    return CriterionResult(
        criterion_id=criterion_id,
        outcome=CriterionOutcome.NOT_MET,
        observation="the page does not contain 'Order #'",
        failure_kind=kind,
        model_derived=model_derived,
    )


def unverified(criterion_id: str) -> CriterionResult:
    return CriterionResult(
        criterion_id=criterion_id,
        outcome=CriterionOutcome.UNVERIFIED,
        observation="the run did not reach this criterion",
    )


class TestResultInvariants:
    def test_an_unmet_criterion_must_say_what_kind_of_failure(self) -> None:
        """Without a kind, the safe reading is "blame the product" — the damaging one."""
        with pytest.raises(InvalidEntityError, match="what kind of failure"):
            CriterionResult(
                criterion_id="ac-1",
                outcome=CriterionOutcome.NOT_MET,
                observation="not there",
            )

    def test_a_met_criterion_cannot_carry_a_failure_kind(self) -> None:
        with pytest.raises(InvalidEntityError, match="no failure kind"):
            CriterionResult(
                criterion_id="ac-1",
                outcome=CriterionOutcome.MET,
                observation="there",
                failure_kind=FailureKind.PRODUCT,
            )

    def test_only_a_product_failure_counts_as_a_defect(self) -> None:
        assert not_met("ac-1", FailureKind.PRODUCT).is_product_defect
        for kind in (
            FailureKind.PLAN,
            FailureKind.ENVIRONMENT,
            FailureKind.POLICY,
            FailureKind.AGENT_BUDGET,
            FailureKind.MODEL,
            FailureKind.UNKNOWN,
        ):
            assert not not_met("ac-1", kind).is_product_defect, kind


class TestVerdictDerivation:
    def test_all_criteria_met_passes(self) -> None:
        results = [met("ac-1"), met("ac-2")]

        assert derive_verdict(results, expected=["ac-1", "ac-2"]) is Verdict.PASSED

    def test_a_deterministic_product_failure_fails_the_run(self) -> None:
        results = [met("ac-1"), not_met("ac-2", FailureKind.PRODUCT)]

        assert derive_verdict(results, expected=["ac-1", "ac-2"]) is Verdict.FAILED

    def test_a_model_only_doubt_never_reports_a_defect(self) -> None:
        """The whole point: a model that says "looks wrong" leaves the run inconclusive."""
        results = [met("ac-1"), not_met("ac-2", FailureKind.UNKNOWN, model_derived=True)]

        assert derive_verdict(results, expected=["ac-1", "ac-2"]) is Verdict.INCONCLUSIVE

    def test_a_bad_plan_does_not_blame_the_product(self) -> None:
        results = [met("ac-1"), not_met("ac-2", FailureKind.PLAN)]

        assert derive_verdict(results, expected=["ac-1", "ac-2"]) is Verdict.INCONCLUSIVE

    @pytest.mark.parametrize(
        "kind",
        [FailureKind.ENVIRONMENT, FailureKind.POLICY, FailureKind.AGENT_BUDGET, FailureKind.MODEL],
    )
    def test_a_run_that_could_not_do_its_job_is_blocked(self, kind: FailureKind) -> None:
        results = [met("ac-1"), not_met("ac-2", kind)]

        assert derive_verdict(results, expected=["ac-1", "ac-2"]) is Verdict.BLOCKED

    def test_a_real_defect_is_not_hidden_by_a_blocked_looking_symptom(self) -> None:
        """Ordering matters: the finding worth having wins over the noise around it."""
        results = [not_met("ac-1", FailureKind.PRODUCT), not_met("ac-2", FailureKind.ENVIRONMENT)]

        assert derive_verdict(results, expected=["ac-1", "ac-2"]) is Verdict.FAILED

    def test_a_criterion_nobody_evaluated_is_never_silently_passed(self) -> None:
        """A missing result is the worst way to get a green run."""
        results = [met("ac-1")]

        assert derive_verdict(results, expected=["ac-1", "ac-2"]) is Verdict.INCONCLUSIVE

    def test_an_unverified_criterion_is_inconclusive(self) -> None:
        results = [met("ac-1"), unverified("ac-2")]

        assert derive_verdict(results, expected=["ac-1", "ac-2"]) is Verdict.INCONCLUSIVE

    def test_a_verdict_needs_something_to_judge(self) -> None:
        with pytest.raises(InvalidEntityError, match="at least one expected criterion"):
            derive_verdict([], expected=[])
