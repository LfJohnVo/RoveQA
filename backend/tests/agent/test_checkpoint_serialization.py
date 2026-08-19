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
from agentic_qa.infrastructure.agent.langgraph.checkpointer import build_serializer


def realistic_state() -> dict[str, Any]:
    """Everything the graph puts in its state, in one object."""
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
