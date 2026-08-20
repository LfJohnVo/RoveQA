"""Storing a map and comparing it against the last one.

Parametrized over the in-memory double and PostgreSQL, because the property that
matters is the one a double is most likely to fake: a state read back out of storage
has to hash to the same signature it had going in. If it does not, every stored state
looks new the next night and the report is noise.
"""

from collections.abc import Callable

import pytest

from agentic_qa.application.errors import NotFoundError
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.application.queries.exploration_report import exploration_outcome
from agentic_qa.domain.exploration.comparison import StateMap
from agentic_qa.domain.exploration.frontier import (
    ExplorationBudget,
    ExplorationReport,
    StopReason,
)
from agentic_qa.domain.exploration.state import Affordance, PageState
from agentic_qa.domain.runs.run import Run, RunStatus, Verdict
from tests.conftest import seed_project_with_default_policy

Factory = Callable[[], UnitOfWork]

BUDGET = ExplorationBudget(max_actions=50, max_states=20, max_depth=3, max_duration_seconds=600)


def page(path: str, *names: str) -> PageState:
    return PageState(
        url=f"https://app.test{path}",
        title=f"page {path}",
        affordances=tuple(Affordance(role="link", name=name) for name in names),
    )


def report(
    reason: StopReason = StopReason.FRONTIER_EXHAUSTED, *, states: int = 1, declined: int = 0
) -> ExplorationReport:
    return ExplorationReport(
        stop_reason=reason,
        actions_taken=states,
        states_discovered=states,
        max_depth_reached=1,
        frontier_remaining=0,
        budget=BUDGET,
        declined=declined,
    )


async def seed_run(factory: Factory, project_id: str, run_id: str) -> None:
    async with factory() as uow:
        await uow.runs.add(
            Run(
                run_id=run_id,
                project_id=project_id,
                status=RunStatus.COMPLETED,
                verdict=Verdict.PASSED,
            )
        )
        await uow.commit()


async def store(
    factory: Factory,
    project_id: str,
    run_id: str,
    states: tuple[PageState, ...],
    *,
    complete: bool = True,
    reason: StopReason = StopReason.FRONTIER_EXHAUSTED,
    declined: int = 0,
) -> None:
    await seed_run(factory, project_id, run_id)
    async with factory() as uow:
        await uow.state_maps.record(
            run_id,
            project_id,
            StateMap(states=states, complete=complete),
            report(reason, states=len(states), declined=declined),
        )
        await uow.commit()


class TestAMapSurvivesStorage:
    async def test_a_state_read_back_has_the_same_signature(
        self, unit_of_work_factory: Factory
    ) -> None:
        # The property everything else rests on. If a stored state hashed differently,
        # every page would look new the next night and the report would be noise.
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        original = page("/records", "new record", "order 8821")
        await store(unit_of_work_factory, project_id, "run-1", (original,))

        async with unit_of_work_factory() as uow:
            stored = await uow.state_maps.get("run-1")

        assert stored is not None
        assert stored.states[0].signature == original.signature

    async def test_the_report_comes_back_with_what_it_spent(
        self, unit_of_work_factory: Factory
    ) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        await store(
            unit_of_work_factory,
            project_id,
            "run-1",
            (page("/"),),
            complete=False,
            reason=StopReason.MAX_ACTIONS,
            declined=3,
        )

        async with unit_of_work_factory() as uow:
            stored = await uow.state_maps.report_for("run-1")

        assert stored is not None
        assert stored.stop_reason is StopReason.MAX_ACTIONS
        assert stored.complete is False
        assert stored.declined == 3

    async def test_recording_twice_does_not_double_the_states(
        self, unit_of_work_factory: Factory
    ) -> None:
        # What a retried activity does. It explored the same application.
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        states = (page("/"), page("/records", "new record"))
        await store(unit_of_work_factory, project_id, "run-1", states)

        async with unit_of_work_factory() as uow:
            await uow.state_maps.record(
                "run-1", project_id, StateMap(states=states), report(states=2)
            )
            await uow.commit()

        async with unit_of_work_factory() as uow:
            stored = await uow.state_maps.get("run-1")
        assert stored is not None
        assert len(stored.states) == 2

    async def test_a_run_that_did_not_explore_has_no_map(
        self, unit_of_work_factory: Factory
    ) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        await seed_run(unit_of_work_factory, project_id, "run-planned")

        async with unit_of_work_factory() as uow:
            assert await uow.state_maps.get("run-planned") is None
            assert await uow.state_maps.report_for("run-planned") is None


class TestComparingAgainstTheLastExploration:
    async def test_the_first_exploration_has_no_delta(self, unit_of_work_factory: Factory) -> None:
        # Discovering the whole application is not forty findings.
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        await store(unit_of_work_factory, project_id, "run-1", (page("/"), page("/records")))

        async with unit_of_work_factory() as uow:
            outcome = await exploration_outcome(uow, "run-1")

        assert outcome.baseline_run_id is None
        assert outcome.delta is None
        assert outcome.report.states_discovered == 2

    async def test_a_page_that_only_changed_its_data_is_not_a_finding(
        self, unit_of_work_factory: Factory
    ) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        await store(unit_of_work_factory, project_id, "run-1", (page("/orders", "order 8821"),))
        await store(
            unit_of_work_factory,
            project_id,
            "run-2",
            (page("/orders", "order 9007", "order 9130"),),
        )

        async with unit_of_work_factory() as uow:
            outcome = await exploration_outcome(uow, "run-2")

        assert outcome.baseline_run_id == "run-1"
        assert outcome.delta is not None
        assert not outcome.delta.has_findings

    async def test_a_page_that_gained_a_control_is_reported_once(
        self, unit_of_work_factory: Factory
    ) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        await store(unit_of_work_factory, project_id, "run-1", (page("/settings", "save"),))
        await store(
            unit_of_work_factory,
            project_id,
            "run-2",
            (page("/settings", "save", "delete account"),),
        )

        async with unit_of_work_factory() as uow:
            outcome = await exploration_outcome(uow, "run-2")

        assert outcome.delta is not None
        assert not outcome.delta.new and not outcome.delta.gone
        assert [change.gained for change in outcome.delta.changed] == [("link:delete account",)]

    async def test_a_new_page_is_reported(self, unit_of_work_factory: Factory) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        await store(unit_of_work_factory, project_id, "run-1", (page("/"),))
        await store(
            unit_of_work_factory, project_id, "run-2", (page("/"), page("/admin", "delete user"))
        )

        async with unit_of_work_factory() as uow:
            outcome = await exploration_outcome(uow, "run-2")

        assert outcome.delta is not None
        assert [state.route for state in outcome.delta.new] == ["/admin"]

    async def test_an_incomplete_crawl_flags_its_own_conclusions(
        self, unit_of_work_factory: Factory
    ) -> None:
        # "Gone" may mean "never reached". Saying so is the difference between a
        # finding and a false alarm.
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        await store(unit_of_work_factory, project_id, "run-1", (page("/"), page("/deep")))
        await store(
            unit_of_work_factory,
            project_id,
            "run-2",
            (page("/"),),
            complete=False,
            reason=StopReason.MAX_ACTIONS,
        )

        async with unit_of_work_factory() as uow:
            outcome = await exploration_outcome(uow, "run-2")

        assert outcome.delta is not None
        assert [state.route for state in outcome.delta.gone] == ["/deep"]
        assert outcome.delta.unreachable_conclusions is True

    async def test_another_project_is_never_the_baseline(
        self, unit_of_work_factory: Factory
    ) -> None:
        mine = await seed_project_with_default_policy(unit_of_work_factory, name="Mine")
        theirs = await seed_project_with_default_policy(unit_of_work_factory, name="Theirs")
        await store(unit_of_work_factory, theirs, "run-theirs", (page("/"),))
        await store(unit_of_work_factory, mine, "run-mine", (page("/"),))

        async with unit_of_work_factory() as uow:
            outcome = await exploration_outcome(uow, "run-mine")

        assert outcome.baseline_run_id is None

    async def test_a_run_that_did_not_explore_is_a_typed_absence(
        self, unit_of_work_factory: Factory
    ) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        await seed_run(unit_of_work_factory, project_id, "run-planned")

        async with unit_of_work_factory() as uow:
            with pytest.raises(NotFoundError):
                await exploration_outcome(uow, "run-planned")

    async def test_an_unknown_run_is_a_typed_absence(self, unit_of_work_factory: Factory) -> None:
        async with unit_of_work_factory() as uow:
            with pytest.raises(NotFoundError):
                await exploration_outcome(uow, "ghost")


async def test_the_time_a_map_was_recorded_orders_the_baseline(
    unit_of_work_factory: Factory,
) -> None:
    """Three explorations: the second compares against the first, the third against the
    second. A baseline that jumped to the oldest map would report a change twice."""
    project_id = await seed_project_with_default_policy(unit_of_work_factory)
    for index in (1, 2, 3):
        await store(unit_of_work_factory, project_id, f"run-{index}", (page("/"),))

    async with unit_of_work_factory() as uow:
        outcome = await exploration_outcome(uow, "run-3")

    assert outcome.baseline_run_id == "run-2"
