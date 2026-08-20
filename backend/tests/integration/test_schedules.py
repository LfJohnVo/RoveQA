"""Recurring runs against a real Temporal server.

The Phase 12 gate is "a scheduled run survives a service restart", and the design that
makes it true is that nothing on our side holds a schedule: Temporal does. What this
file can prove in a test is the half that a fake cannot — that the adapter really
writes to Temporal, that a second client (a stand-in for a restarted API process) reads
back exactly what was written, and that pausing and deleting land there too.

The other half — restarting the Temporal container itself — is a live check recorded in
`docs/status/HANDOFF.md`, because a test running inside a container cannot restart the
service it is talking to.
"""

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from temporalio.client import Client

from agentic_qa.application.errors import AlreadyExistsError
from agentic_qa.application.ports.schedules import RunSchedule
from agentic_qa.bootstrap.settings import Settings
from agentic_qa.infrastructure.workflows.temporal.schedules import TemporalScheduleGateway


@pytest.fixture
async def temporal_address() -> str:
    return Settings.from_env().temporal_address


@pytest.fixture
async def gateway(temporal_address: str) -> AsyncIterator[TemporalScheduleGateway]:
    try:
        client = await Client.connect(temporal_address)
    except RuntimeError as error:  # server not reachable
        pytest.skip(f"Temporal not reachable at {temporal_address}: {error}")
    yield TemporalScheduleGateway(client)


@pytest.fixture
async def schedule(gateway: TemporalScheduleGateway) -> AsyncIterator[RunSchedule]:
    """A paused schedule, created and cleaned up.

    Paused because these tests are about storage, not firing: an active nightly cron in
    a test namespace would eventually start runs nobody asked for.
    """
    created = await gateway.create(
        RunSchedule(
            schedule_id=f"it-{uuid4().hex[:12]}",
            project_id="proj-integration",
            cron="0 2 * * *",
            plan_id="plan-1",
            plan_version="v3",
            paused=True,
            note="integration test",
        )
    )
    try:
        yield created
    finally:
        await gateway.delete(created.schedule_id)


async def test_it_really_lands_in_temporal(
    gateway: TemporalScheduleGateway, schedule: RunSchedule
) -> None:
    stored = await gateway.get(schedule.schedule_id)

    assert stored is not None
    assert stored.project_id == "proj-integration"
    assert stored.cron == "0 2 * * *"
    # The plan version is what a pinned regression is *for*, so losing it in the
    # round-trip would silently turn a pinned schedule into a floating one.
    assert stored.plan_version == "v3"
    assert stored.paused is True


async def test_a_fresh_client_reads_the_same_schedule(
    temporal_address: str, schedule: RunSchedule
) -> None:
    """A new connection stands in for a restarted API process.

    Nothing about the schedule lived in the process that created it, which is the
    property the restart gate rests on.
    """
    other = TemporalScheduleGateway(await Client.connect(temporal_address))

    stored = await other.get(schedule.schedule_id)

    assert stored is not None
    assert stored.cron == schedule.cron
    assert stored.plan_id == schedule.plan_id


async def test_the_same_id_twice_is_a_conflict(
    gateway: TemporalScheduleGateway, schedule: RunSchedule
) -> None:
    with pytest.raises(AlreadyExistsError):
        await gateway.create(schedule)


async def test_pausing_and_resuming_survive_the_round_trip(
    gateway: TemporalScheduleGateway, schedule: RunSchedule
) -> None:
    assert await gateway.set_paused(schedule.schedule_id, paused=False) is True
    resumed = await gateway.get(schedule.schedule_id)
    assert resumed is not None and resumed.paused is False
    # The cron and the plan pin have to survive a pause; otherwise "pause during the
    # deploy freeze" quietly loses what the schedule was.
    assert resumed.cron == schedule.cron
    assert resumed.plan_version == "v3"

    assert await gateway.set_paused(schedule.schedule_id, paused=True) is True
    paused = await gateway.get(schedule.schedule_id)
    assert paused is not None and paused.paused is True


async def test_it_is_listed_under_its_project(
    gateway: TemporalScheduleGateway, schedule: RunSchedule
) -> None:
    listed = await gateway.list_for_project("proj-integration")

    assert schedule.schedule_id in {item.schedule_id for item in listed}
    assert await gateway.list_for_project("proj-nobody") == []


async def test_deleting_removes_it_and_is_idempotent(gateway: TemporalScheduleGateway) -> None:
    schedule_id = f"it-{uuid4().hex[:12]}"
    await gateway.create(
        RunSchedule(
            schedule_id=schedule_id,
            project_id="proj-integration",
            cron="0 3 * * *",
            paused=True,
        )
    )

    assert await gateway.delete(schedule_id) is True
    assert await gateway.get(schedule_id) is None
    # Deleting something that is already gone is the outcome the caller wanted.
    assert await gateway.delete(schedule_id) is False


async def test_operations_on_an_unknown_schedule_report_rather_than_raise(
    gateway: TemporalScheduleGateway,
) -> None:
    assert await gateway.get("it-does-not-exist") is None
    assert await gateway.set_paused("it-does-not-exist", paused=True) is False
