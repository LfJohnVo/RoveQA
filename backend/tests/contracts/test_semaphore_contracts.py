"""Resource semaphore contract.

Capacity must hold under concurrency, and a worker that dies holding a slot must not
shrink the pool forever.
"""

import asyncio

from agentic_qa.application.ports.semaphores import ResourceSemaphore, SlotReservation

SHORT_TTL = 0.3
LONG_TTL = 30.0
RESOURCE = "semaphore:model:planner"


async def test_slots_are_granted_up_to_capacity(resource_semaphore: ResourceSemaphore) -> None:
    first = await resource_semaphore.acquire(RESOURCE, capacity=2, ttl_seconds=LONG_TTL)
    second = await resource_semaphore.acquire(RESOURCE, capacity=2, ttl_seconds=LONG_TTL)

    assert first is not None
    assert second is not None
    assert await resource_semaphore.in_use(RESOURCE) == 2


async def test_capacity_is_not_exceeded(resource_semaphore: ResourceSemaphore) -> None:
    await resource_semaphore.acquire(RESOURCE, capacity=1, ttl_seconds=LONG_TTL)

    assert await resource_semaphore.acquire(RESOURCE, capacity=1, ttl_seconds=LONG_TTL) is None


async def test_concurrent_callers_cannot_overcommit(
    resource_semaphore: ResourceSemaphore,
) -> None:
    """Check-then-add must be atomic: ten racing callers, two slots."""
    results = await asyncio.gather(
        *(resource_semaphore.acquire(RESOURCE, capacity=2, ttl_seconds=LONG_TTL) for _ in range(10))
    )

    granted = [reservation for reservation in results if reservation is not None]
    assert len(granted) == 2
    assert await resource_semaphore.in_use(RESOURCE) == 2


async def test_releasing_frees_a_slot(resource_semaphore: ResourceSemaphore) -> None:
    reservation = await resource_semaphore.acquire(RESOURCE, capacity=1, ttl_seconds=LONG_TTL)
    assert reservation is not None

    assert await resource_semaphore.release(reservation) is True
    assert await resource_semaphore.in_use(RESOURCE) == 0
    assert await resource_semaphore.acquire(RESOURCE, capacity=1, ttl_seconds=LONG_TTL) is not None


async def test_a_lapsed_slot_is_reclaimed(resource_semaphore: ResourceSemaphore) -> None:
    """A worker that died holding a slot must not shrink the pool forever."""
    dead_worker = await resource_semaphore.acquire(RESOURCE, capacity=1, ttl_seconds=SHORT_TTL)
    assert dead_worker is not None

    await asyncio.sleep(SHORT_TTL * 1.5)

    assert await resource_semaphore.in_use(RESOURCE) == 0
    assert await resource_semaphore.acquire(RESOURCE, capacity=1, ttl_seconds=LONG_TTL) is not None
    # The dead worker cannot give back a slot it no longer holds.
    assert await resource_semaphore.release(dead_worker) is False
    assert await resource_semaphore.in_use(RESOURCE) == 1


async def test_renewing_keeps_a_slot_alive(resource_semaphore: ResourceSemaphore) -> None:
    reservation = await resource_semaphore.acquire(RESOURCE, capacity=1, ttl_seconds=SHORT_TTL)
    assert reservation is not None

    assert await resource_semaphore.renew(reservation, ttl_seconds=LONG_TTL) is True
    await asyncio.sleep(SHORT_TTL * 1.5)

    assert await resource_semaphore.in_use(RESOURCE) == 1


async def test_renewing_a_lapsed_reservation_fails(
    resource_semaphore: ResourceSemaphore,
) -> None:
    reservation = await resource_semaphore.acquire(RESOURCE, capacity=1, ttl_seconds=SHORT_TTL)
    assert reservation is not None
    await asyncio.sleep(SHORT_TTL * 1.5)

    assert await resource_semaphore.renew(reservation, ttl_seconds=LONG_TTL) is False


async def test_unknown_reservations_are_rejected(
    resource_semaphore: ResourceSemaphore,
) -> None:
    impostor = SlotReservation(resource=RESOURCE, token="never-granted")

    assert await resource_semaphore.release(impostor) is False
    assert await resource_semaphore.renew(impostor, ttl_seconds=LONG_TTL) is False


async def test_resources_are_independent(resource_semaphore: ResourceSemaphore) -> None:
    await resource_semaphore.acquire("semaphore:model:a", capacity=1, ttl_seconds=LONG_TTL)

    assert (
        await resource_semaphore.acquire("semaphore:model:b", capacity=1, ttl_seconds=LONG_TTL)
        is not None
    )
