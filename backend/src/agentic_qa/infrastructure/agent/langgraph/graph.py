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
from agentic_qa.application.ports.episodes import ActionRecord
from agentic_qa.application.ports.models import ModelGateway, PlanCriterion, PlanningRequest
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
    NEEDS_TARGET,
    ActionTarget,
    BrowserAction,
    BrowserActionType,
    IdempotencyStrategy,
)
from agentic_qa.domain.browser.consent import (
    ConsentPolicy,
    consent_choice,
    looks_like_consent,
)
from agentic_qa.domain.browser.evidence import EvidenceRef
from agentic_qa.domain.browser.policy_guard import evaluate_action
from agentic_qa.domain.exploration.actions import exploration_action, is_takeable, seed_action
from agentic_qa.domain.exploration.frontier import (
    ExplorationBudget,
    ExplorationReport,
    Frontier,
    FrontierSnapshot,
    StopReason,
    stop_reason,
)
from agentic_qa.domain.exploration.state import PageState
from agentic_qa.domain.knowledge.memory_context import MemoryItem
from agentic_qa.domain.projects.run_policy import RunPolicy
from agentic_qa.domain.qa.page_checks import check_page, is_checkable
from agentic_qa.domain.qa.test_plan import PlanStep
from agentic_qa.domain.qa.verification import (
    CriterionOutcome,
    CriterionResult,
    FailureKind,
    failure_kind_for_action,
)

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

    last_page: PageState | None
    """The page the last observation described.

    Kept so a refusal can name the alternative the page offers. The domain guard cannot
    do this -- it decides on the action alone, which is what makes it testable without a
    browser -- and the graph is the layer that has both.
    """

    failed_targets: tuple[str, ...]
    """Locators the browser could not act on this episode, in the order they were tried.

    Fed back to the planner. Kept in the graph state rather than derived from
    `action_log` at planning time because the log is a record of what happened and this
    is an input to what happens next; deriving one from the other would tie the planner's
    context to the shape of the audit trail.
    """

    action_log: tuple[ActionRecord, ...]
    """What the agent did, in order, for the durable log.

    Separate from `agent.recent_steps`, which is a *window* the planner reads and is
    deliberately small. This one is the whole run: an operator diagnosing a stuck run needs
    the step that went wrong, not the last twelve.
    """

    page_checks: dict[str, CriterionResult]
    """One universal check per route this run observed, keyed by criterion id.

    Keyed rather than appended so a route visited twice is one finding, and so the worse
    answer wins: a page that answered 500 once and 200 later is a page that answered 500
    (ADR 0017).
    """

    criteria_seen: dict[str, str]
    """Criteria whose literal has already been seen on a page this run visited, and
    where. Checking a hint costs no inference -- it is a substring -- so it is asked on
    every observation rather than once, at the end, against whichever page the run
    happened to stop on."""

    last_action_type: BrowserActionType | None
    """What the browser was asked to do when it failed. Kept so that giving up can name
    a cause: a locator that never resolved and a page that never loaded are different
    failures, and reporting both as "nobody knows" throws away what we do know."""

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

    consent_answered: bool
    """Whether this episode already answered a consent overlay.

    Once and only once. A banner that reappears is a site refusing the answer, and
    pressing again would be a second consent signal nobody gave."""

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

    def _sightings(
        already: dict[str, str] | None, visible: str, url: str, step: int
    ) -> dict[str, str]:
        """Which criteria this page satisfies, added to what earlier pages showed.

        Matched against `PageState.visible_text` and never against the whole rendered
        observation: that one opens with the url, so a criterion whose literal appears only
        in the address would be credited to a page that never said it. First sighting wins
        -- where a criterion became true is more useful than where it last happened to
        still be true.
        """
        found = dict(already or {})
        for criterion_id, expected in (hints or {}).items():
            if criterion_id in found or not expected:
                continue
            if expected in visible:
                found[criterion_id] = f"step {step} at {url}"
        return found

    def _consent_refusal(state: GraphState, action: BrowserAction) -> str | None:
        """Why this run may not press this control, when the control answers a banner.

        Both facts are needed and only the graph has both: the domain guard decides on an
        action alone — which is what lets it be tested without a browser — and it cannot
        know the page is a consent overlay.

        Deliberately narrow. It refuses a press on a control whose label answers consent,
        on a page that is asking about consent, under a policy that said not to. A button
        called "Accept" on a checkout is not this, and must not be caught by it.
        """
        if policy is None or policy.consent is not ConsentPolicy.LEAVE:
            return None
        if action.type is not BrowserActionType.CLICK:
            return None

        page = state.get("last_page")
        if page is None or not looks_like_consent(page.visible_text):
            return None

        named = tuple(a for a in page.affordances if a.name == action.target.name)
        if not named or consent_choice(named, ConsentPolicy.ACCEPT) is None:
            return None

        return (
            f"this run may not answer a consent overlay: pressing {action.target.name!r} "
            "would record a consent decision nobody made. Set the policy's consent field "
            "to reject or accept if that is intended."
        )

    def _consent_action(state: GraphState, page: PageState) -> BrowserAction | None:
        """The one control a consent overlay offers that this run may press, if any.

        Once per episode. A banner that reappears after being answered is a site refusing
        the answer, and pressing again would be an agent arguing with it — which is both
        futile and a second consent signal nobody gave.
        """
        if policy is None or state.get("consent_answered", False):
            return None
        if not looks_like_consent(page.visible_text):
            return None

        choice = consent_choice(page.affordances, policy.consent)
        if choice is None:
            return None

        return BrowserAction(
            type=BrowserActionType.CLICK,
            intent=f"answer the consent overlay: {choice.name}",
            target=ActionTarget(role=choice.role, name=choice.name),
            side_effect=True,
            idempotency_strategy=IdempotencyStrategy.VERIFY_BEFORE_RETRY,
            verification_strategy="observe whether the overlay is gone",
            answers_consent=True,
        )

    def _page_checks(
        already: dict[str, CriterionResult] | None, page: PageState
    ) -> dict[str, CriterionResult]:
        """The universal checks for this page, folded into what earlier pages produced.

        `exploring` answers the question `check_page` cannot: a crawl only ever takes
        affordances the site published, so a 404 there is the site's own broken link. A
        planned run can reach a url a model invented, where the same status accuses
        nobody (ADR 0015).

        A route already checked keeps the worse answer. Two visits to a page that failed
        once and worked once is not a healthy page, and last-write-wins would decide it
        by the order the crawl happened to take.
        """
        checks = dict(already or {})
        if not is_checkable(page):
            return checks
        result = check_page(page, reached_from_published_link=exploring)
        existing = checks.get(result.criterion_id)
        if existing is None or _severity(result) > _severity(existing):
            checks[result.criterion_id] = result
        return checks

    def _severity(result: CriterionResult) -> int:
        if result.outcome is CriterionOutcome.NOT_MET:
            return 2
        if result.outcome is CriterionOutcome.UNVERIFIED:
            return 1
        return 0

    def _allowed_alternative(state: GraphState, action: BrowserAction) -> BrowserAction | None:
        """The action this policy *does* allow for the element the refused one named.

        Verified with the same guard that refused the original, never assumed: telling a
        planner an alternative is permitted and being wrong would be worse than saying
        nothing. Only the element the model itself named is considered — nothing is
        inferred about what it was really trying to do.
        """
        named = (action.target.name or action.target.text or "").strip().lower()
        page = state.get("last_page")
        if not named or page is None or policy is None:
            return None
        for affordance in page.affordances:
            if affordance.name.strip().lower() != named:
                continue
            candidate = exploration_action(affordance)
            if candidate.type is action.type:
                return None
            if evaluate_action(candidate, policy).allowed:
                return candidate
        return None

    def _logged(
        state: GraphState,
        action: BrowserAction,
        succeeded: bool,
        *,
        detail: str = "",
        url: str | None = None,
        http_status: int | None = None,
    ) -> tuple[ActionRecord, ...]:
        """Append one record. Appending rather than replacing is what makes it a trace."""
        so_far = state.get("action_log", ())
        return (
            *so_far,
            ActionRecord(
                index=len(so_far) + 1,
                action=action.type.value,
                intent=action.intent,
                succeeded=succeeded,
                url=url,
                http_status=http_status,
                detail=detail,
            ),
        )

    def _unreachable(state: GraphState, action: BrowserAction) -> tuple[str, ...]:
        """Remember a locator the browser could not act on, so the planner is told once.

        Only actions the domain requires a target for: `navigate` failing is usually a
        slow or momentarily unhappy site, and warning a planner off a url it should
        retry would trade one wasted step for a stuck run.
        """
        so_far = state.get("failed_targets", ())
        if action.type not in NEEDS_TARGET or action.target.is_empty():
            return so_far
        described = action.target.describe()
        # Ordered dedup: the same target failing twice is one warning, and the order the
        # run tried them in is the order they are worth reading.
        return so_far if described in so_far else (*so_far, described)

    exploring = exploration_budget is not None
    started = now()
    # The plan's criteria, in the shape the planner reads. Built once here because this
    # is the only place that holds both the assertions and their literals; before this
    # they met only in the final verification node, so the planner was asked to advance a
    # goal without being told what reaching it would look like.
    planner_criteria = tuple(
        PlanCriterion(
            criterion_id=step.criterion_id,
            description=step.description,
            expected_text=(hints or {}).get(step.criterion_id),
        )
        for step in assertions
        if step.criterion_id
    )
    settleable = {
        criterion.criterion_id for criterion in planner_criteria if criterion.expected_text
    }
    """Criteria a substring can answer. The rest need a model to judge and cannot be
    called met without asking it, so their presence is what makes a story unfinishable
    without the planner saying so."""

    all_settleable = bool(planner_criteria) and len(settleable) == len(planner_criteria)

    def story_is_done(state: GraphState) -> bool:
        """Every criterion this run is judged by has been seen, so there is nothing left.

        Measured on `after-a-form`: the record was created and the confirmation asserted
        at action 5, and the planner then asserted the same text twenty more times until
        the action budget ran out — twenty model calls and twenty actions after the
        answer was already in hand. `criteria_seen` knew; nothing acted on it.

        Deliberately not applied while exploring. There the story is a layer over a
        crawl (ADR 0017) and the crawl's own job — does every reachable page load — is
        not finished just because the story's criteria turned up early.
        """
        if exploring or not all_settleable:
            return False
        return settleable <= set(state.get("criteria_seen") or {})

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
        observation = page.describe()
        agent.last_observation = observation
        return {
            "agent": agent,
            "safe_point": None,
            "last_page": page,
            "criteria_seen": _sightings(
                state.get("criteria_seen"), page.visible_text, page.url, agent.step_index
            ),
            "page_checks": _page_checks(state.get("page_checks"), page),
        }

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
                # What has already been tried and did not work. Measured: without
                # it a planner spent three of its actions, and thirty seconds, on
                # one field that was never there.
                failed_targets=state.get("failed_targets", ()),
                # What this run is judged by. Constant for the episode, like memory.
                criteria=planner_criteria,
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

        # A browser opens on `about:blank`, and nothing in production ever navigated away
        # from it: a crawl described the blank page, found nothing to do, and reported a
        # *complete* map of one state. The Phase 12 gate passed only because the test
        # called `page.goto` itself before building the graph.
        #
        # Two facts decide whether to seed, and both are needed:
        #
        #   `exploration is None`   nothing has been described yet, so we are not mid-crawl
        #                           and a resumed run never starts over.
        #   last action failed      the seed did not land, so we are still on the blank
        #                           page. Falling through here would describe it and call
        #                           the map complete — the exact lie this exists to stop.
        #
        # The first entry has no last action, which reads as "not succeeded", so it seeds.
        # A failed seed simply seeds again, bounded by Recover, which classifies a
        # navigation that will not complete as `environment` and ends the run `blocked`.
        if (
            state.get("exploration") is None
            and policy is not None
            and not state.get("last_outcome_succeeded", False)
        ):
            # Through `act`, so it passes the guarded browser and counts against the
            # action budget like every other step. A seed exempt from the allowlist would
            # be the one navigation the policy does not govern.
            logger.info("run %s seeding exploration at %s", agent.run_id, policy.allowed_origins[0])
            return {
                "agent": agent,
                "pending_action": seed_action(policy),
                "safe_point": None,
            }

        frontier = Frontier.from_snapshot(
            exploration_budget, state.get("exploration"), takeable=takeable
        )

        page = await browser.describe_page()
        agent.last_observation = page.url or "about:blank"

        overlay = _consent_action(state, page)
        if overlay is not None:
            # Through `act`, like everything else: counted, policy-checked, and published
            # as an event. An agent that quietly clicked things while observing would be
            # one whose trace does not explain what it did to somebody else's site.
            logger.info("run %s answering a consent overlay: %s", agent.run_id, overlay.intent)
            return {
                "agent": agent,
                "pending_action": overlay,
                "consent_answered": True,
                "last_page": page,
                "safe_point": None,
            }
        # An exploring episode observes too, and a criterion satisfied on a page the crawl
        # passed through is as real as one satisfied on the page it stopped at.
        seen = _sightings(state.get("criteria_seen"), page.visible_text, page.url, agent.step_index)
        checks = _page_checks(state.get("page_checks"), page)
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
                "criteria_seen": seen,
                "page_checks": checks,
                "last_page": page,
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
            "criteria_seen": seen,
            "page_checks": checks,
            # Carried so `act` can refuse a click the consent policy forbids. Only the
            # observe node set this, so an exploring run left the guard blind — and a run
            # under `leave` pressed "Accept additional cookies" on gov.uk. Found by
            # running it, not by the unit tests, which asserted the pieces and never the
            # composition.
            "last_page": page,
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
        refusal = _consent_refusal(state, action)
        if refusal is not None:
            # Enforced here rather than in the explore node, because `act` is the one
            # place every action passes through. A planner is free to propose a click on
            # "Accept all cookies" like any other button, and without this the consent
            # policy would govern the crawl and be advice everywhere else.
            logger.warning("run %s refused a consent click: %s", state["agent"].run_id, refusal)
            return {
                "actions_taken": state.get("actions_taken", 0) + 1,
                "last_outcome_succeeded": False,
                "last_detail": refusal,
                "last_denied": True,
                "last_action_type": action.type,
            }

        # Counted before the attempt, not after it succeeds: an action the page refused
        # still cost the run a turn, and a budget that only counted successes would let
        # a failing loop run forever.
        taken = state.get("actions_taken", 0) + 1
        try:
            outcome = await browser.execute(action)
        except ActionDeniedError as denied:
            # A refusal that does not carry the correction is a refusal the planner
            # cannot act on. The trace showed exactly this: intent
            # "navigate_to_records_page", action `click`, denied with "click has side
            # effects" -- the planner already knew where it wanted to go and was told
            # only that it could not go that way.
            #
            # The alternative is on the page, and the graph is holding the page. Naming
            # it changes the feedback, never the action: `recover` puts this sentence in
            # the next prompt, and the planner decides again.
            # A refusal that does not carry the correction is a refusal the planner
            # cannot act on. The trace showed exactly this: intent
            # "navigate_to_records_page", action `click`, denied with "click has side
            # effects" -- it already knew where it wanted to go and was told only that it
            # could not go that way.
            alternative = _allowed_alternative(state, action)
            detail = denied.decision.detail
            if alternative is not None:
                detail = (
                    f"{detail}. {action.target.name or action.target.text} is reachable "
                    f"with {alternative.type.value}"
                    + (f" to {alternative.target.url}" if alternative.target.url else "")
                    + ", which this policy allows"
                )
            # A policy refusal is a fact about the run, not a malfunction. Letting it
            # escape would surface as an activity crash and let Temporal retry the
            # episode, re-proposing an action the policy will refuse again (ADR 0009).
            logger.warning("policy denied %s: %s", action.type, denied.decision.detail)
            return {
                "actions_taken": taken,
                "last_outcome_succeeded": False,
                "last_detail": detail,
                "last_action_type": action.type,
                # Terminal *unless* the policy itself permits another way to the element
                # the planner named. Ending on any refusal is what stops an agent hunting
                # for a way around a policy, and that stance is right — but taking the
                # path the policy allows is not hunting for a way around it, it is the
                # policy's own answer. Bounded by MAX_RECOVERY_ATTEMPTS either way, so
                # this cannot become probing by another name.
                "last_denied": alternative is None,
                "action_log": _logged(state, action, False, detail=detail),
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
                "last_action_type": action.type,
                "last_denied": False,
                "failed_targets": _unreachable(state, action),
                "action_log": _logged(state, action, False, detail=str(unusable)),
            }
        return {
            "actions_taken": taken,
            "last_outcome_succeeded": outcome.succeeded,
            "last_detail": outcome.detail,
            "last_action_type": action.type,
            "last_denied": False,
            "failed_targets": (
                state.get("failed_targets", ())
                if outcome.succeeded
                else _unreachable(state, action)
            ),
            "action_log": _logged(
                state,
                action,
                outcome.succeeded,
                detail=outcome.detail,
                url=outcome.current_url,
                http_status=outcome.http_status,
            ),
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
        if story_is_done(state):
            # Decided here rather than in the router so the episode summary agrees with
            # it: `close_episode` reads `goal_reached`, and a run that met every one of
            # its criteria and then stopped would otherwise summarise itself as failed.
            agent.goal_reached = True
        return {
            "agent": agent,
            "recovery_attempts": 0,
            "safe_point": "navigation_stable",
        }

    async def recover(state: GraphState) -> GraphState:
        attempts = state.get("recovery_attempts", 0) + 1
        agent = state["agent"]
        if attempts > MAX_RECOVERY_ATTEMPTS:
            # Give up honestly rather than looping: the run reports why it stopped, and
            # now also *what kind* of stop it was. The detail was already here; only the
            # classification was missing, which left every one of these `inconclusive`.
            agent.failure_reason = state.get("last_detail") or "action could not be recovered"
            agent.goal_reached = False
            # A rejected proposal never reached the browser, so `last_action_type` still
            # names whatever *did* -- LangGraph keeps an untouched key across updates, and
            # classifying a planner failure from an earlier navigation would report
            # `environment` for something the environment did fine.
            failed = state.get("last_action_type")
            if state.get("last_rejected", False):
                kind: FailureKind | None = FailureKind.MODEL
            elif failed is not None:
                kind = failure_kind_for_action(failed)
            else:
                kind = None
            return {
                "agent": agent,
                "recovery_attempts": attempts,
                "safe_point": None,
                "last_rejected": False,
                "failure_kind": kind,
            }
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

        # Sorted so a report reads the same way twice; dict order is insertion order and
        # a crawl's insertion order is whatever the frontier happened to do.
        swept = tuple(
            state.get("page_checks", {})[key] for key in sorted(state.get("page_checks", {}))
        )

        if not assertions:
            # The whole point of ADR 0017: a run with no story used to return nothing
            # here, so `derive_verdict` was never reached and every sweep — however much
            # it had learned — came back `inconclusive`.
            return {"criterion_results": swept, "evidence": evidence}

        results = await verify_plan_criteria(
            assertions,
            browser=browser,
            model=model,
            hints=hints,
            goal_failure=agent.failure_reason,
            goal_failure_kind=state.get("failure_kind"),
            observed_earlier=state.get("criteria_seen"),
        )
        if shot is not None:
            # Every criterion was judged against this one page state, so this is
            # honestly the evidence for all of them. The sweep results are excluded: each
            # one is about a page the run left long ago, and attaching a screenshot of
            # the last page to a finding about the third would be evidence for the wrong
            # claim.
            results = tuple(
                replace(result, evidence_refs=(shot.artifact_id,)) for result in results
            )
        return {"criterion_results": results + swept, "evidence": evidence}

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
