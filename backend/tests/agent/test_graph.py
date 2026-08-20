"""Agent graph behaviour over deterministic doubles.

The graph depends on the browser and model *ports*, so its logic can be exercised
without a real browser — which is what lets the durability tests be repeatable
instead of flaky.
"""

from typing import Any

from agentic_qa.application.ports.browser import ActionOutcome
from agentic_qa.domain.agent.state import AgentState
from agentic_qa.domain.browser.actions import (
    ActionTarget,
    BrowserAction,
    BrowserActionType,
    IdempotencyStrategy,
)
from agentic_qa.infrastructure.agent.langgraph.graph import (
    MAX_RECOVERY_ATTEMPTS,
    build_agent_graph,
)
from tests.fakes.agent import RecordingBrowserGateway, ScriptedModelGateway


def navigate(url: str = "http://target.test/records") -> BrowserAction:
    return BrowserAction(
        type=BrowserActionType.NAVIGATE, intent=f"open {url}", target=ActionTarget(url=url)
    )


def click(name: str) -> BrowserAction:
    return BrowserAction(
        type=BrowserActionType.CLICK,
        intent=f"press {name}",
        target=ActionTarget(role="button", name=name),
        side_effect=True,
        idempotency_strategy=IdempotencyStrategy.VERIFY_BEFORE_RETRY,
        verification_strategy="the page confirms it",
    )


async def run_graph(
    *, script: list[BrowserAction], browser: RecordingBrowserGateway, goal: str = "create a record"
) -> Any:
    graph = build_agent_graph(browser=browser, model=ScriptedModelGateway(script=script))
    return await graph.ainvoke({"agent": AgentState(run_id="r-graph", goal=goal)})


async def test_the_graph_executes_the_planned_actions_in_order() -> None:
    browser = RecordingBrowserGateway()

    await run_graph(script=[navigate(), click("Create record")], browser=browser)

    assert browser.executed == ["open http://target.test/records", "press Create record"]


async def test_a_finished_goal_closes_the_episode_with_a_summary() -> None:
    browser = RecordingBrowserGateway()

    result = await run_graph(script=[navigate()], browser=browser)
    agent: AgentState = result["agent"]

    assert agent.goal_reached is True
    assert len(agent.episode_summaries) == 1
    assert agent.episode_summaries[0].succeeded is True
    assert agent.recent_steps == ()  # folded into the summary


async def test_a_failed_action_goes_through_recovery_and_retries() -> None:
    """Recovery owns semantic retries; nothing else re-runs the action."""
    browser = RecordingBrowserGateway(fail_intents={"press Create record"})
    action = click("Create record")
    retry = click("Create record")

    await run_graph(script=[action, retry], browser=browser)

    # Failed once, recovered, and the planner's next action ran.
    assert browser.executed == ["press Create record", "press Create record"]


class AlwaysFailingBrowser(RecordingBrowserGateway):
    async def execute(self, action: BrowserAction) -> ActionOutcome:
        self.executed.append(action.intent)
        return ActionOutcome(succeeded=False, current_url=self.url, detail="never works")


async def test_recovery_gives_up_instead_of_looping_forever() -> None:
    """A step that never succeeds must end the episode, not spin."""
    browser = AlwaysFailingBrowser()
    script = [click("Broken") for _ in range(MAX_RECOVERY_ATTEMPTS + 3)]

    result = await run_graph(script=script, browser=browser)
    agent: AgentState = result["agent"]

    assert agent.failure_reason == "never works"
    assert len(browser.executed) <= MAX_RECOVERY_ATTEMPTS + 1
    assert agent.episode_summaries[0].succeeded is False


async def test_a_failure_is_reported_not_smoothed_over() -> None:
    """The summary of an unrecoverable episode says it failed, and says why."""
    browser = AlwaysFailingBrowser()

    result = await run_graph(script=[click("Broken")], browser=browser)
    agent: AgentState = result["agent"]

    summary = agent.episode_summaries[0]
    assert summary.succeeded is False
    assert summary.summary == "never works"  # the browser's detail, not an invention


async def test_a_step_that_fails_then_succeeds_is_recorded_as_both() -> None:
    """Outcomes are observed per step, so a recovered failure is still visible."""
    browser = RecordingBrowserGateway(fail_intents={"press Create record"})
    state = AgentState(run_id="r-out", goal="fail once then recover")
    graph = build_agent_graph(
        browser=browser,
        model=ScriptedModelGateway(script=[click("Create record"), click("Create record")]),
    )

    await graph.ainvoke({"agent": state})

    # The same mutable state object recorded both attempts before the episode folded.
    assert browser.executed == ["press Create record", "press Create record"]


async def test_marking_a_safe_point_is_the_graphs_job_not_a_database_write() -> None:
    """Nodes decide when a moment is safe; persisting it happens outside the graph."""
    browser = RecordingBrowserGateway()

    result = await run_graph(script=[navigate()], browser=browser)

    assert result["safe_point"] == "episode_closed"


async def test_the_planner_only_ever_sees_a_bounded_context() -> None:
    """What the planner reads must not grow with the length of the run."""
    browser = RecordingBrowserGateway()
    seen: list[int] = []

    class ContextWatchingModel(ScriptedModelGateway):
        async def next_action(self, request: Any) -> Any:
            seen.append(len(request.recent_steps) + len(request.episode_summaries))
            return await super().next_action(request)

    model = ContextWatchingModel(script=[navigate() for _ in range(30)])
    graph = build_agent_graph(browser=browser, model=model)
    await graph.ainvoke({"agent": AgentState(run_id="r-ctx", goal="many steps")})

    from agentic_qa.domain.agent.state import MAX_RECENT_STEPS

    assert max(seen) <= MAX_RECENT_STEPS
    assert len(browser.executed) == 30  # all steps ran, context stayed flat


async def test_an_action_the_page_cannot_satisfy_is_a_failed_step_not_a_crash() -> None:
    """Regression: a planner asking for something unlocatable killed the episode.

    Found by the Phase 09 benchmark, where the real model proposed a `check` whose
    target had no role, label or text. The adapter raised, the exception escaped the
    graph, and the episode died — so Temporal would have retried the whole thing and
    the planner would have proposed the same unusable action again (ADR 0009).

    Recorded as a failed step instead, which is what lets the planner try something
    else, and the run still closes with a safe point rather than an exception.
    """
    from agentic_qa.application.ports.browser import UnperformableActionError

    class UnlocatableBrowser(RecordingBrowserGateway):
        async def execute(self, action: BrowserAction) -> ActionOutcome:
            if action.type is BrowserActionType.CLICK:
                raise UnperformableActionError("action target has no semantic locator")
            return await super().execute(action)

    browser = UnlocatableBrowser()

    result = await run_graph(script=[click("Nowhere"), navigate()], browser=browser)

    agent = result["agent"]
    # Unlike a policy refusal, trying something else is the right response here, so the
    # run stays on the recovery path rather than stopping.
    assert not result["last_denied"]
    # Both the unusable attempt and the recovery are on the record…
    assert agent.step_index == 2
    # …and the run went on to do the next thing instead of dying.
    assert "open http://target.test/records" in browser.executed
    assert agent.failure_reason is None
