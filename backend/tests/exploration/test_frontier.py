"""Bounded exploration, with no browser and no model.

Two of the three Phase 12 gates are decided here. An exploration has to end — by budget
or by running out of places to go, never by someone noticing it is still running — and
the map it produces has to distinguish a real change from a page that merely rendered
different text today.
"""

import pytest

from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.domain.exploration.actions import is_takeable
from agentic_qa.domain.exploration.comparison import StateMap, compare
from agentic_qa.domain.exploration.frontier import (
    ExplorationBudget,
    ExplorationProgress,
    ExplorationReport,
    Frontier,
    StopReason,
    stop_reason,
)
from agentic_qa.domain.exploration.state import Affordance, PageState
from agentic_qa.domain.projects.run_policy import RunPolicy

GENEROUS = ExplorationBudget(
    max_actions=1000, max_states=1000, max_depth=10, max_duration_seconds=3600
)


def page(path: str, *names: str, host: str = "https://app.test") -> PageState:
    return PageState(
        url=f"{host}{path}",
        affordances=tuple(Affordance(role="link", name=name) for name in names),
    )


def explore(
    pages: dict[str, PageState], *, budget: ExplorationBudget, start: str = "/"
) -> tuple[Frontier, ExplorationReport]:
    """Walk a fake site until something stops it.

    The loop is the one the real driver will run: ask the frontier for the next thing
    to try, follow it, record where it led. If the frontier ever fails to terminate,
    this hangs — which is exactly the failure the gate is about, so there is no
    iteration cap here to hide it.
    """
    frontier = Frontier(budget)
    frontier.record(pages[start], depth=0)
    elapsed = 0.0
    while True:
        reason = stop_reason(budget, frontier.progress(elapsed_seconds=elapsed))
        if reason is not None:
            return frontier, frontier.report(reason)
        entry = frontier.take()
        assert entry is not None
        elapsed += 1.0
        destination = pages.get(f"/{entry.affordance.name}")
        if destination is not None:
            frontier.record(destination, depth=entry.depth)


class TestExplorationEnds:
    def test_two_pages_linking_to_each_other_do_not_loop_forever(self) -> None:
        # The classic non-termination: A links to B, B links back to A. Nothing about
        # the budgets saves this — what saves it is that an affordance is offered once.
        site = {"/": page("/", "b"), "/b": page("/b", "")}
        site["/b"] = PageState(
            url="https://app.test/b", affordances=(Affordance(role="link", name=""),)
        )
        site["/"] = PageState(
            url="https://app.test/", affordances=(Affordance(role="link", name="b"),)
        )

        _frontier, report = explore(site, budget=GENEROUS)

        assert report.stop_reason is StopReason.FRONTIER_EXHAUSTED
        assert report.complete

    def test_a_fully_connected_site_still_terminates(self) -> None:
        # Every page links to every other page: the worst case for a naive crawler.
        names = ["a", "b", "c", "d"]
        site = {
            f"/{name}": PageState(
                url=f"https://app.test/{name}",
                affordances=tuple(Affordance(role="link", name=other) for other in names),
            )
            for name in names
        }
        site["/"] = PageState(
            url="https://app.test/",
            affordances=tuple(Affordance(role="link", name=name) for name in names),
        )

        _frontier, report = explore(site, budget=GENEROUS)

        assert report.stop_reason is StopReason.FRONTIER_EXHAUSTED
        assert report.states_discovered == 5

    def test_it_stops_on_the_action_budget_and_says_so(self) -> None:
        site = {
            f"/p{index}": PageState(
                url=f"https://app.test/p{index}",
                affordances=(Affordance(role="link", name=f"p{index + 1}"),),
            )
            for index in range(50)
        }
        site["/"] = PageState(
            url="https://app.test/", affordances=(Affordance(role="link", name="p0"),)
        )
        budget = ExplorationBudget(
            max_actions=5, max_states=1000, max_depth=100, max_duration_seconds=3600
        )

        _frontier, report = explore(site, budget=budget)

        assert report.stop_reason is StopReason.MAX_ACTIONS
        assert report.actions_taken == 5
        # Not complete: a comparison against this map must not read the pages it never
        # reached as pages that were removed.
        assert not report.complete

    def test_it_stops_on_the_state_budget(self) -> None:
        site = {
            f"/p{index}": PageState(
                url=f"https://app.test/p{index}",
                affordances=(Affordance(role="link", name=f"p{index + 1}"),),
            )
            for index in range(50)
        }
        site["/"] = PageState(
            url="https://app.test/", affordances=(Affordance(role="link", name="p0"),)
        )
        budget = ExplorationBudget(
            max_actions=1000, max_states=4, max_depth=100, max_duration_seconds=3600
        )

        _frontier, report = explore(site, budget=budget)

        assert report.stop_reason is StopReason.MAX_STATES
        assert report.states_discovered == 4

    def test_depth_prunes_instead_of_stopping(self) -> None:
        # Depth is not a stop reason: reaching the limit means that branch is finished,
        # not that the exploration is. Reporting it as a stop would make a completed
        # crawl look truncated.
        site = {
            f"/p{index}": PageState(
                url=f"https://app.test/p{index}",
                affordances=(Affordance(role="link", name=f"p{index + 1}"),),
            )
            for index in range(20)
        }
        site["/"] = PageState(
            url="https://app.test/", affordances=(Affordance(role="link", name="p0"),)
        )
        budget = ExplorationBudget(
            max_actions=1000, max_states=1000, max_depth=3, max_duration_seconds=3600
        )

        _frontier, report = explore(site, budget=budget)

        assert report.stop_reason is StopReason.FRONTIER_EXHAUSTED
        assert report.max_depth_reached == 3

    def test_the_deadline_ends_it_even_with_places_left(self) -> None:
        progress = ExplorationProgress(
            actions_taken=1, states_discovered=1, elapsed_seconds=3600.0, frontier_size=99
        )

        assert stop_reason(GENEROUS, progress) is StopReason.DEADLINE

    def test_finding_what_it_came_for_outranks_every_budget(self) -> None:
        progress = ExplorationProgress(
            actions_taken=99999,
            states_discovered=99999,
            elapsed_seconds=99999.0,
            frontier_size=0,
            goal_reached=True,
        )

        assert stop_reason(GENEROUS, progress) is StopReason.GOAL_REACHED


class TestTheBudgetCannotExceedThePolicy:
    def policy(self, **overrides: object) -> RunPolicy:
        defaults: dict[str, object] = {
            "policy_id": "pol-1",
            "project_id": "proj-1",
            "allowed_origins": ("https://app.test",),
            "max_duration_seconds": 600,
            "max_actions": 30,
            "max_model_calls": 10,
        }
        defaults.update(overrides)
        return RunPolicy(**defaults)  # type: ignore[arg-type]

    def test_it_inherits_the_policy_limits(self) -> None:
        budget = ExplorationBudget.under(self.policy(max_depth=2))

        assert budget.max_actions == 30
        assert budget.max_duration_seconds == 600.0
        assert budget.max_depth == 2

    def test_a_policy_with_no_depth_limit_still_gets_one(self) -> None:
        # Unbounded depth is how an explorer walks into pagination and never comes back.
        assert ExplorationBudget.under(self.policy()).max_depth == 4

    def test_a_budget_that_permits_nothing_is_refused(self) -> None:
        with pytest.raises(InvalidEntityError):
            ExplorationBudget(max_actions=0, max_states=10, max_depth=1, max_duration_seconds=60)


class TestTheSameStateIsRecognisedAgain:
    def test_a_list_that_grew_by_one_row_is_not_a_new_place(self) -> None:
        # The failure this whole design exists to prevent: without normalisation, every
        # row count is a new state and the crawl never converges.
        before = page("/orders", "order 8821", "order 9007")
        after = page("/orders", "order 8821", "order 9007", "order 9130")

        assert before.signature == after.signature

    def test_the_same_page_under_a_different_id_is_the_same_state(self) -> None:
        assert page("/orders/8821", "cancel").signature == page("/orders/9007", "cancel").signature

    def test_a_query_string_does_not_fork_a_state(self) -> None:
        filtered = PageState(
            url="https://app.test/orders?status=open",
            affordances=(Affordance(role="link", name="new order"),),
        )

        assert filtered.signature == page("/orders", "new order").signature

    def test_render_order_does_not_change_the_signature(self) -> None:
        assert page("/", "a", "b").signature == page("/", "b", "a").signature

    def test_a_page_that_gained_a_control_is_a_different_state(self) -> None:
        # The one change that *is* worth reporting: something new can be done here.
        assert page("/", "a").signature != page("/", "a", "delete everything").signature

    def test_a_visited_state_is_not_re_enqueued(self) -> None:
        frontier = Frontier(GENEROUS)
        state = page("/", "a", "b")

        assert frontier.record(state) is True
        assert frontier.record(state) is False
        assert len(frontier.pending) == 2


class TestTheFrontierIsReproducible:
    def test_two_runs_over_the_same_site_try_things_in_the_same_order(self) -> None:
        site = {
            "/": page("/", "beta", "alpha"),
            "/alpha": page("/alpha", "gamma"),
            "/beta": page("/beta"),
            "/gamma": page("/gamma"),
        }

        first, _ = explore(site, budget=GENEROUS)
        second, _ = explore(site, budget=GENEROUS)

        assert [state.url for state in first.visited] == [state.url for state in second.visited]

    def test_it_goes_broad_before_it_goes_deep(self) -> None:
        # Breadth first finds the shape of an application sooner; a depth-first crawler
        # that stops on budget comes back with one long corridor and no map.
        site = {
            "/": page("/", "a", "b"),
            "/a": page("/a", "a-child"),
            "/b": page("/b"),
            "/a-child": page("/a-child"),
        }
        budget = ExplorationBudget(
            max_actions=2, max_states=1000, max_depth=10, max_duration_seconds=3600
        )

        frontier, _report = explore(site, budget=budget)

        assert {state.route for state in frontier.visited} == {"/", "/a", "/b"}


class TestComparingAgainstABaseline:
    def test_a_page_that_only_changed_its_data_is_not_a_finding(self) -> None:
        baseline = StateMap(states=(page("/orders", "order 8821"),))
        current = StateMap(states=(page("/orders", "order 9007", "order 9130"),))

        assert not compare(baseline, current).has_findings

    def test_a_new_page_is_reported(self) -> None:
        baseline = StateMap(states=(page("/"),))
        current = StateMap(states=(page("/"), page("/admin", "delete user")))

        delta = compare(baseline, current)

        assert [state.route for state in delta.new] == ["/admin"]
        assert not delta.changed

    def test_a_page_that_gained_a_control_is_one_change_not_two(self) -> None:
        # Reported as the same route changing, never as one page vanishing and another
        # appearing: two findings for one edit is how a report stops being read.
        baseline = StateMap(states=(page("/settings", "save"),))
        current = StateMap(states=(page("/settings", "save", "delete account"),))

        delta = compare(baseline, current)

        assert not delta.new and not delta.gone
        assert len(delta.changed) == 1
        change = delta.changed[0]
        assert change.route == "/settings"
        assert change.gained == ("link:delete account",)
        assert change.lost == ()

    def test_a_control_that_disappeared_is_reported_as_lost(self) -> None:
        baseline = StateMap(states=(page("/settings", "save", "export"),))
        current = StateMap(states=(page("/settings", "save"),))

        assert compare(baseline, current).changed[0].lost == ("link:export",)

    def test_a_page_that_is_gone_is_reported_separately(self) -> None:
        baseline = StateMap(states=(page("/"), page("/legacy", "do the old thing")))
        current = StateMap(states=(page("/"),))

        delta = compare(baseline, current)

        assert [state.route for state in delta.gone] == ["/legacy"]
        assert not delta.unreachable_conclusions

    def test_an_incomplete_crawl_flags_its_own_conclusions(self) -> None:
        # The exploration stopped on budget, so "gone" may mean "never reached". Saying
        # so is the difference between a finding and a false alarm.
        baseline = StateMap(states=(page("/"), page("/deep", "x")))
        current = StateMap(states=(page("/"),), complete=False)

        delta = compare(baseline, current)

        assert delta.gone
        assert delta.unreachable_conclusions

    def test_two_identical_maps_produce_nothing(self) -> None:
        same = StateMap(states=(page("/", "a"), page("/a", "b")))

        assert not compare(same, same).has_findings


class TestWhatItDeclinedToTake:
    """Counted, not attempted, and reported either way.

    "Mapped 12 states, left 4 controls alone because this run may not change anything"
    is a different statement from "mapped 12 states", and only one of them lets a
    reader decide whether to run it again with a wider policy.
    """

    def policy(self, *, destructive: bool) -> RunPolicy:
        return RunPolicy(
            policy_id="pol-1",
            project_id="proj-1",
            allowed_origins=("https://app.test",),
            max_duration_seconds=600,
            max_actions=100,
            max_model_calls=0,
            destructive_actions=destructive,
        )

    def state_with_a_button(self) -> PageState:
        return PageState(
            url="https://app.test/",
            affordances=(
                Affordance(role="link", name="records", url="https://app.test/records"),
                Affordance(role="button", name="delete everything"),
                Affordance(role="textbox", name="search"),
            ),
        )

    def test_a_read_only_run_is_offered_the_link_and_not_the_button(self) -> None:
        policy = self.policy(destructive=False)
        frontier = Frontier(GENEROUS, takeable=lambda item: is_takeable(item, policy))

        frontier.record(self.state_with_a_button())

        assert [entry.affordance.name for entry in frontier.pending] == ["records"]
        # The button and the textbox: one forbidden, one not walkable.
        assert frontier.declined == 2

    def test_a_run_allowed_to_change_things_is_offered_the_button(self) -> None:
        policy = self.policy(destructive=True)
        frontier = Frontier(GENEROUS, takeable=lambda item: is_takeable(item, policy))

        frontier.record(self.state_with_a_button())

        assert {entry.affordance.name for entry in frontier.pending} == {
            "records",
            "delete everything",
        }

    def test_an_off_origin_link_is_declined_before_it_is_attempted(self) -> None:
        # The page is untrusted data, links included. Exploration widens nothing.
        policy = self.policy(destructive=False)
        frontier = Frontier(GENEROUS, takeable=lambda item: is_takeable(item, policy))

        frontier.record(
            PageState(
                url="https://app.test/",
                affordances=(Affordance(role="link", name="elsewhere", url="https://evil.test/x"),),
            )
        )

        assert frontier.pending == ()
        assert frontier.declined == 1

    def test_the_count_survives_a_checkpoint(self) -> None:
        policy = self.policy(destructive=False)
        takeable = lambda item: is_takeable(item, policy)  # noqa: E731
        frontier = Frontier(GENEROUS, takeable=takeable)
        frontier.record(self.state_with_a_button())

        resumed = Frontier.from_snapshot(GENEROUS, frontier.snapshot(), takeable=takeable)

        assert resumed.declined == 2
        assert resumed.report(StopReason.FRONTIER_EXHAUSTED).declined == 2


class TestResumingAnExploration:
    def test_a_resumed_frontier_does_not_re_offer_what_it_already_tried(self) -> None:
        # Without the `offered` set, a resumed exploration would walk a two-page cycle
        # forever — having survived the crash and lost the guarantee.
        frontier = Frontier(GENEROUS)
        frontier.record(page("/", "a", "b"))
        first = frontier.take()
        assert first is not None

        resumed = Frontier.from_snapshot(GENEROUS, frontier.snapshot())
        resumed.record(page("/", "a", "b"))

        assert [entry.affordance.key for entry in resumed.pending] == ["link:b"]

    def test_it_remembers_what_it_had_already_spent(self) -> None:
        frontier = Frontier(GENEROUS)
        frontier.record(page("/", "a", "b"))
        frontier.take()
        frontier.take()

        resumed = Frontier.from_snapshot(GENEROUS, frontier.snapshot())

        assert resumed.actions_taken == 2
        assert resumed.states_discovered == 1

    def test_a_fresh_exploration_starts_from_nothing(self) -> None:
        empty = Frontier.from_snapshot(GENEROUS, None)

        assert empty.states_discovered == 0
        assert empty.actions_taken == 0
