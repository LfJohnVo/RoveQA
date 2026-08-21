"""What a run says when it could not do its job.

The taxonomy in `FailureKind` has existed since Phase 07, and until this phase the
planning path could not actually produce most of it: nothing counted actions, model
calls or elapsed time, so a run that looped ran until Temporal's activity timeout and
came back as an *infrastructure* failure. That is the worst available classification —
it is wrong, and it makes Temporal retry the same loop.

The rule these tests defend: a run that stopped before reaching a criterion has
observed nothing about the product. It must say why it stopped, in the vocabulary a
report uses, and it must never say "the product is broken".
"""

from itertools import count
from typing import Any

from agentic_qa.application.ports.browser import ActionOutcome
from agentic_qa.application.ports.models import PlannedAction, PlanningRequest
from agentic_qa.application.services.guarded_browser import GuardedBrowserGateway
from agentic_qa.domain.agent.state import AgentState
from agentic_qa.domain.browser.actions import (
    ActionTarget,
    BrowserAction,
    BrowserActionType,
    IdempotencyStrategy,
)
from agentic_qa.domain.projects.run_policy import RunPolicy
from agentic_qa.domain.qa.test_plan import PlanStep, PlanStepType
from agentic_qa.domain.qa.verification import CriterionOutcome, FailureKind, derive_verdict
from agentic_qa.domain.runs.run import Verdict
from agentic_qa.infrastructure.agent.langgraph.graph import MAX_RECOVERY_ATTEMPTS, build_agent_graph
from tests.fakes.agent import RecordingBrowserGateway, ScriptedModelGateway

CRITERION = "ac-confirmed"


def policy_for(
    *, max_actions: int = 50, max_model_calls: int = 50, max_duration_seconds: int = 600
) -> RunPolicy:
    return RunPolicy(
        policy_id="pol-1",
        project_id="proj-1",
        allowed_origins=("http://target.test",),
        max_duration_seconds=max_duration_seconds,
        max_actions=max_actions,
        max_model_calls=max_model_calls,
        destructive_actions=False,
    )


def assertion() -> PlanStep:
    return PlanStep(
        step_id="assert-1",
        type=PlanStepType.ASSERTION,
        description="the confirmation page appears",
        criterion_id=CRITERION,
    )


class EndlessPlanner:
    """A planner that never says it is done. The loop a budget exists to stop."""

    def __init__(self) -> None:
        self.calls = 0

    async def next_action(self, request: PlanningRequest) -> PlannedAction:
        self.calls += 1
        return PlannedAction(
            action=BrowserAction(
                type=BrowserActionType.NAVIGATE,
                intent=f"keep looking ({self.calls})",
                target=ActionTarget(url="http://target.test/records"),
            ),
            rationale="still looking",
        )

    async def judge(self, request: Any) -> Any:  # pragma: no cover - never reached
        raise AssertionError("a budget-stopped run must not ask for a judgement")


class DeadModel:
    """Inference is unreachable. A declared failure, never an exception (docs/08)."""

    async def next_action(self, request: PlanningRequest) -> PlannedAction:
        return PlannedAction(action=None, failure="model unavailable: connection refused")

    async def judge(self, request: Any) -> Any:  # pragma: no cover - never reached
        raise AssertionError("a model that cannot plan is not asked to judge")


async def run_episode(
    *,
    model: Any,
    policy: RunPolicy,
    browser: RecordingBrowserGateway | None = None,
    now: Any = None,
    guarded: bool = False,
) -> Any:
    raw = browser or RecordingBrowserGateway()
    graph = build_agent_graph(
        browser=GuardedBrowserGateway(raw, policy) if guarded else raw,
        model=model,
        assertions=(assertion(),),
        hints={CRITERION: "Order confirmed"},
        policy=policy,
        **({"now": now} if now is not None else {}),
    )
    return await graph.ainvoke({"agent": AgentState(run_id="run-1", goal="place an order")})


def verdict_of(final: Any) -> Verdict:
    return derive_verdict(final["criterion_results"], expected=[CRITERION])


class TestARunThatRanOutSaysSo:
    async def test_the_action_budget_stops_an_endless_planner(self) -> None:
        browser = RecordingBrowserGateway()

        final = await run_episode(
            model=EndlessPlanner(), policy=policy_for(max_actions=3), browser=browser
        )

        # It stopped, and it stopped where the policy said — not at a timeout.
        assert len(browser.executed) == 3
        result = final["criterion_results"][0]
        assert result.outcome is CriterionOutcome.NOT_MET
        assert result.failure_kind is FailureKind.AGENT_BUDGET
        assert "3 action(s)" in result.observation

    async def test_a_budget_stop_blocks_the_run_rather_than_failing_it(self) -> None:
        # `blocked` is the honest verdict: the run could not finish, and it observed
        # nothing about the product. `failed` would be an accusation nobody checked.
        final = await run_episode(model=EndlessPlanner(), policy=policy_for(max_actions=2))

        assert verdict_of(final) is Verdict.BLOCKED

    async def test_the_model_call_budget_is_enforced_too(self) -> None:
        planner = EndlessPlanner()

        final = await run_episode(model=planner, policy=policy_for(max_model_calls=2))

        assert planner.calls == 2
        assert final["criterion_results"][0].failure_kind is FailureKind.AGENT_BUDGET

    async def test_the_duration_budget_is_enforced_too(self) -> None:
        # An injected clock rather than a sleep: the condition is observable, and a
        # test that waited ten minutes would be a test nobody runs.
        ticks = count(start=0, step=400.0)

        final = await run_episode(
            model=EndlessPlanner(),
            policy=policy_for(max_duration_seconds=600),
            now=lambda: next(ticks),
        )

        result = final["criterion_results"][0]
        assert result.failure_kind is FailureKind.AGENT_BUDGET
        assert "600s" in result.observation

    async def test_a_budget_stopped_run_never_blames_the_product(self) -> None:
        final = await run_episode(model=EndlessPlanner(), policy=policy_for(max_actions=1))

        assert not any(result.is_product_defect for result in final["criterion_results"])


class TestOtherReasonsAreClassifiedToo:
    async def test_a_policy_refusal_blocks_the_run(self) -> None:
        """It used to come back inconclusive.

        The policy stopping a run is a fact about the run, not a mystery — and a
        report that cannot tell "we were not allowed" from "nobody could tell" cannot
        be acted on.
        """

        class WantsToClick:
            async def next_action(self, request: PlanningRequest) -> PlannedAction:
                return PlannedAction(
                    action=BrowserAction(
                        type=BrowserActionType.CLICK,
                        intent="press Pay",
                        target=ActionTarget(role="button", name="Pay"),
                        side_effect=True,
                        idempotency_strategy=IdempotencyStrategy.VERIFY_BEFORE_RETRY,
                        verification_strategy="the page confirms it",
                    )
                )

            async def judge(self, request: Any) -> Any:  # pragma: no cover
                raise AssertionError("a denied run is not judged by a model")

        final = await run_episode(model=WantsToClick(), policy=policy_for(), guarded=True)

        result = final["criterion_results"][0]
        assert result.failure_kind is FailureKind.POLICY
        assert verdict_of(final) is Verdict.BLOCKED

    async def test_an_unavailable_model_blocks_the_run(self) -> None:
        final = await run_episode(model=DeadModel(), policy=policy_for())

        result = final["criterion_results"][0]
        assert result.failure_kind is FailureKind.MODEL
        assert verdict_of(final) is Verdict.BLOCKED

    async def test_a_page_failure_nobody_explained_stays_unclassified(self) -> None:
        """Deliberately inconclusive.

        An action that failed on the page could be a broken environment or a broken
        product. Guessing between them is exactly the guess that makes a report
        untrustworthy, so the run says it does not know.
        """
        browser = RecordingBrowserGateway(fail_intents={"open http://target.test/records"})
        script = [
            BrowserAction(
                type=BrowserActionType.NAVIGATE,
                intent="open http://target.test/records",
                target=ActionTarget(url="http://target.test/records"),
            )
        ]

        final = await run_episode(
            model=ScriptedModelGateway(script=script), policy=policy_for(), browser=browser
        )

        result = final["criterion_results"][0]
        assert result.outcome is CriterionOutcome.UNVERIFIED
        assert result.failure_kind is None
        assert verdict_of(final) is Verdict.INCONCLUSIVE


async def test_a_run_that_finishes_within_its_budget_is_unaffected() -> None:
    # The bound must not change what a healthy run reports.
    browser = RecordingBrowserGateway()
    script = [
        BrowserAction(
            type=BrowserActionType.NAVIGATE,
            intent="open the confirmation",
            target=ActionTarget(url="http://target.test/records"),
        )
    ]

    final = await run_episode(
        model=ScriptedModelGateway(script=script), policy=policy_for(), browser=browser
    )

    assert final["criterion_results"][0].failure_kind is not FailureKind.AGENT_BUDGET
    # One agent action plus the deterministic check of the criterion. Only the first
    # counts against the budget: verifying what a run was asked to verify is not the
    # agent spending its allowance, and counting it would make `max_actions=1` a run
    # that can act once and never check.
    assert browser.executed == ["open the confirmation", f"verify criterion {CRITERION}"]


async def test_the_default_double_outcome_is_still_honoured() -> None:
    """Sanity on the fixture: the recording browser reports success by default, so a
    classification below could not be an artefact of a browser that always fails."""
    assert (
        await RecordingBrowserGateway().execute(
            BrowserAction(
                type=BrowserActionType.NAVIGATE,
                intent="open",
                target=ActionTarget(url="http://target.test/"),
            )
        )
    ) == ActionOutcome(succeeded=True, current_url="http://target.test/")


class TestThePlannerIsToldWhereTheApplicationIs:
    """The soak of Phase 14 found this: 22 runs out of 22 ended `blocked` with kind
    `model`, because the planner kept proposing a navigation with no url.

    It had none to propose. A run starts on `about:blank`, and the only thing that knows
    the application's address is the RunPolicy allowlist — which was used purely as a
    fence. The planner guessed, and the same allowlist refused the guess.
    """

    def test_the_allowed_origins_reach_the_prompt(self) -> None:
        from agentic_qa.infrastructure.inference.prompts import build_planning_prompt

        prompt = build_planning_prompt(
            PlanningRequest(
                goal="open the application",
                observation="about:blank",
                allowed_origins=("https://app.test", "https://admin.app.test"),
            )
        )

        assert "<allowed_origins>" in prompt
        assert "https://app.test" in prompt
        assert "https://admin.app.test" in prompt

    def test_a_request_without_a_policy_says_nothing_about_origins(self) -> None:
        # Silence rather than an empty block: a section with nothing in it reads as
        # "you may go nowhere", which is not what an unconstrained request means.
        from agentic_qa.infrastructure.inference.prompts import build_planning_prompt

        prompt = build_planning_prompt(
            PlanningRequest(goal="open the application", observation="about:blank")
        )

        assert "<allowed_origins>" not in prompt

    async def test_the_graph_takes_them_from_the_policy(self) -> None:
        seen: list[PlanningRequest] = []

        class Recording:
            async def next_action(self, request: PlanningRequest) -> PlannedAction:
                seen.append(request)
                return PlannedAction(action=None, rationale="done")

            async def judge(self, request: Any) -> Any:  # pragma: no cover
                raise AssertionError("not reached")

        await run_episode(model=Recording(), policy=policy_for())

        assert seen[0].allowed_origins == ("http://target.test",)


class TestThePlannerIsToldWhatEachActionNeeds:
    """The 90-minute soak of Phase 14 ended 91 runs out of 91 `blocked`, every one of
    them on an action the domain refused: `wait_for` with no target (65) or `navigate`
    with no url (26).

    The domain has always required these. The prompt listed the action *names* and
    stopped there, so the planner was being graded on a rule nobody had told it. The
    lists below are rendered from the domain's own frozensets, which is what keeps the
    two from drifting apart again.
    """

    def test_every_action_that_needs_a_target_is_named_in_the_prompt(self) -> None:
        from agentic_qa.domain.browser.actions import NEEDS_TARGET
        from agentic_qa.infrastructure.inference.prompts import SYSTEM_PROMPT

        for action in NEEDS_TARGET:
            assert action.value in SYSTEM_PROMPT, f"{action.value} needs a target, unsaid"

    def test_every_action_that_needs_a_value_is_named_in_the_prompt(self) -> None:
        from agentic_qa.domain.browser.actions import NEEDS_VALUE
        from agentic_qa.infrastructure.inference.prompts import SYSTEM_PROMPT

        for action in NEEDS_VALUE:
            assert action.value in SYSTEM_PROMPT, f"{action.value} needs a value, unsaid"

    def test_the_prompt_says_navigate_needs_a_url(self) -> None:
        from agentic_qa.infrastructure.inference.prompts import SYSTEM_PROMPT

        assert "target.url" in SYSTEM_PROMPT

    def test_the_prompt_version_moved_with_the_wording(self) -> None:
        # A result is only comparable to another when both name the prompt that
        # produced them, and this wording changes what the planner proposes.
        from agentic_qa.infrastructure.inference.prompts import PLANNING_PROMPT_VERSION

        assert PLANNING_PROMPT_VERSION == "planner.v4"


class TestThePlannerIsShownThePage:
    """The demo of Phase 14 found this, and the evidence it captured said it outright.

    A planner was given the page's *url* and nothing else, then asked which element to
    act on. It could only invent one, and each invention cost a ten-second locator
    timeout and a recovery attempt until the episode ran out. `describe_page` had been
    returning roles and accessible names since the exploration work; it was simply
    never wired to the path that plans.
    """

    async def test_the_observation_names_what_the_page_offers(self) -> None:
        from agentic_qa.domain.exploration.state import Affordance

        seen: list[PlanningRequest] = []

        class Recording:
            async def next_action(self, request: PlanningRequest) -> PlannedAction:
                seen.append(request)
                return PlannedAction(action=None, rationale="done")

            async def judge(self, request: Any) -> Any:  # pragma: no cover
                raise AssertionError("not reached")

        browser = RecordingBrowserGateway(
            affordances=[
                Affordance(role="link", name="Projects", url="http://target.test/projects"),
                Affordance(role="button", name="New run"),
            ]
        )
        await run_episode(model=Recording(), browser=browser, policy=policy_for())

        observation = seen[0].observation
        assert "Projects" in observation
        assert "New run" in observation
        assert "button" in observation

    def test_a_page_offering_nothing_says_so_instead_of_looking_empty(self) -> None:
        from agentic_qa.domain.exploration.state import PageState

        described = PageState(url="http://target.test/").describe()

        # An empty element list and a page that was never described must not read the
        # same to a planner: one means "there is nothing to click", the other means
        # "nobody looked".
        assert "no interactive elements" in described

    def test_the_description_is_bounded(self) -> None:
        from agentic_qa.domain.exploration.state import (
            MAX_DESCRIBED_AFFORDANCES,
            Affordance,
            PageState,
        )

        crowded = PageState(
            url="http://target.test/",
            affordances=tuple(Affordance(role="link", name=f"row {index}") for index in range(500)),
        )
        described = crowded.describe()

        assert described.count("- link:") == MAX_DESCRIBED_AFFORDANCES
        # And it says so, because a planner that thinks it has seen the whole page will
        # conclude something is absent when it was only cut off.
        assert "and 460 more" in described


class TestARefusedProposalIsNotTheEndOfTheRun:
    """A proposal the domain refuses and a model that cannot be reached both used to
    arrive as one string, and both ended the episode on the spot.

    They are not the same thing. A refusal is something the planner can fix once it is
    told what was wrong; a dead endpoint will be just as dead next call. Flattening
    them cost a whole run for one malformed proposal — which is how every run in the
    Phase 14 soak ended.
    """

    async def test_the_planner_gets_another_turn_and_is_told_why(self) -> None:
        prompts: list[PlanningRequest] = []

        class SlipsOnce:
            def __init__(self) -> None:
                self.calls = 0

            async def next_action(self, request: PlanningRequest) -> PlannedAction:
                prompts.append(request)
                self.calls += 1
                if self.calls == 1:
                    return PlannedAction(
                        action=None,
                        failure="planner proposed an invalid action: assert_url requires a value",
                        rejected=True,
                    )
                return PlannedAction(
                    action=BrowserAction(
                        type=BrowserActionType.NAVIGATE,
                        intent="go to the records page",
                        target=ActionTarget(url="http://target.test/records"),
                    ),
                )

            async def judge(self, request: Any) -> Any:  # pragma: no cover
                raise AssertionError("not reached")

        planner = SlipsOnce()
        browser = RecordingBrowserGateway()
        await run_episode(model=planner, browser=browser, policy=policy_for(max_actions=2))

        assert planner.calls > 1, "a refused proposal must not end the episode"
        # And the second prompt carries the reason, or the retry is a coin toss.
        retried = prompts[1]
        assert any("assert_url requires a value" in step.detail for step in retried.recent_steps)
        assert "go to the records page" in browser.executed

    async def test_an_unreachable_model_still_ends_the_episode(self) -> None:
        # The distinction has to cut both ways: retrying a dead endpoint inside the
        # episode asks the same question of the same silence.
        class Unreachable:
            def __init__(self) -> None:
                self.calls = 0

            async def next_action(self, request: PlanningRequest) -> PlannedAction:
                self.calls += 1
                return PlannedAction(action=None, failure="model unavailable: connection refused")

            async def judge(self, request: Any) -> Any:  # pragma: no cover
                raise AssertionError("not reached")

        planner = Unreachable()
        final = await run_episode(model=planner, policy=policy_for())

        assert planner.calls == 1
        assert final["criterion_results"][0].failure_kind is FailureKind.MODEL
        assert verdict_of(final) is Verdict.BLOCKED

    async def test_a_planner_that_only_slips_still_stops(self) -> None:
        # Recovery is bounded. A planner that never produces a legal action must end
        # the run rather than spend every model call it has on the same mistake.
        class AlwaysSlips:
            def __init__(self) -> None:
                self.calls = 0

            async def next_action(self, request: PlanningRequest) -> PlannedAction:
                self.calls += 1
                return PlannedAction(
                    action=None,
                    failure="planner proposed an invalid action: click requires a semantic target",
                    rejected=True,
                )

            async def judge(self, request: Any) -> Any:  # pragma: no cover
                raise AssertionError("not reached")

        planner = AlwaysSlips()
        final = await run_episode(model=planner, policy=policy_for())

        assert planner.calls <= MAX_RECOVERY_ATTEMPTS + 1
        assert verdict_of(final) is not Verdict.PASSED


class TestThePlannerIsToldWhatCountsAsDone:
    """Phase 15, slices 6 and 9.

    The plan's literals reached only the final verification node, and the one frozenset
    that would have stopped the planner over-declaring `side_effect` was the one the
    prompt did not render. Both are information the process held and did not hand over.
    """

    def test_the_prompt_names_the_read_only_actions(self) -> None:
        from agentic_qa.domain.browser.actions import READ_ONLY_ACTIONS
        from agentic_qa.infrastructure.inference.prompts import _READ_ONLY_ACTIONS, SYSTEM_PROMPT

        rendered = SYSTEM_PROMPT
        for action in READ_ONLY_ACTIONS:
            assert action.value in _READ_ONLY_ACTIONS
        assert "must not be marked side_effect" in rendered

    def test_a_criterion_with_a_literal_arrives_with_it(self) -> None:
        from agentic_qa.application.ports.models import PlanCriterion, PlanningRequest
        from agentic_qa.infrastructure.inference.prompts import build_planning_prompt

        prompt = build_planning_prompt(
            PlanningRequest(
                goal="see the screen",
                observation="url: https://app.test/",
                criteria=(
                    PlanCriterion(
                        criterion_id="ac-title",
                        description="the screen shows its title",
                        expected_text="Sign in",
                    ),
                ),
            )
        )

        assert "<acceptance_criteria>" in prompt
        assert "ac-title" in prompt
        assert '"Sign in"' in prompt

    def test_a_criterion_without_a_literal_says_so(self) -> None:
        # Otherwise the planner invents one, and an invented literal asserted against
        # the page is a deterministic check of something nobody asked for.
        from agentic_qa.application.ports.models import PlanCriterion, PlanningRequest
        from agentic_qa.infrastructure.inference.prompts import build_planning_prompt

        prompt = build_planning_prompt(
            PlanningRequest(
                goal="see the screen",
                observation="url: https://app.test/",
                criteria=(
                    PlanCriterion(criterion_id="ac-vibe", description="it feels responsive"),
                ),
            )
        )

        assert "not assertable" in prompt

    def test_no_criteria_means_no_section(self) -> None:
        from agentic_qa.application.ports.models import PlanningRequest
        from agentic_qa.infrastructure.inference.prompts import build_planning_prompt

        prompt = build_planning_prompt(
            PlanningRequest(goal="explore", observation="url: https://app.test/")
        )

        assert "<acceptance_criteria>" not in prompt
