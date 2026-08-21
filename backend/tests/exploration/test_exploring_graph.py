"""The agent graph in exploration mode.

The claim being tested is not "it clicks things". It is that an exploring episode calls
**no model at all** — the frontier decides from what the page offers — and that it stops
on its own: on the frontier running dry, or on a budget, never on somebody noticing it
is still going.
"""

from dataclasses import dataclass, field

from agentic_qa.application.ports.browser import ActionOutcome
from agentic_qa.domain.agent.state import AgentState
from agentic_qa.domain.browser.actions import BrowserAction
from agentic_qa.domain.exploration.frontier import (
    ExplorationBudget,
    ExplorationReport,
    FrontierSnapshot,
)
from agentic_qa.domain.exploration.state import Affordance, PageState
from agentic_qa.domain.projects.run_policy import RunPolicy
from agentic_qa.domain.qa.verification import FailureKind
from agentic_qa.infrastructure.agent.langgraph.graph import build_agent_graph
from tests.fakes.agent import ScriptedModelGateway

GENEROUS = ExplorationBudget(
    max_actions=100, max_states=100, max_depth=5, max_duration_seconds=3600
)


def _path_of(url: str) -> str:
    """`https://app.test/alpha` -> `alpha`, and the root -> the empty string.

    The trailing slash is stripped separately because a policy origin is normalised
    without one, and the seed navigates to exactly that string.
    """
    return url.removeprefix("https://app.test").removeprefix("/")


def page(path: str, *names: str) -> PageState:
    """A page whose links carry their destination, as a real snapshot does."""
    return PageState(
        url=f"https://app.test{path}",
        affordances=tuple(
            Affordance(role="link", name=name, url=f"https://app.test/{name}") for name in names
        ),
    )


@dataclass
class SiteBrowser:
    """A fake site: clicking a link named `x` navigates to `/x`.

    Records what it was asked to do, which is how the tests below check that the same
    affordance is never taken twice.
    """

    pages: dict[str, PageState]
    current: str = "/"
    clicked: list[str] = field(default_factory=list)
    described: int = 0
    unclickable: set[str] = field(default_factory=set)

    async def execute(self, action: BrowserAction) -> ActionOutcome:
        # Exploration navigates when the page said where a link goes, and clicks only
        # when it did not — so this fake reads both.
        name = _path_of(action.target.url) if action.target.url else action.target.name
        self.clicked.append(name or "")
        if name in self.unclickable:
            return ActionOutcome(succeeded=False, detail="nothing happened")
        destination = f"/{name}"
        if destination in self.pages:
            self.current = destination
        return ActionOutcome(succeeded=True, current_url=f"https://app.test{self.current}")

    async def capture_screenshot(self) -> bytes:
        return b"png"

    async def current_url(self) -> str | None:
        return f"https://app.test{self.current}"

    async def describe_page(self) -> PageState:
        self.described += 1
        return self.pages.get(self.current, page(self.current))

    async def aclose(self) -> None:
        return None


async def explore(browser: SiteBrowser, budget: ExplorationBudget = GENEROUS) -> AgentState:
    model = ScriptedModelGateway(script=[])
    graph = build_agent_graph(browser=browser, model=model, exploration_budget=budget)
    result = await graph.ainvoke(
        {"agent": AgentState(run_id="run-1", goal="explore the application")}
    )
    agent = result["agent"]
    assert isinstance(agent, AgentState)
    # The property that makes exploration cheap, asserted on every path below.
    assert model.calls == 0
    return agent


async def test_it_walks_a_small_site_and_stops_when_there_is_nowhere_left() -> None:
    browser = SiteBrowser(
        pages={
            "/": page("/", "alpha", "beta"),
            "/alpha": page("/alpha", "gamma"),
            "/beta": page("/beta"),
            "/gamma": page("/gamma"),
        }
    )

    agent = await explore(browser)

    assert sorted(browser.clicked) == ["alpha", "beta", "gamma"]
    # Frontier exhausted: everything reachable was reached, which is a complete run.
    assert agent.goal_reached is True
    assert agent.failure_reason is None


async def test_a_cycle_does_not_become_an_infinite_walk() -> None:
    # Two pages linking to each other. Nothing about the budget saves this — what
    # saves it is that an affordance is offered once.
    browser = SiteBrowser(pages={"/": page("/", "b"), "/b": page("/b", "")})
    browser.pages["/b"] = PageState(
        url="https://app.test/b",
        affordances=(Affordance(role="link", name="home", url="https://app.test/"),),
    )

    agent = await explore(browser)

    assert agent.goal_reached is True
    # Each link taken exactly once, and then nowhere left to go. "" is the root.
    assert sorted(browser.clicked) == ["", "b"]


async def test_it_stops_on_the_action_budget_and_says_why() -> None:
    corridor = {f"/p{index}": page(f"/p{index}", f"p{index + 1}") for index in range(40)}
    corridor["/"] = page("/", "p0")
    budget = ExplorationBudget(
        max_actions=3, max_states=100, max_depth=100, max_duration_seconds=3600
    )

    agent = await explore(SiteBrowser(pages=corridor), budget)

    # Not a pass: the map has holes, and a report built on it must not claim otherwise.
    assert agent.goal_reached is False
    assert agent.failure_reason == "exploration stopped: max_actions"


async def test_a_dead_link_does_not_stall_the_exploration() -> None:
    # A click that does nothing is a failed step. An exploring run must not re-plan it:
    # the affordance is already out of the frontier, and asking again is how a broken
    # link becomes an infinite loop.
    browser = SiteBrowser(
        pages={"/": page("/", "broken", "works"), "/works": page("/works")},
        unclickable={"broken"},
    )

    agent = await explore(browser)

    # Both were taken, the broken one once. The raw steps are folded into the episode
    # summary at close (context compaction, docs/05), so the count is what survives.
    assert sorted(browser.clicked) == ["broken", "works"]
    assert agent.episode_summaries[-1].steps_taken == 2
    assert agent.goal_reached is True


async def test_depth_bounds_how_far_it_walks() -> None:
    corridor = {f"/p{index}": page(f"/p{index}", f"p{index + 1}") for index in range(10)}
    corridor["/"] = page("/", "p0")
    budget = ExplorationBudget(
        max_actions=100, max_states=100, max_depth=2, max_duration_seconds=3600
    )

    agent = await explore(SiteBrowser(pages=corridor), budget)

    # Depth prunes rather than stops: the exploration finished what it was allowed to
    # reach, so it is complete, not truncated.
    assert agent.goal_reached is True
    assert browser_clicks_within_depth(corridor, budget.max_depth)


def browser_clicks_within_depth(pages: dict[str, PageState], max_depth: int) -> bool:
    """Sanity check on the fixture rather than on the code under test."""
    return len(pages) > max_depth


async def test_a_page_that_offers_nothing_ends_the_exploration_immediately() -> None:
    browser = SiteBrowser(pages={"/": page("/")})

    agent = await explore(browser)

    assert browser.clicked == []
    assert agent.goal_reached is True


def crawlable_policy(origin: str = "https://app.test") -> RunPolicy:
    """Read-only, which is the mode a crawl of somebody else's site deserves."""
    return RunPolicy(
        policy_id="pol-explore",
        project_id="proj-explore",
        allowed_origins=(origin,),
        max_duration_seconds=600,
        max_actions=50,
        max_model_calls=0,
        destructive_actions=False,
    )


async def explore_with_policy(
    browser: SiteBrowser, policy: RunPolicy, budget: ExplorationBudget = GENEROUS
) -> dict[str, object]:
    model = ScriptedModelGateway(script=[])
    graph = build_agent_graph(
        browser=browser, model=model, exploration_budget=budget, policy=policy
    )
    result = await graph.ainvoke(
        {"agent": AgentState(run_id="run-1", goal="explore the application")}
    )
    assert model.calls == 0
    return dict(result)


class TestAnExplorationFindsItsOwnWayToTheApplication:
    """A browser opens on `about:blank`, and nothing in production ever navigated away
    from it. An exploring run therefore mapped exactly one state — the blank one — and
    reported it as a *complete* map.

    The Phase 12 gate passed anyway, because the test called `page.goto` itself before
    building the graph. A gate that supplies the step it is checking is not a gate.
    """

    async def test_it_navigates_to_the_policy_origin_first(self) -> None:
        # Starts where a real browser starts: nowhere.
        browser = SiteBrowser(
            pages={
                "/": page("/", "alpha", "beta"),
                "/alpha": page("/alpha"),
                "/beta": page("/beta"),
            },
            current="/about:blank",
        )

        agent = (await explore_with_policy(browser, crawlable_policy()))["agent"]
        assert isinstance(agent, AgentState)

        # The seed is the first thing it does, and it goes through the ordinary action
        # path — so it is bounded and policed like every other step.
        assert browser.clicked[0] == ""
        assert sorted(browser.clicked[1:]) == ["alpha", "beta"]
        assert agent.goal_reached is True

    async def test_it_maps_more_than_one_state_without_help(self) -> None:
        browser = SiteBrowser(
            pages={
                "/": page("/", "alpha"),
                "/alpha": page("/alpha", "beta"),
                "/beta": page("/beta"),
            },
            current="/about:blank",
        )

        result = await explore_with_policy(browser, crawlable_policy())

        report = result["exploration_report"]
        assert isinstance(report, ExplorationReport)
        # The blank page is not one of them: it is never described, so it never becomes
        # a state. Three real pages, reached without the test touching the browser.
        assert report.states_discovered == 3

    async def test_an_unreachable_origin_is_blocked_with_a_cause(self) -> None:
        # Nothing at the other end. The run must say so — `frontier_exhausted` would
        # claim it had seen the whole application, which is the opposite of the truth.
        browser = SiteBrowser(pages={}, current="/about:blank", unclickable={""})

        result = await explore_with_policy(browser, crawlable_policy())

        agent = result["agent"]
        assert isinstance(agent, AgentState)
        assert agent.goal_reached is False
        assert result["failure_kind"] is FailureKind.ENVIRONMENT
        assert result.get("exploration_report") is None

    async def test_a_resumed_crawl_does_not_start_over(self) -> None:
        # `exploration is None` is what "not seeded yet" means, so a state that already
        # carries a frontier must go straight back to crawling. Re-seeding would send a
        # browser that died on page nine back to page one.
        browser = SiteBrowser(pages={"/": page("/", "alpha"), "/alpha": page("/alpha")})
        model = ScriptedModelGateway(script=[])
        graph = build_agent_graph(
            browser=browser,
            model=model,
            exploration_budget=GENEROUS,
            policy=crawlable_policy(),
        )

        result = await graph.ainvoke(
            {
                "agent": AgentState(run_id="run-1", goal="explore the application"),
                "exploration": FrontierSnapshot(),
            }
        )

        assert isinstance(result["agent"], AgentState)
        # No seed navigation: the first thing it did was take a link off the page it was
        # already on.
        assert browser.clicked == ["alpha"]
