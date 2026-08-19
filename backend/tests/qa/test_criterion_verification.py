"""The verification pipeline: deterministic first, model last, and the line between them.

These drive the real service against the browser and model *ports*, with doubles that
behave the way the real adapters do, so what is being tested is the rule — not the
plumbing.
"""

from dataclasses import dataclass, field

import pytest

from agentic_qa.application.ports.browser import ActionOutcome
from agentic_qa.application.ports.models import (
    CriterionJudgement,
    JudgementRequest,
    ModelInvocation,
)
from agentic_qa.application.services.criterion_verification import verify_criteria
from agentic_qa.application.services.guarded_browser import (
    ActionDeniedError,
    GuardedBrowserGateway,
)
from agentic_qa.domain.browser.actions import BrowserAction
from agentic_qa.domain.browser.policy_guard import PolicyDecision, PolicyViolation
from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.domain.projects.run_policy import RunPolicy
from agentic_qa.domain.qa.test_plan import PlanStep, PlanStepType
from agentic_qa.domain.qa.verification import (
    CriterionOutcome,
    CriterionResult,
    FailureKind,
)
from tests.fakes.agent import ScriptedModelGateway


@dataclass
class PageDouble:
    """A page whose text is known, so a deterministic check has something real to check."""

    text: str = "Order #1234 confirmed"
    url: str = "http://target.test/confirmation"
    checked: list[str] = field(default_factory=list)

    async def execute(self, action: BrowserAction) -> ActionOutcome:
        expected = action.value or ""
        self.checked.append(expected)
        return ActionOutcome(succeeded=expected in self.text, current_url=self.url)

    async def capture_screenshot(self) -> bytes:
        return b"fake-png-bytes"

    async def current_url(self) -> str | None:
        return self.url

    async def aclose(self) -> None:
        return None


def assertion(criterion_id: str, description: str) -> PlanStep:
    return PlanStep(
        step_id=f"assert-{criterion_id}",
        type=PlanStepType.ASSERTION,
        description=description,
        criterion_id=criterion_id,
    )


async def test_a_hint_makes_the_result_deterministic() -> None:
    browser = PageDouble()
    model = ScriptedModelGateway()

    results = await verify_criteria(
        (assertion("ac-1", "the confirmation shows an order number"),),
        browser=browser,
        model=model,
        hints={"ac-1": "Order #"},
    )

    assert results[0].outcome is CriterionOutcome.MET
    assert results[0].model_derived is False
    assert browser.checked == ["Order #"]
    assert model.judged == [], "a deterministic check must not consult the model"


async def test_a_failed_deterministic_check_is_a_product_defect() -> None:
    browser = PageDouble(text="Something went wrong")

    results = await verify_criteria(
        (assertion("ac-1", "the confirmation shows an order number"),),
        browser=browser,
        model=ScriptedModelGateway(),
        hints={"ac-1": "Order #"},
    )

    assert results[0].outcome is CriterionOutcome.NOT_MET
    assert results[0].failure_kind is FailureKind.PRODUCT
    assert results[0].is_product_defect


async def test_without_a_hint_the_model_judges_and_is_labelled() -> None:
    model = ScriptedModelGateway(judgements={"the cart is empty": True})

    results = await verify_criteria(
        (assertion("ac-1", "the cart is empty"),),
        browser=PageDouble(),
        model=model,
        hints={},
    )

    assert results[0].outcome is CriterionOutcome.MET
    assert results[0].model_derived is True
    assert "model judgement" in results[0].observation
    assert model.judged == ["the cart is empty"]


async def test_a_model_saying_no_does_not_accuse_the_product() -> None:
    """It is recorded as unmet with an unknown cause, which keeps the run inconclusive."""
    model = ScriptedModelGateway(judgements={"the cart is empty": False})

    results = await verify_criteria(
        (assertion("ac-1", "the cart is empty"),),
        browser=PageDouble(),
        model=model,
        hints={},
    )

    assert results[0].outcome is CriterionOutcome.NOT_MET
    assert results[0].failure_kind is FailureKind.UNKNOWN
    assert results[0].is_product_defect is False


async def test_a_model_that_cannot_tell_leaves_the_criterion_unverified() -> None:
    results = await verify_criteria(
        (assertion("ac-1", "the cart is empty"),),
        browser=PageDouble(),
        model=ScriptedModelGateway(),  # nothing scripted -> unclear
        hints={},
    )

    assert results[0].outcome is CriterionOutcome.UNVERIFIED


async def test_an_unavailable_model_is_a_model_failure_not_a_defect() -> None:
    @dataclass
    class DeadModel(ScriptedModelGateway):
        async def judge(self, request: JudgementRequest) -> CriterionJudgement:
            return CriterionJudgement(satisfied=None, failure="model unavailable: refused")

    results = await verify_criteria(
        (assertion("ac-1", "the cart is empty"),),
        browser=PageDouble(),
        model=DeadModel(),
        hints={},
    )

    assert results[0].failure_kind is FailureKind.MODEL
    assert results[0].is_product_defect is False


async def test_a_refused_check_is_reported_as_policy_not_as_a_defect() -> None:
    """A check the policy forbids says nothing about the product.

    The refusal is raised by the guard, so this drives the handler with a browser that
    raises what the guard raises, rather than staging a policy that happens to deny a
    read-only assertion today.
    """
    policy = RunPolicy(
        policy_id="policy-1",
        project_id="project-1",
        allowed_origins=("http://target.test",),
        max_duration_seconds=60,
        max_actions=10,
        max_model_calls=10,
    )

    @dataclass
    class RefusingPage(PageDouble):
        async def execute(self, action: BrowserAction) -> ActionOutcome:
            raise ActionDeniedError(
                action,
                PolicyDecision.deny(
                    PolicyViolation.DESTRUCTIVE_NOT_ALLOWED, "this policy forbids them"
                ),
            )

    results = await verify_criteria(
        (assertion("ac-1", "the order is placed"),),
        browser=GuardedBrowserGateway(RefusingPage(), policy),
        model=ScriptedModelGateway(),
        hints={"ac-1": "Order #"},
    )

    assert results[0].outcome is CriterionOutcome.NOT_MET
    assert results[0].failure_kind is FailureKind.POLICY
    assert results[0].is_product_defect is False


async def test_criteria_are_not_judged_when_the_run_never_reached_them() -> None:
    """Judging the page anyway would report whatever was on screen as the outcome."""
    browser = PageDouble()
    model = ScriptedModelGateway(judgements={"the cart is empty": True})

    results = await verify_criteria(
        (assertion("ac-1", "the cart is empty"),),
        browser=browser,
        model=model,
        hints={"ac-1": "empty"},
        goal_failure="the checkout button was never found",
    )

    assert results[0].outcome is CriterionOutcome.UNVERIFIED
    assert "never found" in results[0].observation
    assert browser.checked == [], "the page was checked after the goal failed"
    assert model.judged == []


async def test_a_model_judgement_records_which_model_and_prompt_produced_it() -> None:
    """docs/08: a hypothesis that cannot name its source is not reproducible."""

    @dataclass
    class TracedModel(ScriptedModelGateway):
        async def judge(self, request: JudgementRequest) -> CriterionJudgement:
            return CriterionJudgement(
                satisfied=False,
                reasoning="the cart still shows items",
                invocation=ModelInvocation(
                    invocation_id="inv-1", model="test-model", prompt_version="judge.v1"
                ),
            )

    results = await verify_criteria(
        (assertion("ac-1", "the cart is empty"),),
        browser=PageDouble(),
        model=TracedModel(),
        hints={},
    )

    result = results[0]
    assert result.model_derived is True
    assert result.model_invocation_id == "inv-1"
    assert result.model_name == "test-model"
    assert result.prompt_version == "judge.v1"


async def test_a_deterministic_result_names_no_model() -> None:
    """The absence is information: this result is one nobody needed a model for."""
    results = await verify_criteria(
        (assertion("ac-1", "the confirmation shows an order number"),),
        browser=PageDouble(),
        model=ScriptedModelGateway(),
        hints={"ac-1": "Order #"},
    )

    assert results[0].model_invocation_id is None
    assert results[0].prompt_version is None


def test_a_deterministic_result_cannot_claim_a_model_invocation() -> None:
    """Guarded in the domain: provenance and `model_derived` cannot disagree."""
    with pytest.raises(InvalidEntityError, match="cannot name a model invocation"):
        CriterionResult(
            criterion_id="ac-1",
            outcome=CriterionOutcome.MET,
            observation="the page contains 'Order #'",
            model_derived=False,
            model_invocation_id="inv-1",
        )
