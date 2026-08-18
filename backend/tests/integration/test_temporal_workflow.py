"""Durable run lifecycle against a real Temporal server and a real database.

These are the durability gates of Phase 02: a run outlives its worker, the durable
status follows the workflow rather than the request, and cancellation is explicit.
"""

import asyncio
from collections.abc import AsyncIterator, Callable
from uuid import uuid4

import pytest
from temporalio.client import Client
from temporalio.worker import Worker

from agentic_qa.application.commands.create_project import (
    CreateProjectCommand,
    create_project,
)
from agentic_qa.application.commands.start_run import StartRunCommand, start_run
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.bootstrap.container import Container
from agentic_qa.bootstrap.settings import Settings
from agentic_qa.domain.runs.run import RunStatus, Verdict
from agentic_qa.infrastructure.workflows.temporal.activities import RunActivities
from agentic_qa.infrastructure.workflows.temporal.contracts import workflow_id_for
from agentic_qa.infrastructure.workflows.temporal.gateway import TemporalWorkflowGateway
from agentic_qa.infrastructure.workflows.temporal.worker import build_worker

UnitOfWorkFactory = Callable[[], UnitOfWork]

RESULT_TIMEOUT = 30
POLL_INTERVAL = 0.1


@pytest.fixture
async def temporal_client() -> AsyncIterator[Client]:
    address = Settings.from_env().temporal_address
    try:
        client = await Client.connect(address)
    except RuntimeError as error:  # server not reachable
        pytest.skip(f"Temporal not reachable at {address}: {error}")
    yield client


async def wait_for_status(
    factory: UnitOfWorkFactory, run_id: str, expected: RunStatus, timeout: float = RESULT_TIMEOUT
) -> None:
    """Poll durable status until it matches, or fail with what it actually was."""
    deadline = asyncio.get_running_loop().time() + timeout
    last: RunStatus | None = None
    while asyncio.get_running_loop().time() < deadline:
        async with factory() as uow:
            run = await uow.runs.get(run_id)
            last = run.status if run else None
            if last is expected:
                return
        await asyncio.sleep(POLL_INTERVAL)
    raise AssertionError(f"run {run_id} stayed in {last}, expected {expected}")


async def queue_run(factory: UnitOfWorkFactory, client: Client, task_queue: str) -> str:
    gateway = TemporalWorkflowGateway(client, task_queue)
    async with factory() as uow:
        project = await create_project(uow, CreateProjectCommand(name="Durability"))
    async with factory() as uow:
        result = await start_run(
            uow,
            gateway,
            StartRunCommand(project_id=project.project_id, idempotency_key=str(uuid4())),
        )
    return result.run.run_id


def worker_for(client: Client, factory: UnitOfWorkFactory, task_queue: str) -> Worker:
    # Activities only need the unit of work; the engine belongs to the test fixture.
    return build_worker(client, RunActivities(Container(unit_of_work=factory)), task_queue)


async def test_run_reaches_a_terminal_state_through_activities(
    postgres_unit_of_work_factory: UnitOfWorkFactory, temporal_client: Client
) -> None:
    task_queue = f"test-{uuid4()}"
    run_id = await queue_run(postgres_unit_of_work_factory, temporal_client, task_queue)

    async with worker_for(temporal_client, postgres_unit_of_work_factory, task_queue):
        handle = temporal_client.get_workflow_handle(workflow_id_for(run_id))
        assert await asyncio.wait_for(handle.result(), timeout=RESULT_TIMEOUT) == "inconclusive"

    async with postgres_unit_of_work_factory() as uow:
        run = await uow.runs.get(run_id)
        assert run is not None
        # No plan was executed, so the honest verdict is inconclusive, not passed.
        assert run.status is RunStatus.COMPLETED
        assert run.verdict is Verdict.INCONCLUSIVE


async def test_a_queued_run_waits_for_a_worker_instead_of_being_lost(
    postgres_unit_of_work_factory: UnitOfWorkFactory, temporal_client: Client
) -> None:
    """No worker is running when the run is accepted: the run must survive anyway."""
    task_queue = f"test-{uuid4()}"
    run_id = await queue_run(postgres_unit_of_work_factory, temporal_client, task_queue)

    async with postgres_unit_of_work_factory() as uow:
        run = await uow.runs.get(run_id)
        assert run is not None
        assert run.status is RunStatus.QUEUED

    async with worker_for(temporal_client, postgres_unit_of_work_factory, task_queue):
        await wait_for_status(postgres_unit_of_work_factory, run_id, RunStatus.COMPLETED)


async def test_run_continues_after_the_worker_is_replaced(
    postgres_unit_of_work_factory: UnitOfWorkFactory, temporal_client: Client
) -> None:
    """The core durability gate: a worker is replaceable mid-run.

    The run is paused so it is genuinely in flight, the worker is destroyed, a new one
    takes over, and the resumed run still reaches a terminal state.
    """
    task_queue = f"test-{uuid4()}"
    gateway = TemporalWorkflowGateway(temporal_client, task_queue)
    run_id = await queue_run(postgres_unit_of_work_factory, temporal_client, task_queue)

    async with worker_for(temporal_client, postgres_unit_of_work_factory, task_queue):
        await gateway.request_pause(run_id)
        await wait_for_status(postgres_unit_of_work_factory, run_id, RunStatus.PAUSED)

    # Worker gone. The run is paused and durable, held by Temporal and PostgreSQL.
    async with postgres_unit_of_work_factory() as uow:
        run = await uow.runs.get(run_id)
        assert run is not None
        assert run.status is RunStatus.PAUSED

    async with worker_for(temporal_client, postgres_unit_of_work_factory, task_queue):
        await gateway.request_resume(run_id)
        await wait_for_status(postgres_unit_of_work_factory, run_id, RunStatus.COMPLETED)


async def test_cancellation_is_explicit_and_terminal(
    postgres_unit_of_work_factory: UnitOfWorkFactory, temporal_client: Client
) -> None:
    task_queue = f"test-{uuid4()}"
    gateway = TemporalWorkflowGateway(temporal_client, task_queue)
    run_id = await queue_run(postgres_unit_of_work_factory, temporal_client, task_queue)

    async with worker_for(temporal_client, postgres_unit_of_work_factory, task_queue):
        await gateway.request_pause(run_id)
        await wait_for_status(postgres_unit_of_work_factory, run_id, RunStatus.PAUSED)
        await gateway.request_cancel(run_id)
        await wait_for_status(postgres_unit_of_work_factory, run_id, RunStatus.CANCELLED)

    async with postgres_unit_of_work_factory() as uow:
        run = await uow.runs.get(run_id)
        assert run is not None
        assert run.verdict is Verdict.CANCELLED

    # Cancelling a finished run is a no-op, not an error.
    await gateway.request_cancel(run_id)


async def test_starting_the_same_run_twice_does_not_duplicate_the_workflow(
    postgres_unit_of_work_factory: UnitOfWorkFactory, temporal_client: Client
) -> None:
    """A retried start after a lost acknowledgement finds the same workflow."""
    task_queue = f"test-{uuid4()}"
    gateway = TemporalWorkflowGateway(temporal_client, task_queue)
    run_id = await queue_run(postgres_unit_of_work_factory, temporal_client, task_queue)

    await gateway.start_run(run_id, "irrelevant")  # must not raise

    async with worker_for(temporal_client, postgres_unit_of_work_factory, task_queue):
        await wait_for_status(postgres_unit_of_work_factory, run_id, RunStatus.COMPLETED)
