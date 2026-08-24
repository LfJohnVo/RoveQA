"""What a checkpoint may reconstruct.

LangGraph keeps state in memory during a run, so serialization only really matters at
the moment that matters most: a fresh worker reading an existing thread. That makes the
allowlist easy to break without noticing — nothing fails until a resume — so it is
tested directly here, without a database.

`LANGGRAPH_STRICT_MSGPACK=true` is set for the whole suite, which is the regime the
library is moving to. A type missing from `CHECKPOINTED_TYPES` fails here rather than
during someone's recovery.
"""

from typing import Any

from agentic_qa.domain.agent.state import (
    AgentState,
    EpisodeSummary,
    StepOutcome,
    StepRecord,
)
from agentic_qa.domain.browser.actions import (
    ActionTarget,
    BrowserAction,
    BrowserActionType,
    IdempotencyStrategy,
)
from agentic_qa.domain.exploration.state import Affordance, PageState
from agentic_qa.domain.qa.verification import (
    CriterionOutcome,
    CriterionResult,
    CriterionSource,
)
from agentic_qa.infrastructure.agent.langgraph.checkpointer import (
    CHECKPOINTED_TYPES,
    build_serializer,
)
from agentic_qa.infrastructure.agent.langgraph.graph import GraphState


def realistic_state() -> dict[str, Any]:
    """Everything the graph puts in its state, in one object.

    That sentence stopped being true and nothing noticed: the page-check layer added
    `page_checks`, `last_page` and `consent_answered`, this object did not, and
    `CriterionSource` was missing from the allowlist for a whole phase. A worker that
    died mid-crawl could not have resumed. The class of mistake is covered below by
    `test_every_state_key_names_a_type_the_checkpoint_can_rebuild`; keeping this object
    honest is still worth doing, because a round trip exercises values and not just
    names.
    """
    agent = AgentState(
        run_id="run-1",
        goal="check out",
        last_observation="http://target.test/cart",
        recent_steps=(
            StepRecord(index=1, intent="open the cart", outcome=StepOutcome.SUCCEEDED),
            StepRecord(
                index=2, intent="delete the account", outcome=StepOutcome.DENIED, detail="no"
            ),
        ),
        episode_summaries=(
            EpisodeSummary(
                episode_index=0, goal="sign in", steps_taken=3, succeeded=True, summary="ok"
            ),
        ),
    )
    return {
        "agent": agent,
        "pending_action": BrowserAction(
            type=BrowserActionType.CLICK,
            intent="place the order",
            target=ActionTarget(role="button", name="Place order"),
            side_effect=True,
            idempotency_strategy=IdempotencyStrategy.VERIFY_BEFORE_RETRY,
            verification_strategy="the confirmation page appears",
        ),
        "last_page": PageState(
            url="http://target.test/cart",
            affordances=(Affordance(role="button", name="Place order"),),
            title="Cart",
            http_status=200,
        ),
        "page_checks": {
            "page:/cart": CriterionResult(
                criterion_id="page:/cart",
                outcome=CriterionOutcome.MET,
                observation="the page answered 200",
                source=CriterionSource.SWEEP,
            )
        },
        "consent_answered": True,
    }


def test_a_checkpointed_state_survives_a_round_trip_as_itself() -> None:
    """Not "it deserializes" — it comes back as the same types, with the same values."""
    serializer = build_serializer()
    original = realistic_state()

    restored: dict[str, Any] = serializer.loads_typed(serializer.dumps_typed(original))

    agent = restored["agent"]
    assert isinstance(agent, AgentState), f"AgentState came back as {type(agent).__name__}"
    assert agent.run_id == "run-1"
    assert isinstance(agent.recent_steps[1], StepRecord)
    assert agent.recent_steps[1].outcome is StepOutcome.DENIED
    assert isinstance(agent.episode_summaries[0], EpisodeSummary)

    action = restored["pending_action"]
    assert isinstance(action, BrowserAction), f"BrowserAction came back as {type(action).__name__}"
    assert action.type is BrowserActionType.CLICK
    assert isinstance(action.target, ActionTarget)
    assert action.idempotency_strategy is IdempotencyStrategy.VERIFY_BEFORE_RETRY

    checks = restored["page_checks"]
    assert isinstance(checks["page:/cart"], CriterionResult)
    assert checks["page:/cart"].source is CriterionSource.SWEEP
    assert isinstance(restored["last_page"], PageState)
    assert restored["last_page"].http_status == 200


def test_every_state_key_names_a_type_the_checkpoint_can_rebuild() -> None:
    """The class of mistake, not the instance.

    Adding a key to `GraphState` whose type is not in the allowlist breaks nothing until
    somebody resumes a run — so the failure lands on a stranger, at the worst moment, and
    reads as data loss. This walks the annotations instead of trusting the next person to
    remember.

    Plain types are fine on their own; only the project's own classes and enums need
    registering.
    """
    from typing import Union, get_args, get_origin, get_type_hints

    allowed = set(CHECKPOINTED_TYPES)
    plain = {bool, int, float, str, bytes, type(None), dict, list, tuple, set, Any}

    def flatten(annotation: object) -> list[object]:
        origin = get_origin(annotation)
        if origin is None:
            return [annotation]
        found: list[object] = [origin]
        for argument in get_args(annotation):
            found.extend(flatten(argument))
        return found

    missing: list[str] = []
    for key, annotation in get_type_hints(GraphState).items():
        for candidate in flatten(annotation):
            if candidate in plain or candidate in allowed or candidate is Union:
                continue
            if not isinstance(candidate, type):
                continue
            if candidate.__module__.startswith("agentic_qa"):
                missing.append(f"{key} -> {candidate.__name__}")

    assert missing == [], (
        "these state types cannot be rebuilt from a checkpoint; add them to "
        f"CHECKPOINTED_TYPES: {missing}"
    )
