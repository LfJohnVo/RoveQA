"""Losing Redis entirely must cost coordination and freshness, never truth.

`FLUSHALL` is the blunt version of the recovery assumption in docs/09: the product's
truth lives in PostgreSQL, so a wiped Redis degrades performance and live delivery
and nothing else.
"""

from collections.abc import Callable

from redis.asyncio import Redis

from agentic_qa.application.commands.start_run import StartRunCommand, start_run
from agentic_qa.application.commands.transition_run import (
    TransitionRunCommand,
    transition_run,
)
from agentic_qa.application.ports.locks import LockHandle
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.domain.runs.run import RunStatus
from agentic_qa.infrastructure.cache.redis.locks import RedisLockManager
from agentic_qa.infrastructure.cache.redis.semaphores import RedisResourceSemaphore
from agentic_qa.infrastructure.cache.redis.streams import RedisRunEventPublisher, stream_key
from tests.conftest import seed_project_with_default_policy
from tests.fakes.workflows import RecordingWorkflowGateway

UnitOfWorkFactory = Callable[[], UnitOfWork]


async def test_a_flushed_redis_leaves_the_run_and_its_history_intact(
    postgres_unit_of_work_factory: UnitOfWorkFactory, redis_client: Redis
) -> None:
    publisher = RedisRunEventPublisher(redis_client)

    project_id = await seed_project_with_default_policy(postgres_unit_of_work_factory, "Redis loss")
    async with postgres_unit_of_work_factory() as uow:
        result = await start_run(
            uow,
            RecordingWorkflowGateway(),
            StartRunCommand(project_id=project_id, idempotency_key="k-flush"),
            publisher=publisher,
        )
    run_id = result.run.run_id

    async with postgres_unit_of_work_factory() as uow:
        await transition_run(
            uow, TransitionRunCommand(run_id=run_id, target_status=RunStatus.RUNNING), publisher
        )

    assert await redis_client.exists(stream_key(run_id)) == 1

    await redis_client.flushdb()

    assert await redis_client.exists(stream_key(run_id)) == 0
    async with postgres_unit_of_work_factory() as uow:
        run = await uow.runs.get(run_id)
        assert run is not None
        assert run.status is RunStatus.RUNNING  # confirmed status survived

        events = await uow.events.list_for_run(run_id, after=0, limit=100)
        assert [event.type for event in events] == ["run.created", "run.status.changed"]
        assert [event.sequence for event in events] == [1, 2]


async def test_a_client_rebuilds_its_baseline_after_losing_realtime(
    postgres_unit_of_work_factory: UnitOfWorkFactory, redis_client: Redis
) -> None:
    """Reconnect path: durable catch-up gives the full picture, then live resumes."""
    publisher = RedisRunEventPublisher(redis_client)

    project_id = await seed_project_with_default_policy(postgres_unit_of_work_factory, "Reconnect")
    async with postgres_unit_of_work_factory() as uow:
        result = await start_run(
            uow,
            RecordingWorkflowGateway(),
            StartRunCommand(project_id=project_id, idempotency_key="k-reconnect"),
            publisher=publisher,
        )
    run_id = result.run.run_id

    await redis_client.flushdb()  # the client was offline and the stream is gone

    async with postgres_unit_of_work_factory() as uow:
        baseline = await uow.events.list_for_run(run_id, after=0, limit=100)
    assert [event.sequence for event in baseline] == [1]

    # Live delivery resumes from the cursor the baseline ended on.
    subscription = await publisher.subscribe(run_id)
    async with postgres_unit_of_work_factory() as uow:
        await transition_run(
            uow, TransitionRunCommand(run_id=run_id, target_status=RunStatus.RUNNING), publisher
        )

    received = await anext(aiter(subscription))
    assert received.sequence == 2
    await subscription.aclose()


async def test_coordination_recovers_after_a_flush(redis_client: Redis) -> None:
    """Locks and slots are lost, which is allowed: they are coordination, not truth."""
    locks = RedisLockManager(redis_client)
    semaphore = RedisResourceSemaphore(redis_client)

    held = await locks.acquire("lock:browser:flush", ttl_seconds=30)
    reservation = await semaphore.acquire("semaphore:model:flush", capacity=1, ttl_seconds=30)
    assert held is not None
    assert reservation is not None

    await redis_client.flushdb()

    # The lock is gone, so the resource is contended for a moment — acceptable.
    reacquired = await locks.acquire("lock:browser:flush", ttl_seconds=30)
    assert reacquired is not None
    assert await semaphore.in_use("semaphore:model:flush") == 0
    assert await semaphore.acquire("semaphore:model:flush", capacity=1, ttl_seconds=30) is not None

    # The pre-flush holder cannot free what it no longer owns.
    assert await locks.release(LockHandle(key="lock:browser:flush", token=held.token)) is False
    assert await semaphore.release(reservation) is False
