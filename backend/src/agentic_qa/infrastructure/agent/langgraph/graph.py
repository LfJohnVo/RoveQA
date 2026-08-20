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
import time
from collections.abc import Callable
from dataclasses import replace
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from agentic_qa.application.ports.artifacts import ArtifactRepository
from agentic_qa.application.ports.browser import BrowserGateway, UnperformableActionError
from agentic_qa.application.ports.models import ModelGateway, PlanningRequest
from agentic_qa.application.services.criterion_verification import (
    verify_criteria as verify_plan_criteria,
)
from agentic_qa.application.services.guarded_browser import ActionDeniedError
from agentic_qa.domain.agent.state import (
    AgentState,
    EpisodeSummary,
    StepOutcome,
    StepRecord,
)
from agentic_qa.domain.browser.actions import (
    BrowserAction,
)
from agentic_qa.domain.browser.evidence import EvidenceRef
from agentic_qa.domain.exploration.actions import exploration_action, is_takeable
from agentic_qa.domain.exploration.frontier import (
    ExplorationBudget,
    ExplorationReport,
    Frontier,
    FrontierSnapshot,
    StopReason,
    stop_reason,
)
from agentic_qa.domain.knowledge.memory_context import MemoryItem
from agentic_qa.domain.projects.run_policy import RunPolicy
from agentic_qa.domain.qa.test_plan import PlanStep
from agentic_qa.domain.qa.verification import CriterionResult, FailureKind

logger = logging.getLogger(__name__)

MAX_RECOVERY_ATTEMPTS = 2
"""Bounded so a failing step cannot spin forever inside one episode."""


class GraphState(TypedDict, total=False):
    agent: AgentState
    pending_action: BrowserAction | None
    last_outcome_succeeded: bool
    last_detail: str
    last_denied: bool
    """Refused by policy. Distinguished from a failure because it must not be retried."""

    last_rejected: bool
    """The planner proposed an action the domain refused. Distinguished from a policy
    denial because it *should* be retried: the planner can correct a missing target
    once it is told, while a policy refusal will refuse the same action again."""

    recovery_attempts: int
    actions_taken: int
    """Actions this episode sent to the browser. Counted here because the RunPolicy
    promises a bound, and a promise nothing enforces is not a bound."""

    model_calls: int
    failure_kind: FailureKind | None
    """Why the episode stopped, in the vocabulary a report uses. Without it a run that
    ran out of actions and a run nobody could explain look the same — and the second
    reading, inconclusive, hides the first."""

    safe_point: str | None
    """Set by Checkpoint; the activity turns it into a durable RecoveryPoint."""

    criterion_results: tuple[CriterionResult, ...]
    """One per plan assertion. The activity persists them and derives the verdict."""

    evidence: tuple[EvidenceRef, ...]
    """Artifacts captured this episode. The activity indexes them durably."""

    exploration: FrontierSnapshot | None
    """The frontier, flattened. Checkpointed with everything else, because an
    exploration is exactly the long run that must survive a worker dying — and a
    frontier that came back without its `offered` set could walk a two-page cycle
    forever, having survived the crash and lost the guarantee."""

    exploration_depth: int
    """Depth of the affordance most recently taken, so the page it leads to is recorded
    at the right distance from the entry point."""

    exploration_report: ExplorationReport | None
    """Set once, when exploring stops. What was spent and why, which is the difference
    between a complete map and a truncated one."""


def build_agent_graph(
    *,
    browser: BrowserGateway,
    model: ModelGateway,
    checkpointer: Any = None,
    assertions: tuple[PlanStep, ...] = (),
    hints: dict[str, str] | None = None,
    memory: tuple[MemoryItem, ...] = (),
    artifacts: ArtifactRepository | None = None,
    run_id: str | None = None,
    evidence_set_id: str | None = None,
    exploration_budget: ExplorationBudget | None = None,
    policy: RunPolicy | None = None,
    now: Callable[[], float] = time.monotonic,
) -> Any:
    """Compile the graph over the ports it needs. No adapter types appear here.

    `assertions` are the plan's acceptance criteria. They are evaluated once, at the end
    of the episode, while the browser still holds the page the run finished on — closing
    the session first and judging from artifacts afterwards would mean judging a
    screenshot instead of the application.

    Evidence is captured for the same reason and at the same moment: the bytes only
    exist while the page does. Storing them is the repository's job and *recording*
    them durably is the activity's, so the graph returns refs and writes no rows.

    `exploration_budget` switches the graph from planning to exploring. The two never
    coexist: an exploring episode calls no model at all — the frontier decides what to
    try next from what the page offers — so exploring an application costs zero
    inference. Which mode applies is decided when the graph is built, not per step, so
    neither node has to ask what kind of episode it is in.

    `policy` is what the run may spend and what it may do. It bounds the episode
    (actions, model calls, duration) and, when exploring, decides what the frontier is
    allowed to offer. Absent only in tests that are about something else.
    """
    exploring = exploration_budget is not None
    started = now()
    # Asked before an affordance enters the frontier, not after it is attempted: a
    # denied action ends an episode by design, so a read-only exploration that queued
    # buttons would stop at the first one instead of mapping the application.
    takeable = (lambda affordance: is_takeable(affordance, policy)) if policy is not None else None

    def exhausted(state: GraphState) -> str | None:
        """Which of the run's budgets is spent, if any.

        The RunPolicy promises three bounds — actions, model calls, duration — and
        nothing on the planning path counted them. An unbounded loop therefore ran until
        Temporal's activity timeout and came back as an infrastructure failure: both the
        wrong classification and the dangerous one, because a retry replays the loop.
        """
        if policy is None:
            return None
        if state.get("actions_taken", 0) >= policy.max_actions:
            return f"the run reached its limit of {policy.max_actions} action(s)"
        if state.get("model_calls", 0) >= policy.max_model_calls:
            return f"the run reached its limit of {policy.max_model_calls} model call(s)"
        if now() - started >= policy.max_duration_seconds:
            return f"the run reached its limit of {policy.max_duration_seconds:.0f}s"
        return None

    async def observe(state: GraphState) -> GraphState:
        agent = state["agent"]
        # The planner used to be told the url and nothing else, and then asked to name
        # an element to act on. It could only invent one — `wait_for` on a heading that
        # was never there — and every invention cost a locator timeout and a recovery
        # attempt until the episode ran out. `describe_page` has existed since the
        # exploration work; it was simply never on this path.
        page = await browser.describe_page()
        agent.last_observation = page.describe()
        return {"agent": agent, "safe_point": None}

    async def plan(state: GraphState) -> GraphState:
        agent = state["agent"]
        spent = exhausted(state)
        if spent is not None:
            agent.failure_reason = spent
            agent.goal_reached = False
            logger.info("run %s stopped on budget: %s", agent.run_id, spent)
            return {
                "agent": agent,
                "pending_action": None,
                # `agent_budget` makes the run `blocked`, which is the truth: it could
                # not finish, and it observed nothing about the product.
                "failure_kind": FailureKind.AGENT_BUDGET,
            }

        decision = await model.next_action(
            PlanningRequest(
                goal=agent.goal,
                observation=agent.last_observation,
                recent_steps=agent.recent_steps,
                episode_summaries=agent.episode_summaries,
                folded_episodes=agent.folded_episodes,
                # The policy is what knows the application's address. Withholding it
                # left the planner guessing at URLs the same policy then refused.
                allowed_origins=policy.allowed_origins if policy is not None else (),
                # Constant for the episode: it was resolved once, before the graph
                # started, so every replay of this episode plans against the same
                # memory the original attempt saw.
                memory=memory,
            )
        )
        agent.pending_action_intent = decision.action.intent if decision.action else None
        kind: FailureKind | None = None
        rejected = False
        if decision.action is None:
            # The planner proposing nothing is not the same as the goal being met.
            # If the last observed step failed and nothing repaired it, the episode
            # ended unresolved — reporting success here would be claiming a verdict
            # nobody verified.
            last_step = agent.recent_steps[-1] if agent.recent_steps else None
            if decision.rejected:
                # We refused the proposal, so the planner is the one who can fix it —
                # once it is told. Recorded as a failed step, which is how the reason
                # reaches the next prompt, and routed through Recover like any other
                # semantic failure (ADR 0009). Ending the episode here instead cost a
                # whole run for one malformed proposal.
                rejected = True
                agent.record_step(
                    StepRecord(
                        index=agent.step_index + 1,
                        intent=decision.failure or "the proposed action was refused",
                        outcome=StepOutcome.FAILED,
                        detail=decision.failure or "",
                    )
                )
            elif decision.failure is not None:
                # No decision was obtained: unreachable model, unusable output, no
                # capacity. Retrying inside the episode would ask a dead endpoint the
                # same question, so the episode ends unresolved.
                agent.failure_reason = decision.failure
                agent.goal_reached = False
                kind = FailureKind.MODEL
            elif last_step is not None and last_step.outcome is StepOutcome.FAILED:
                agent.failure_reason = (
                    last_step.detail or "the last action failed and no recovery was proposed"
                )
                agent.goal_reached = False
                # Deliberately unclassified. An action that failed on the page could be
                # a broken environment or a broken product, and guessing between them is
                # exactly the guess that makes a report untrustworthy.
            else:
                agent.goal_reached = True
        return {
            "agent": agent,
            "pending_action": decision.action,
            "model_calls": state.get("model_calls", 0) + 1,
            "failure_kind": kind,
            "last_rejected": rejected,
            **({"last_detail": decision.failure or ""} if rejected else {}),
        }

    async def explore(state: GraphState) -> GraphState:
        """Decide the next thing to try from what the page offers. No model involved.

        This node both records where the last action landed and picks the next move,
        because those are one decision: the page in front of us is the evidence for
        what is left to do.
        """
        assert exploration_budget is not None  # `exploring` gates this node
        agent = state["agent"]
        frontier = Frontier.from_snapshot(
            exploration_budget, state.get("exploration"), takeable=takeable
        )

        page = await browser.describe_page()
        agent.last_observation = page.url or "about:blank"
        discovered = frontier.record(page, depth=state.get("exploration_depth", 0))
        if discovered:
            logger.info(
                "run %s discovered state %s at %s", agent.run_id, page.signature, page.route
            )

        reason = stop_reason(
            exploration_budget,
            frontier.progress(elapsed_seconds=now() - started),
        )
        if reason is not None:
            # Exhausting the frontier is success: everything reachable was reached.
            # A budget stop is not a failure either — the run reports what it spent —
            # but it must not be reported as a complete map.
            agent.goal_reached = reason in (StopReason.FRONTIER_EXHAUSTED, StopReason.GOAL_REACHED)
            if not agent.goal_reached:
                agent.failure_reason = f"exploration stopped: {reason.value}"
            logger.info("run %s stopped exploring: %s", agent.run_id, reason.value)
            return {
                "agent": agent,
                "pending_action": None,
                "exploration": frontier.snapshot(),
                "exploration_report": frontier.report(reason),
                "safe_point": None,
                # A crawl that ran out of budget did not observe the whole application.
                # One that ran out of places to go is simply finished.
                "failure_kind": None if agent.goal_reached else FailureKind.AGENT_BUDGET,
            }

        entry = frontier.take()
        assert entry is not None  # `frontier_size == 0` is a stop reason
        return {
            "agent": agent,
            "pending_action": exploration_action(entry.affordance),
            "exploration": frontier.snapshot(),
            "exploration_depth": entry.depth,
            "safe_point": None,
        }

    async def act(state: GraphState) -> GraphState:
        action = state.get("pending_action")
        if action is None:
            if state.get("last_rejected", False):
                # Nothing was executed and nothing here is worth resetting: the reason
                # the proposal was refused is the only news, and clearing `last_detail`
                # would throw it away one node before Recover reads it.
                return {}
            return {"last_outcome_succeeded": True, "last_detail": "", "last_denied": False}
        # Counted before the attempt, not after it succeeds: an action the page refused
        # still cost the run a turn, and a budget that only counted successes would let
        # a failing loop run forever.
        taken = state.get("actions_taken", 0) + 1
        try:
            outcome = await browser.execute(action)
        except ActionDeniedError as denied:
            # A policy refusal is a fact about the run, not a malfunction. Letting it
            # escape would surface as an activity crash and let Temporal retry the
            # episode, re-proposing an action the policy will refuse again (ADR 0009).
            logger.warning("policy denied %s: %s", action.type, denied.decision.detail)
            return {
                "actions_taken": taken,
                "last_outcome_succeeded": False,
                "last_detail": denied.decision.detail,
                "last_denied": True,
            }
        except UnperformableActionError as unusable:
            # Same reasoning, different cause: the planner asked for something the page
            # cannot satisfy — a click with no locatable target, an invented role. That
            # is a failed step the planner should see and route around, not a crash.
            # Not `last_denied`: unlike a policy refusal, trying something else here is
            # exactly the right response, so this stays on the recovery path.
            logger.warning("action %s could not be performed: %s", action.type, unusable)
            return {
                "actions_taken": taken,
                "last_outcome_succeeded": False,
                "last_detail": str(unusable),
                "last_denied": False,
            }
        return {
            "actions_taken": taken,
            "last_outcome_succeeded": outcome.succeeded,
            "last_detail": outcome.detail,
            "last_denied": False,
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
        denied = state.get("last_denied", False)
        if denied:
            outcome = StepOutcome.DENIED
        elif succeeded:
            outcome = StepOutcome.SUCCEEDED
        else:
            outcome = StepOutcome.FAILED

        agent.record_step(
            StepRecord(
                index=agent.step_index + 1,
                intent=action.intent,
                outcome=outcome,
                detail=state.get("last_detail", ""),
            )
        )
        if denied:
            # Stop rather than re-plan. Letting the agent look for another way to do
            # what the policy just refused is exactly the behaviour the policy exists
            # to prevent.
            agent.failure_reason = f"policy denied {action.type}: {state.get('last_detail', '')}"
            agent.goal_reached = False
            # Classified, so the run comes back `blocked` rather than inconclusive. The
            # policy stopped it; that is a fact about the run, not a mystery.
            return {"agent": agent, "failure_kind": FailureKind.POLICY}
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
        # Cleared here, not in `plan`: leaving it set would send the next pass straight
        # back to recovery whatever the planner decided.
        return {
            "agent": agent,
            "recovery_attempts": attempts,
            "safe_point": None,
            "last_rejected": False,
        }

    async def capture(kind: str, step_id: str | None = None) -> EvidenceRef | None:
        """Store one screenshot, or give up quietly.

        Evidence is worth having and never worth failing a run for: a browser that
        cannot produce a screenshot has usually already told us something worse
        through the action outcome.
        """
        if artifacts is None or run_id is None or evidence_set_id is None:
            return None
        try:
            image = await browser.capture_screenshot()
        except Exception as error:  # noqa: BLE001 - any capture failure is non-fatal
            logger.info("could not capture %s evidence: %s", kind, error)
            return None
        return await artifacts.store(
            run_id=run_id,
            evidence_set_id=evidence_set_id,
            kind=kind,
            filename=f"{kind}-{step_id or 'episode'}.png",
            content=image,
            step_id=step_id,
        )

    async def verify_criteria(state: GraphState) -> GraphState:
        """Judge the plan's acceptance criteria against the page the run ended on."""
        agent = state["agent"]
        # Captured before judging, so the image shows the page the criteria were
        # judged against rather than whatever a check navigated to afterwards.
        shot = await capture("screenshot")
        evidence = (shot,) if shot is not None else ()

        if not assertions:
            return {"criterion_results": (), "evidence": evidence}

        results = await verify_plan_criteria(
            assertions,
            browser=browser,
            model=model,
            hints=hints,
            goal_failure=agent.failure_reason,
            goal_failure_kind=state.get("failure_kind"),
        )
        if shot is not None:
            # Every criterion was judged against this one page state, so this is
            # honestly the evidence for all of them.
            results = tuple(
                replace(result, evidence_refs=(shot.artifact_id,)) for result in results
            )
        return {"criterion_results": results, "evidence": evidence}

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
        if state.get("last_rejected", False):
            # No action reached the browser, but there is something to recover from:
            # the planner's own proposal, and the reason it was refused is now the last
            # step it will see.
            return "recover"
        if state.get("pending_action") is None or state.get("last_denied", False):
            return "verify_criteria"
        if state.get("last_outcome_succeeded", False):
            return "checkpoint"
        return "recover"

    def after_recover(state: GraphState) -> str:
        agent = state["agent"]
        if agent.failure_reason is not None:
            return "verify_criteria"
        # An exploring run does not re-plan a failed step: the affordance was already
        # taken out of the frontier, and asking for it again is how a broken link
        # becomes an infinite loop. It moves on to whatever is next.
        return "explore" if exploring else "plan"

    def after_checkpoint(state: GraphState) -> str:
        if state["agent"].goal_reached:
            return "verify_criteria"
        return "explore" if exploring else "observe"

    builder: StateGraph[GraphState, Any, GraphState, GraphState] = StateGraph(GraphState)
    builder.add_node("observe", observe)
    builder.add_node("plan", plan)
    builder.add_node("explore", explore)
    builder.add_node("act", act)
    builder.add_node("verify", verify)
    builder.add_node("checkpoint", checkpoint)
    builder.add_node("recover", recover)
    builder.add_node("verify_criteria", verify_criteria)
    builder.add_node("close_episode", close_episode)

    # The mode is chosen here, once, rather than branched on inside every node.
    builder.add_edge(START, "explore" if exploring else "observe")
    builder.add_edge("observe", "plan")
    builder.add_edge("plan", "act")
    builder.add_edge("explore", "act")
    builder.add_edge("act", "verify")
    builder.add_conditional_edges("verify", after_verify)
    builder.add_conditional_edges("recover", after_recover)
    builder.add_conditional_edges("checkpoint", after_checkpoint)
    builder.add_edge("verify_criteria", "close_episode")
    builder.add_edge("close_episode", END)

    return builder.compile(checkpointer=checkpointer)
