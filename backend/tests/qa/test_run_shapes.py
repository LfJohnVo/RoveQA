"""A run may carry a story, a sweep, or both.

Three shapes, and until ADR 0017 only one of them answered anything:

- **story** — a plan's acceptance criteria, checked deterministically where a hint exists.
- **sweep** — no story at all. Every page the run observes gets the universal checks, so
  "do all the reachable pages load" becomes a question the system can answer. It used to
  return `inconclusive` no matter what it had learned.
- **both** — a crawl that also credits a story's criteria as it walks past them. This one
  was never designed; it falls out of exploring plus ADR 0013's continuous verification.

The rule that survives all three: **only a deterministic check may accuse the product**,
and a page answering 500 is deterministic while a noisy console is not.
"""

from dataclasses import dataclass, field
from typing import Any

from agentic_qa.application.ports.browser import ActionOutcome
from agentic_qa.domain.agent.state import AgentState
from agentic_qa.domain.browser.actions import BrowserAction, BrowserActionType
from agentic_qa.domain.exploration.frontier import ExplorationBudget
from agentic_qa.domain.exploration.state import Affordance, PageState
from agentic_qa.domain.projects.run_policy import RunPolicy
from agentic_qa.domain.qa.page_checks import check_page, criterion_id_for
from agentic_qa.domain.qa.test_plan import PlanStep, PlanStepType
from agentic_qa.domain.qa.verification import (
    CriterionOutcome,
    CriterionSource,
    FailureKind,
    derive_verdict,
)
from agentic_qa.domain.runs.run import Verdict
from agentic_qa.infrastructure.agent.langgraph.graph import build_agent_graph
from tests.fakes.agent import ScriptedModelGateway

GENEROUS = ExplorationBudget(
    max_actions=100, max_states=100, max_depth=5, max_duration_seconds=3600
)


def site_page(path: str, *links: str, status: int | None = 200, title: str = "A page") -> PageState:
    return PageState(
        url=f"https://app.test{path}",
        affordances=tuple(
            Affordance(role="link", name=name, url=f"https://app.test/{name}") for name in links
        ),
        title=title,
        http_status=status,
    )


@dataclass
class Site:
    """A site that answers, including badly. Statuses are the point of these tests."""

    pages: dict[str, PageState]
    current: str = "/about:blank"
    visited: list[str] = field(default_factory=list)

    def _path(self, url: str) -> str:
        return url.removeprefix("https://app.test").removeprefix("/")

    async def execute(self, action: BrowserAction) -> ActionOutcome:
        if action.type is BrowserActionType.ASSERT_TEXT:
            here = self.pages.get(self.current)
            found = here is not None and (action.value or "") in here.visible_text
            return ActionOutcome(succeeded=found, detail="" if found else "text not found")

        name = self._path(action.target.url or "")
        self.current = f"/{name}"
        self.visited.append(self.current)
        return ActionOutcome(succeeded=True, current_url=f"https://app.test{self.current}")

    async def capture_screenshot(self) -> bytes:
        return b"png"

    async def current_url(self) -> str | None:
        return f"https://app.test{self.current}"

    async def describe_page(self) -> PageState:
        return self.pages.get(self.current, site_page(self.current, status=None))

    async def aclose(self) -> None:
        return None


def policy() -> RunPolicy:
    return RunPolicy(
        policy_id="pol",
        project_id="proj",
        allowed_origins=("https://app.test",),
        max_duration_seconds=600,
        max_actions=50,
        max_model_calls=0,
        destructive_actions=False,
    )


async def run(
    site: Site, *, assertions: tuple[PlanStep, ...] = (), hints: dict[str, str] | None = None
) -> dict[str, Any]:
    model = ScriptedModelGateway(script=[])
    graph = build_agent_graph(
        browser=site,
        model=model,
        exploration_budget=GENEROUS,
        policy=policy(),
        assertions=assertions,
        hints=hints or {},
    )
    final = await graph.ainvoke({"agent": AgentState(run_id="run-1", goal="check the site")})
    # Every shape here is deterministic. If any of them ever calls a model, that is the
    # finding, not the assertion below.
    assert model.calls == 0
    return dict(final)


CONFIRMED = PlanStep(
    step_id="assert-confirmed",
    type=PlanStepType.ASSERTION,
    description="the confirmation appears",
    criterion_id="ac-confirmed",
)


class TestASweepWithNoStory:
    async def test_every_page_that_answered_is_a_criterion_that_passed(self) -> None:
        site = Site(
            pages={
                "/": site_page("/", "alpha", "beta"),
                "/alpha": site_page("/alpha"),
                "/beta": site_page("/beta"),
            }
        )

        final = await run(site)
        results = final["criterion_results"]

        assert {result.criterion_id for result in results} == {
            "page:/",
            "page:/alpha",
            "page:/beta",
        }
        assert all(result.source is CriterionSource.SWEEP for result in results)
        assert all(result.outcome is CriterionOutcome.MET for result in results)
        # The whole gap this closes: a run with no story now has something to expect, so
        # it gets a verdict instead of falling through to "nobody knows".
        assert derive_verdict(results, expected=[r.criterion_id for r in results]) is Verdict.PASSED

    async def test_a_page_answering_500_fails_the_run(self) -> None:
        site = Site(
            pages={
                "/": site_page("/", "broken"),
                "/broken": site_page("/broken", status=500),
            }
        )

        final = await run(site)
        results = final["criterion_results"]
        broken = next(r for r in results if r.criterion_id == "page:/broken")

        assert broken.outcome is CriterionOutcome.NOT_MET
        assert broken.failure_kind is FailureKind.PRODUCT
        assert derive_verdict(results, expected=[r.criterion_id for r in results]) is Verdict.FAILED

    async def test_a_404_on_a_link_the_site_offers_accuses_the_site(self) -> None:
        # ADR 0015's provenance rule: a crawl only follows links the site published, so a
        # 404 here is the site publishing something it cannot serve.
        site = Site(pages={"/": site_page("/", "gone"), "/gone": site_page("/gone", status=404)})

        final = await run(site)
        gone = next(r for r in final["criterion_results"] if r.criterion_id == "page:/gone")

        assert gone.failure_kind is FailureKind.PRODUCT

    async def test_a_page_with_no_status_is_unverified_rather_than_healthy(self) -> None:
        # A client-side route change makes no navigation response. Calling it healthy is
        # a claim nobody measured.
        site = Site(pages={"/": site_page("/", "spa"), "/spa": site_page("/spa", status=None)})

        final = await run(site)
        spa = next(r for r in final["criterion_results"] if r.criterion_id == "page:/spa")

        assert spa.outcome is CriterionOutcome.UNVERIFIED
        assert spa.failure_kind is None


class TestAStoryAndASweepTogether:
    async def test_both_kinds_of_criterion_come_back_and_say_which_they_are(self) -> None:
        site = Site(
            pages={
                "/": site_page("/", "beta"),
                "/beta": PageState(
                    url="https://app.test/beta",
                    title="Done",
                    http_status=200,
                    body_text="Order confirmed",
                ),
            }
        )

        final = await run(site, assertions=(CONFIRMED,), hints={"ac-confirmed": "Order confirmed"})
        results = final["criterion_results"]
        by_source = {result.source for result in results}

        assert by_source == {CriterionSource.PLAN, CriterionSource.SWEEP}
        story = next(r for r in results if r.source is CriterionSource.PLAN)
        assert story.criterion_id == "ac-confirmed"
        assert story.outcome is CriterionOutcome.MET
        # Credited by walking past it: no planner steered here and no model was asked.
        assert story.model_derived is False

    async def test_a_broken_page_fails_the_run_even_when_the_story_passed(self) -> None:
        # The reason a sweep belongs in a story-driven run at all. A run that walks
        # through a 500 on its way to a passing checkout should say so.
        site = Site(
            pages={
                "/": site_page("/", "beta", "broken"),
                "/beta": PageState(
                    url="https://app.test/beta",
                    title="Done",
                    http_status=200,
                    body_text="Order confirmed",
                ),
                "/broken": site_page("/broken", status=503),
            }
        )

        final = await run(site, assertions=(CONFIRMED,), hints={"ac-confirmed": "Order confirmed"})
        results = final["criterion_results"]

        assert next(r for r in results if r.criterion_id == "ac-confirmed").outcome is (
            CriterionOutcome.MET
        )
        assert derive_verdict(results, expected=[r.criterion_id for r in results]) is Verdict.FAILED


class TestTheCheckItself:
    def test_a_route_is_the_grain_not_a_url(self) -> None:
        # A catalogue of a hundred products must not produce a hundred identical findings.
        first = site_page("/orders/8821")
        second = site_page("/orders/9007")

        assert criterion_id_for(first) == criterion_id_for(second)

    def test_a_missing_title_is_reported_and_does_not_fail_the_page(self) -> None:
        result = check_page(site_page("/", title=""), reached_from_published_link=True)

        assert result.outcome is CriterionOutcome.MET
        assert "no title" in result.observation

    def test_a_404_the_run_chose_itself_accuses_nobody(self) -> None:
        result = check_page(site_page("/guess", status=404), reached_from_published_link=False)

        assert result.outcome is CriterionOutcome.UNVERIFIED
        assert result.failure_kind is None
