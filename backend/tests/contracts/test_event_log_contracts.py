"""Run event log contract.

Both implementations must number, order and page identically: this log is what a
reconnecting client replays from, so a divergence here becomes lost or duplicated
history in the UI.
"""

from collections.abc import Callable

from agentic_qa.application.ports.events import RUN_CREATED, NewRunEvent
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.domain.projects.project import Project
from agentic_qa.domain.runs.run import Run

UnitOfWorkFactory = Callable[[], UnitOfWork]


async def seed_run(factory: UnitOfWorkFactory, run_id: str = "r-ev") -> str:
    async with factory() as uow:
        await uow.projects.add(Project(project_id="p-ev", name="Events"))
        await uow.runs.add(Run(run_id=run_id, project_id="p-ev"))
        await uow.commit()
    return run_id


async def test_sequences_start_at_one_and_increment(
    unit_of_work_factory: UnitOfWorkFactory,
) -> None:
    run_id = await seed_run(unit_of_work_factory)

    async with unit_of_work_factory() as uow:
        first = await uow.events.append(NewRunEvent(run_id=run_id, type=RUN_CREATED))
        second = await uow.events.append(NewRunEvent(run_id=run_id, type="run.status.changed"))
        await uow.commit()

    assert (first.sequence, second.sequence) == (1, 2)
    assert first.event_id != second.event_id


async def test_sequences_are_per_run(unit_of_work_factory: UnitOfWorkFactory) -> None:
    await seed_run(unit_of_work_factory, "r-a")
    async with unit_of_work_factory() as uow:
        await uow.runs.add(Run(run_id="r-b", project_id="p-ev"))
        await uow.commit()

    async with unit_of_work_factory() as uow:
        await uow.events.append(NewRunEvent(run_id="r-a", type=RUN_CREATED))
        other = await uow.events.append(NewRunEvent(run_id="r-b", type=RUN_CREATED))
        await uow.commit()

    assert other.sequence == 1  # a fresh run starts its own numbering


async def test_catch_up_returns_only_events_after_the_cursor(
    unit_of_work_factory: UnitOfWorkFactory,
) -> None:
    run_id = await seed_run(unit_of_work_factory)
    async with unit_of_work_factory() as uow:
        for index in range(5):
            await uow.events.append(
                NewRunEvent(run_id=run_id, type="run.status.changed", payload={"i": index})
            )
        await uow.commit()

    async with unit_of_work_factory() as uow:
        page = await uow.events.list_for_run(run_id, after=2, limit=10)

    assert [event.sequence for event in page] == [3, 4, 5]


async def test_reads_are_bounded_by_limit(unit_of_work_factory: UnitOfWorkFactory) -> None:
    run_id = await seed_run(unit_of_work_factory)
    async with unit_of_work_factory() as uow:
        for _ in range(5):
            await uow.events.append(NewRunEvent(run_id=run_id, type="run.status.changed"))
        await uow.commit()

    async with unit_of_work_factory() as uow:
        page = await uow.events.list_for_run(run_id, after=0, limit=2)

    assert [event.sequence for event in page] == [1, 2]


async def test_payload_and_request_id_survive_the_round_trip(
    unit_of_work_factory: UnitOfWorkFactory,
) -> None:
    run_id = await seed_run(unit_of_work_factory)
    async with unit_of_work_factory() as uow:
        await uow.events.append(
            NewRunEvent(
                run_id=run_id,
                type=RUN_CREATED,
                payload={"project_id": "p-ev", "nested": {"n": 1}},
                request_id="req-ev",
            )
        )
        await uow.commit()

    async with unit_of_work_factory() as uow:
        [event] = await uow.events.list_for_run(run_id, after=0, limit=10)

    assert event.payload == {"project_id": "p-ev", "nested": {"n": 1}}
    assert event.request_id == "req-ev"


async def test_an_uncommitted_event_is_not_visible(
    unit_of_work_factory: UnitOfWorkFactory,
) -> None:
    """Events obey the same transaction as the change they describe."""
    run_id = await seed_run(unit_of_work_factory)

    async with unit_of_work_factory() as uow:
        await uow.events.append(NewRunEvent(run_id=run_id, type=RUN_CREATED))
        # no commit

    async with unit_of_work_factory() as uow:
        assert await uow.events.list_for_run(run_id, after=0, limit=10) == []
