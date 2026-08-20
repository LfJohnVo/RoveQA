"""A transient PostgreSQL failure, against a real PostgreSQL.

The gap the recovery matrix named: everything else in this system has a failure somebody
injects, and the database — the one component whose loss would actually cost data — had
only an argument in its favour.

The claim being tested is narrow and worth having: a write that fails mid-flight leaves
**nothing** behind, and the retry Temporal performs produces exactly one of everything.
The status change and its event share a transaction precisely so a run can never move
without leaving its event, nor an event exist for a move that rolled back — and a failure
is the only situation where that pairing can be observed to hold.
"""

import asyncio
from collections.abc import AsyncIterator, Callable
from uuid import uuid4

import psycopg
import pytest
from sqlalchemy.exc import OperationalError
from temporalio.testing import ActivityEnvironment

from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.bootstrap.container import Container
from agentic_qa.domain.runs.run import Run, RunStatus
from agentic_qa.infrastructure.persistence.postgres.engine import (
    create_engine,
    create_session_factory,
)
from agentic_qa.infrastructure.persistence.postgres.repositories import PostgresRunEventLog
from agentic_qa.infrastructure.persistence.postgres.unit_of_work import PostgresUnitOfWork
from agentic_qa.infrastructure.workflows.temporal.activities import RunActivities
from agentic_qa.infrastructure.workflows.temporal.contracts import TransitionParams
from tests.conftest import (
    postgres_test_dsn,
    postgres_unit_of_work_scope,
    seed_project_with_default_policy,
)

Factory = Callable[[], UnitOfWork]


class FlakyDatabase:
    """A unit-of-work factory that refuses to connect for the first `failures` calls.

    Modelled on the failure that actually happens — the database is briefly gone, then
    comes back — rather than on a permanent outage, because "it never returns" is not a
    recovery scenario, it is an outage.
    """

    def __init__(self, real: Factory, *, failures: int) -> None:
        self._real = real
        self.remaining = failures
        self.attempts = 0

    def __call__(self) -> UnitOfWork:
        self.attempts += 1
        if self.remaining > 0:
            self.remaining -= 1
            raise OperationalError("connect", None, ConnectionError("the database is gone"))
        return self._real()


@pytest.fixture
async def factory() -> AsyncIterator[Factory]:
    try:
        async with postgres_unit_of_work_scope() as real:
            yield real
    except (OSError, psycopg.OperationalError) as error:  # pragma: no cover - env guard
        pytest.skip(f"PostgreSQL not reachable: {error}")


async def queued_run(factory: Factory) -> str:
    project_id = await seed_project_with_default_policy(factory, name="Flaky DB")
    run_id = f"r-{uuid4()}"
    async with factory() as uow:
        run = Run(run_id=run_id, project_id=project_id)
        run.transition_to(RunStatus.QUEUED)
        await uow.runs.add(run)
        await uow.commit()
    return run_id


async def transition(container: Container, run_id: str, status: str) -> None:
    await ActivityEnvironment().run(
        RunActivities(container).transition_run_status,
        TransitionParams(run_id=run_id, target_status=status),
    )


async def test_a_transient_failure_is_raised_so_temporal_can_retry(factory: Factory) -> None:
    """Not swallowed. An activity that hid a database failure would report a status
    change that never happened, and Temporal would never retry the one write that
    matters."""
    run_id = await queued_run(factory)
    flaky = FlakyDatabase(factory, failures=1)

    with pytest.raises(OperationalError):
        await transition(Container(unit_of_work=flaky), run_id, "running")

    async with factory() as uow:
        run = await uow.runs.get(run_id)
    assert run is not None
    assert run.status is RunStatus.QUEUED


async def test_the_retry_lands_exactly_one_transition_and_one_event(
    factory: Factory,
) -> None:
    run_id = await queued_run(factory)
    flaky = FlakyDatabase(factory, failures=1)
    container = Container(unit_of_work=flaky)

    with pytest.raises(OperationalError):
        await transition(container, run_id, "running")
    # What Temporal does next, and the whole point of raising above.
    await transition(container, run_id, "running")

    async with factory() as uow:
        run = await uow.runs.get(run_id)
        events = await uow.events.list_for_run(run_id, after=0, limit=50)
    assert run is not None
    assert run.status is RunStatus.RUNNING
    # Exactly one. The failed attempt wrote nothing, so the retry is not a second move.
    assert [event.payload["to"] for event in events] == ["running"]
    assert flaky.attempts == 2


async def test_a_failure_between_the_status_and_its_event_rolls_back_both(
    factory: Factory,
) -> None:
    """They share a transaction on purpose.

    A run that moved without leaving its event would be invisible to every client
    catching up from the durable log; an event for a move that rolled back would be a
    history of something that never happened.
    """
    run_id = await queued_run(factory)

    class BrokenEventLog(PostgresUnitOfWork):
        """A real unit of work whose event log is unreachable.

        A subclass rather than a wrapper, so this is still a `PostgresUnitOfWork` to
        the type checker and to the session: everything but `events` behaves exactly as
        production does, which is what makes the rollback below meaningful.
        """

        @property
        def events(self) -> PostgresRunEventLog:
            raise OperationalError("append", None, ConnectionError("the database is gone"))

    engine = create_engine(postgres_test_dsn())
    try:
        sessions = create_session_factory(engine)
        container = Container(unit_of_work=lambda: BrokenEventLog(sessions))

        with pytest.raises(OperationalError):
            await transition(container, run_id, "running")
    finally:
        await engine.dispose()

    async with factory() as uow:
        run = await uow.runs.get(run_id)
        events = await uow.events.list_for_run(run_id, after=0, limit=50)
    assert run is not None
    # The status write happened inside the transaction and went back with it.
    assert run.status is RunStatus.QUEUED
    assert events == []


def test_the_flaky_double_really_fails_before_it_succeeds() -> None:
    """Sanity on the fixture: a double that never failed would make every assertion
    above pass for the wrong reason."""

    async def check() -> None:
        calls: list[int] = []

        def real() -> UnitOfWork:
            calls.append(1)
            raise AssertionError("not reached in this check")

        flaky = FlakyDatabase(real, failures=2)
        for _ in range(2):
            with pytest.raises(OperationalError):
                flaky()
        assert calls == []
        assert flaky.remaining == 0

    asyncio.run(check())
