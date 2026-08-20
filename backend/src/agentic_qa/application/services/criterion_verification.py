"""Evaluate a plan's acceptance criteria against the page the run ended on.

The verification order from docs/06, applied literally:

1. **Deterministic first.** When the criterion carries a `verification_hint`, that hint
   is the literal the page must contain, and the browser answers yes or no. Only this
   path can conclude "the product is wrong", because only this path produces a claim
   somebody can reproduce without a model.
2. **Semantic last.** With no hint there is nothing deterministic to check, so a model
   is asked — and its answer is labelled `model_derived`. A model that says "not
   satisfied" leaves the criterion *unmet with an unknown cause*, which makes the run
   inconclusive rather than a reported defect.

That asymmetry is the point. A model's suspicion is worth surfacing and worthless as an
accusation; the first time this system blames a product for something only a model
believed, every later report gets read with suspicion.
"""

import logging

from agentic_qa.application.ports.browser import BrowserGateway
from agentic_qa.application.ports.models import JudgementRequest, ModelGateway
from agentic_qa.application.services.guarded_browser import ActionDeniedError
from agentic_qa.domain.browser.actions import BrowserAction, BrowserActionType
from agentic_qa.domain.qa.test_plan import PlanStep
from agentic_qa.domain.qa.verification import (
    CriterionOutcome,
    CriterionResult,
    FailureKind,
)

logger = logging.getLogger(__name__)

MAX_OBSERVATION_CHARS = 4000


async def verify_criteria(
    assertions: tuple[PlanStep, ...],
    *,
    browser: BrowserGateway,
    model: ModelGateway,
    hints: dict[str, str] | None = None,
    goal_failure: str | None = None,
    goal_failure_kind: FailureKind | None = None,
) -> tuple[CriterionResult, ...]:
    """Produce one result per assertion.

    `goal_failure` short-circuits everything: if the agent never completed the goal, the
    criteria were never reachable, and checking the page anyway would report whatever
    happened to be on screen as if it were the outcome of the story.

    `goal_failure_kind` is what makes that short-circuit *readable*. When the reason is
    known — the policy refused an action, the run ran out of actions, inference was
    unavailable — the criterion is `not_met` with that kind, and the run comes back
    `blocked`: it could not do its job, and it says so. Without a kind the honest answer
    is `unverified` and an inconclusive run, because "nobody knows why" is different
    from "we know why and it was not the product".
    """
    if goal_failure is not None:
        return tuple(_unreached(step, goal_failure, goal_failure_kind) for step in assertions)

    hints = hints or {}
    results: list[CriterionResult] = []
    for step in assertions:
        criterion_id = _criterion_of(step)
        hint = hints.get(criterion_id)
        if hint:
            results.append(await _check_deterministically(step, criterion_id, hint, browser))
        else:
            results.append(await _judge_semantically(step, criterion_id, browser, model))
    return tuple(results)


async def _check_deterministically(
    step: PlanStep, criterion_id: str, hint: str, browser: BrowserGateway
) -> CriterionResult:
    """The hint is the literal the page must contain. Reproducible without a model."""
    action = BrowserAction(
        type=BrowserActionType.ASSERT_TEXT,
        intent=f"verify criterion {criterion_id}",
        value=hint,
    )
    try:
        outcome = await browser.execute(action)
    except ActionDeniedError as denied:
        return CriterionResult(
            criterion_id=criterion_id,
            outcome=CriterionOutcome.NOT_MET,
            observation=f"the policy refused the check: {denied.decision.detail}",
            failure_kind=FailureKind.POLICY,
            step_id=step.step_id,
        )

    if outcome.succeeded:
        return CriterionResult(
            criterion_id=criterion_id,
            outcome=CriterionOutcome.MET,
            observation=f"the page contains {hint!r}",
            step_id=step.step_id,
        )
    return CriterionResult(
        criterion_id=criterion_id,
        outcome=CriterionOutcome.NOT_MET,
        observation=f"the page does not contain {hint!r}"
        + (f" ({outcome.detail})" if outcome.detail else ""),
        # Deterministic and reproducible, so this is a claim about the product.
        failure_kind=FailureKind.PRODUCT,
        step_id=step.step_id,
    )


async def _judge_semantically(
    step: PlanStep, criterion_id: str, browser: BrowserGateway, model: ModelGateway
) -> CriterionResult:
    observation = (await browser.current_url()) or "about:blank"
    judgement = await model.judge(
        JudgementRequest(
            criterion=step.description, observation=observation[:MAX_OBSERVATION_CHARS]
        )
    )

    if judgement.failure is not None:
        return CriterionResult(
            criterion_id=criterion_id,
            outcome=CriterionOutcome.NOT_MET,
            observation=f"no judgement could be obtained: {judgement.failure}",
            failure_kind=FailureKind.MODEL,
            model_derived=True,
            step_id=step.step_id,
        )

    # Named explicitly rather than unpacked from a dict: which field is which is
    # the kind of thing a type checker should be able to see.
    invocation = judgement.invocation
    invocation_id = invocation.invocation_id if invocation is not None else None
    model_name = invocation.model if invocation is not None else None
    prompt_version = invocation.prompt_version if invocation is not None else None

    if judgement.satisfied is True:
        return CriterionResult(
            criterion_id=criterion_id,
            outcome=CriterionOutcome.MET,
            observation=_labelled(judgement.reasoning, observation),
            model_derived=True,
            step_id=step.step_id,
            model_invocation_id=invocation_id,
            model_name=model_name,
            prompt_version=prompt_version,
        )

    if judgement.satisfied is None:
        return CriterionResult(
            criterion_id=criterion_id,
            outcome=CriterionOutcome.UNVERIFIED,
            observation=_labelled(judgement.reasoning or "the model could not tell", observation),
            model_derived=True,
            step_id=step.step_id,
            model_invocation_id=invocation_id,
            model_name=model_name,
            prompt_version=prompt_version,
        )

    # The model says no. Recorded as unmet, but the cause stays UNKNOWN: nothing
    # deterministic corroborates it, so the run ends inconclusive rather than accusing
    # the product of a defect on a model's word.
    return CriterionResult(
        criterion_id=criterion_id,
        outcome=CriterionOutcome.NOT_MET,
        observation=_labelled(judgement.reasoning or "the model judged this unmet", observation),
        failure_kind=FailureKind.UNKNOWN,
        model_derived=True,
        step_id=step.step_id,
        model_invocation_id=invocation_id,
        model_name=model_name,
        prompt_version=prompt_version,
    )


def _labelled(reasoning: str, observation: str) -> str:
    """Keep the model's words visibly the model's, next to what was actually seen."""
    return f"model judgement: {reasoning} (observed at {observation})"


def _criterion_of(step: PlanStep) -> str:
    # Guaranteed by PlanStep: an assertion cannot exist without a criterion.
    assert step.criterion_id is not None
    return step.criterion_id


def _unreached(step: PlanStep, reason: str, kind: FailureKind | None) -> CriterionResult:
    criterion_id = _criterion_of(step)
    observation = f"the run did not reach this criterion: {reason}"
    if kind is None:
        return CriterionResult(
            criterion_id=criterion_id,
            outcome=CriterionOutcome.UNVERIFIED,
            observation=observation,
            step_id=step.step_id,
        )
    return CriterionResult(
        criterion_id=criterion_id,
        outcome=CriterionOutcome.NOT_MET,
        # Never PRODUCT. A run that stopped before reaching a criterion has observed
        # nothing about the product, and saying otherwise is the one mistake that
        # makes every later report suspect.
        failure_kind=kind,
        observation=observation,
        step_id=step.step_id,
    )
