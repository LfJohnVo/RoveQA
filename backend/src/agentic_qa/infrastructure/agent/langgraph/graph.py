"""The agent graph (docs/06).

    Observe -> Plan -> Act -> Verify -> Checkpoint -> (Observe | Close Episode)
                               |
                               +-> Recover -> Plan

Two rules shape this file:

- **Nodes decide, the activity persists.** A node marks a moment as safe by setting
  `safe_point`; writing the durable `RecoveryPoint` happens outside the graph, where
  the real checkpoint id exists. Keeping database writes out of nodes also keeps the
  graph replayable.
- **Recover owns semantic retries** and nothing else does. Temporal retries only
  infrastructure failures, and both always resume through the checkpoint plus
  verify-before-retry (ADR 0009). A second retry loop here would multiply.

Memory retrieval is a documented node in docs/06 but belongs to Phase 09; adding a
placeholder now would be a fake step that proves nothing.
"""

import logging
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from agentic_qa.application.ports.browser import BrowserGateway
from agentic_qa.application.ports.models import ModelGateway, PlanningRequest
from agentic_qa.domain.agent.state import (
    AgentState,
    EpisodeSummary,
    StepOutcome,
    StepRecord,
)
from agentic_qa.domain.browser.actions import BrowserAction

logger = logging.getLogger(__name__)

MAX_RECOVERY_ATTEMPTS = 2
"""Bounded so a failing step cannot spin forever inside one episode."""


class GraphState(TypedDict, total=False):
    agent: AgentState
    pending_action: BrowserAction | None
    last_outcome_succeeded: bool
    last_detail: str
    recovery_attempts: int
    safe_point: str | None
    """Set by Checkpoint; the activity turns it into a durable RecoveryPoint."""


def build_agent_graph(
    *, browser: BrowserGateway, model: ModelGateway, checkpointer: Any = None
) -> Any:
    """Compile the graph over the ports it needs. No adapter types appear here."""

    async def observe(state: GraphState) -> GraphState:
        agent = state["agent"]
        url = await browser.current_url()
        agent.last_observation = url or "about:blank"
        return {"agent": agent, "safe_point": None}

    async def plan(state: GraphState) -> GraphState:
        agent = state["agent"]
        decision = await model.next_action(
            PlanningRequest(
                goal=agent.goal,
                observation=agent.last_observation,
                recent_steps=agent.recent_steps,
                episode_summaries=agent.episode_summaries,
            )
        )
        agent.pending_action_intent = decision.action.intent if decision.action else None
        if decision.action is None:
            # The planner proposing nothing is not the same as the goal being met.
            # If the last observed step failed and nothing repaired it, the episode
            # ended unresolved — reporting success here would be claiming a verdict
            # nobody verified.
            last_step = agent.recent_steps[-1] if agent.recent_steps else None
            if last_step is not None and last_step.outcome is StepOutcome.FAILED:
                agent.failure_reason = (
                    last_step.detail or "the last action failed and no recovery was proposed"
                )
                agent.goal_reached = False
            else:
                agent.goal_reached = True
        return {"agent": agent, "pending_action": decision.action}

    async def act(state: GraphState) -> GraphState:
        action = state.get("pending_action")
        if action is None:
            return {"last_outcome_succeeded": True, "last_detail": ""}
        outcome = await browser.execute(action)
        return {
            "last_outcome_succeeded": outcome.succeeded,
            "last_detail": outcome.detail,
        }

    async def verify(state: GraphState) -> GraphState:
        """Deterministic verification first (docs/06 verification priority).

        The browser already reported whether the action did what it claimed; a model
        opinion is not consulted here and would not override it if it were.
        """
        agent = state["agent"]
        action = state.get("pending_action")
        if action is None:
            return {"agent": agent}

        succeeded = state.get("last_outcome_succeeded", False)
        agent.record_step(
            StepRecord(
                index=agent.step_index + 1,
                intent=action.intent,
                outcome=StepOutcome.SUCCEEDED if succeeded else StepOutcome.FAILED,
                detail=state.get("last_detail", ""),
            )
        )
        return {"agent": agent}

    async def checkpoint(state: GraphState) -> GraphState:
        """Mark a semantically safe moment. Persisting it is the activity's job."""
        agent = state["agent"]
        return {
            "agent": agent,
            "recovery_attempts": 0,
            "safe_point": "navigation_stable",
        }

    async def recover(state: GraphState) -> GraphState:
        attempts = state.get("recovery_attempts", 0) + 1
        agent = state["agent"]
        if attempts > MAX_RECOVERY_ATTEMPTS:
            # Give up honestly rather than looping: the run reports why it stopped.
            agent.failure_reason = state.get("last_detail") or "action could not be recovered"
            agent.goal_reached = False
        logger.info("recovery attempt %s for run %s", attempts, agent.run_id)
        return {"agent": agent, "recovery_attempts": attempts, "safe_point": None}

    async def close_episode(state: GraphState) -> GraphState:
        agent = state["agent"]
        agent.close_episode(
            EpisodeSummary(
                episode_index=agent.episode_index,
                goal=agent.goal,
                steps_taken=agent.step_index,
                succeeded=agent.goal_reached and agent.failure_reason is None,
                summary=agent.failure_reason or f"goal reached at step {agent.step_index}",
            )
        )
        return {"agent": agent, "safe_point": "episode_closed"}

    def after_verify(state: GraphState) -> str:
        if state.get("pending_action") is None:
            return "close_episode"
        if state.get("last_outcome_succeeded", False):
            return "checkpoint"
        return "recover"

    def after_recover(state: GraphState) -> str:
        agent = state["agent"]
        if agent.failure_reason is not None:
            return "close_episode"
        return "plan"

    def after_checkpoint(state: GraphState) -> str:
        return "close_episode" if state["agent"].goal_reached else "observe"

    builder: StateGraph[GraphState, Any, GraphState, GraphState] = StateGraph(GraphState)
    builder.add_node("observe", observe)
    builder.add_node("plan", plan)
    builder.add_node("act", act)
    builder.add_node("verify", verify)
    builder.add_node("checkpoint", checkpoint)
    builder.add_node("recover", recover)
    builder.add_node("close_episode", close_episode)

    builder.add_edge(START, "observe")
    builder.add_edge("observe", "plan")
    builder.add_edge("plan", "act")
    builder.add_edge("act", "verify")
    builder.add_conditional_edges("verify", after_verify)
    builder.add_conditional_edges("recover", after_recover)
    builder.add_conditional_edges("checkpoint", after_checkpoint)
    builder.add_edge("close_episode", END)

    return builder.compile(checkpointer=checkpointer)
