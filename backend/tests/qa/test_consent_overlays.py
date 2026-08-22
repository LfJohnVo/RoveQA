"""A consent overlay, and the decision a run is not allowed to take on its own.

Most of these tests assert a *refusal*. That is the point of the feature: "Accept all" is
the easiest button on the public web — larger, higher contrast, first in the DOM — so any
heuristic aiming at "get past the overlay" lands on the most-conceding option by the
site's own design. Accepting cookies is a legal act performed on somebody's behalf, and a
run that did it quietly is a thing nobody finds out about until somebody else does
(ADR 0018).
"""

from agentic_qa.domain.browser.actions import (
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
from agentic_qa.domain.exploration.state import Affordance, PageState
from agentic_qa.domain.projects.run_policy import RunPolicy

# The real thing, from the gate-4 smoke against gov.uk.
GOV_UK = (
    Affordance(role="button", name="Accept additional cookies"),
    Affordance(role="button", name="Reject additional cookies"),
    Affordance(role="link", name="View cookies"),
)
BANNER_TEXT = "We use some essential cookies to make this service work."


def policy(consent: ConsentPolicy = ConsentPolicy.LEAVE) -> RunPolicy:
    return RunPolicy(
        policy_id="pol",
        project_id="proj",
        allowed_origins=("https://app.test",),
        max_duration_seconds=600,
        max_actions=20,
        max_model_calls=0,
        destructive_actions=True,
        consent=consent,
    )


class TestTheDefaultTouchesNothing:
    def test_a_policy_that_says_nothing_says_leave(self) -> None:
        # The default costs runs against a banner-gated site, and that is the trade: a run
        # that fails because a banner was in the way is a visible failure with an obvious
        # remedy. The other direction is invisible.
        assert policy().consent is ConsentPolicy.LEAVE

    def test_it_chooses_nothing_even_when_a_reject_button_is_right_there(self) -> None:
        assert consent_choice(GOV_UK, ConsentPolicy.LEAVE) is None


class TestRejectTakesTheLeastConcedingOption:
    def test_it_prefers_reject_over_accept_whatever_the_order(self) -> None:
        # `Accept` comes first in gov.uk's DOM, as it does almost everywhere. A rule that
        # took the first pressable control would take that one every time.
        choice = consent_choice(GOV_UK, ConsentPolicy.REJECT)

        assert choice is not None
        assert choice.name == "Reject additional cookies"

    def test_it_reads_the_other_words_banners_use(self) -> None:
        for label in ("Only essential cookies", "Necessary only", "Decline", "No, thanks"):
            offered = (
                Affordance(role="button", name="Accept all"),
                Affordance(role="button", name=label),
            )
            choice = consent_choice(offered, ConsentPolicy.REJECT)
            assert choice is not None and choice.name == label, label

    def test_with_nothing_to_reject_it_does_not_settle_for_accepting(self) -> None:
        # The failure this whole module exists to prevent: pressing "Accept" because it
        # was the only button there.
        only_accept = (Affordance(role="button", name="Accept all cookies"),)

        assert consent_choice(only_accept, ConsentPolicy.REJECT) is None

    def test_a_manage_screen_is_taken_before_giving_up(self) -> None:
        # It concedes nothing by itself and it stops the overlay blocking the page.
        offered = (
            Affordance(role="button", name="Accept all"),
            Affordance(role="button", name="Manage preferences"),
        )
        choice = consent_choice(offered, ConsentPolicy.REJECT)

        assert choice is not None and choice.name == "Manage preferences"


class TestAcceptIsNeverInferred:
    def test_it_still_prefers_rejecting_when_the_overlay_offers_it(self) -> None:
        # Even asked to accept, the least-conceding option is the one taken. `accept`
        # means "you may get past this", not "concede as much as possible".
        choice = consent_choice(GOV_UK, ConsentPolicy.ACCEPT)

        assert choice is not None and choice.name == "Reject additional cookies"

    def test_only_accept_reaches_an_accepting_button(self) -> None:
        only_accept = (Affordance(role="button", name="I agree"),)

        assert consent_choice(only_accept, ConsentPolicy.ACCEPT) is not None
        assert consent_choice(only_accept, ConsentPolicy.REJECT) is None


class TestItKnowsAConsentBannerFromACheckout:
    def test_a_page_about_cookies_is_one(self) -> None:
        assert looks_like_consent(BANNER_TEXT)

    def test_a_checkout_with_an_agree_button_is_not(self) -> None:
        # Without this the agent would press "I agree to the terms" on a payment page.
        # That is a purchase, not a consent decision.
        assert not looks_like_consent(
            "Review your order. Total £48.00. I agree to the terms of sale."
        )

    def test_an_unrecognised_banner_is_left_for_a_person(self) -> None:
        # A banner whose buttons say "Sure" and "Maybe later" is one somebody should look
        # at, not one to guess at.
        vague = (Affordance(role="button", name="Sure"), Affordance(role="button", name="Later"))

        assert consent_choice(vague, ConsentPolicy.REJECT) is None
        assert consent_choice(vague, ConsentPolicy.ACCEPT) is None


class TestTheRefusalIsEnforcedOnEveryAction:
    """A planner can propose a click on any affordance, including the banner's.

    Without an enforcement point the consent policy would govern the crawl and be advice
    everywhere else. `act` is the one place every action passes through.
    """

    def page(self) -> PageState:
        return PageState(
            url="https://app.test/",
            affordances=GOV_UK,
            body_text=BANNER_TEXT,
            http_status=200,
        )

    def press(self, name: str) -> BrowserAction:
        return BrowserAction(
            type=BrowserActionType.CLICK,
            intent=f"press {name}",
            target=ActionTarget(role="button", name=name),
            side_effect=True,
            idempotency_strategy=IdempotencyStrategy.VERIFY_BEFORE_RETRY,
            verification_strategy="observe the page",
        )

    def test_the_pieces_the_graph_composes_are_each_true(self) -> None:
        # The graph's `_consent_refusal` needs all three to hold before it refuses. Each
        # is asserted here; the wiring is exercised end to end in the graph tests.
        page = self.page()

        assert looks_like_consent(page.visible_text)
        named = tuple(a for a in page.affordances if a.name == "Accept additional cookies")
        assert consent_choice(named, ConsentPolicy.ACCEPT) is not None
        assert policy().consent is ConsentPolicy.LEAVE

    def test_an_ordinary_button_on_a_consent_page_is_not_caught(self) -> None:
        # The refusal has to be narrow. A cookie banner page that also has a "Search"
        # button must not become a page where nothing can be clicked.
        page = self.page()
        named = tuple(a for a in page.affordances if a.name == "View cookies")

        assert consent_choice(named, ConsentPolicy.ACCEPT) is None


class TestTheGuardActuallyFiresInAGraph:
    """The composition, not the pieces.

    The unit tests above asserted that `looks_like_consent` is true, that
    `consent_choice` finds the button, and that the default is `leave` — all true, and
    the run still pressed "Accept additional cookies" on gov.uk. `_consent_refusal` reads
    `last_page`, and only the observe node was setting it, so an exploring run left the
    guard blind. Found by running it against the real site.
    """

    async def test_an_exploring_run_under_leave_refuses_the_banner(self) -> None:
        from agentic_qa.domain.agent.state import AgentState
        from agentic_qa.domain.exploration.frontier import ExplorationBudget
        from agentic_qa.infrastructure.agent.langgraph.graph import build_agent_graph
        from tests.fakes.agent import RecordingBrowserGateway, ScriptedModelGateway

        browser = RecordingBrowserGateway(
            url="https://app.test/",
            affordances=list(GOV_UK),
            body_text=BANNER_TEXT,
        )
        graph = build_agent_graph(
            browser=browser,
            model=ScriptedModelGateway(script=[]),
            exploration_budget=ExplorationBudget(
                max_actions=4, max_states=4, max_depth=2, max_duration_seconds=60
            ),
            policy=policy(ConsentPolicy.LEAVE),
        )

        await graph.ainvoke({"agent": AgentState(run_id="run-1", goal="explore")})

        pressed = [intent for intent in browser.executed if "Accept" in intent]
        assert pressed == [], f"a run under `leave` pressed a consent button: {pressed}"

    async def test_under_reject_it_presses_the_rejecting_one(self) -> None:
        from agentic_qa.domain.agent.state import AgentState
        from agentic_qa.domain.exploration.frontier import ExplorationBudget
        from agentic_qa.infrastructure.agent.langgraph.graph import build_agent_graph
        from tests.fakes.agent import RecordingBrowserGateway, ScriptedModelGateway

        browser = RecordingBrowserGateway(
            url="https://app.test/",
            affordances=list(GOV_UK),
            body_text=BANNER_TEXT,
        )
        graph = build_agent_graph(
            browser=browser,
            model=ScriptedModelGateway(script=[]),
            exploration_budget=ExplorationBudget(
                max_actions=4, max_states=4, max_depth=2, max_duration_seconds=60
            ),
            policy=policy(ConsentPolicy.REJECT),
        )

        await graph.ainvoke({"agent": AgentState(run_id="run-1", goal="explore")})

        answered = [i for i in browser.executed if i.startswith("answer the consent overlay")]
        assert answered == ["answer the consent overlay: Reject additional cookies"]
