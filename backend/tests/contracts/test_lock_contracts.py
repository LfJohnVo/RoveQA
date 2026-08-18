"""Lock manager contract.

The ownership tests are the point: a holder whose lease expired has lost the lock,
and must not be able to free or extend what someone else now owns.
"""

import asyncio

from agentic_qa.application.ports.locks import LockHandle, LockManager

# Short enough to expire inside a test, long enough not to be flaky on a slow machine.
SHORT_TTL = 0.3
LONG_TTL = 30.0


async def test_a_free_lock_can_be_acquired(lock_manager: LockManager) -> None:
    assert await lock_manager.acquire("lock:browser:1", ttl_seconds=LONG_TTL) is not None


async def test_a_held_lock_cannot_be_acquired_again(lock_manager: LockManager) -> None:
    await lock_manager.acquire("lock:browser:1", ttl_seconds=LONG_TTL)
    assert await lock_manager.acquire("lock:browser:1", ttl_seconds=LONG_TTL) is None


async def test_the_owner_can_release_and_the_lock_becomes_free(
    lock_manager: LockManager,
) -> None:
    handle = await lock_manager.acquire("lock:browser:1", ttl_seconds=LONG_TTL)
    assert handle is not None

    assert await lock_manager.release(handle) is True
    assert await lock_manager.acquire("lock:browser:1", ttl_seconds=LONG_TTL) is not None


async def test_a_foreign_token_cannot_release_the_lock(lock_manager: LockManager) -> None:
    handle = await lock_manager.acquire("lock:account:7", ttl_seconds=LONG_TTL)
    assert handle is not None

    impostor = LockHandle(key="lock:account:7", token="not-the-owner")
    assert await lock_manager.release(impostor) is False
    # Still held by the real owner.
    assert await lock_manager.acquire("lock:account:7", ttl_seconds=LONG_TTL) is None


async def test_a_foreign_token_cannot_renew_the_lock(lock_manager: LockManager) -> None:
    handle = await lock_manager.acquire("lock:account:7", ttl_seconds=LONG_TTL)
    assert handle is not None

    impostor = LockHandle(key="lock:account:7", token="not-the-owner")
    assert await lock_manager.renew(impostor, ttl_seconds=LONG_TTL) is False


async def test_the_owner_can_renew_its_lease(lock_manager: LockManager) -> None:
    handle = await lock_manager.acquire("lock:browser:2", ttl_seconds=SHORT_TTL)
    assert handle is not None

    assert await lock_manager.renew(handle, ttl_seconds=LONG_TTL) is True
    await asyncio.sleep(SHORT_TTL * 1.5)
    # Would have expired on the original lease; the renewal kept it alive.
    assert await lock_manager.acquire("lock:browser:2", ttl_seconds=LONG_TTL) is None


async def test_a_lock_expires_so_a_dead_holder_cannot_block_forever(
    lock_manager: LockManager,
) -> None:
    handle = await lock_manager.acquire("lock:browser:3", ttl_seconds=SHORT_TTL)
    assert handle is not None

    await asyncio.sleep(SHORT_TTL * 1.5)

    assert await lock_manager.acquire("lock:browser:3", ttl_seconds=LONG_TTL) is not None


async def test_an_expired_holder_cannot_release_the_new_owners_lock(
    lock_manager: LockManager,
) -> None:
    """The classic distributed-lock bug, asserted rather than assumed.

    A GET-then-DEL release would delete the second holder's lock here and silently
    break mutual exclusion for everyone after it.
    """
    expired = await lock_manager.acquire("lock:browser:4", ttl_seconds=SHORT_TTL)
    assert expired is not None
    await asyncio.sleep(SHORT_TTL * 1.5)

    new_owner = await lock_manager.acquire("lock:browser:4", ttl_seconds=LONG_TTL)
    assert new_owner is not None

    assert await lock_manager.release(expired) is False
    assert await lock_manager.renew(expired, ttl_seconds=LONG_TTL) is False
    # The new owner still holds it.
    assert await lock_manager.acquire("lock:browser:4", ttl_seconds=LONG_TTL) is None
    assert await lock_manager.release(new_owner) is True


async def test_different_keys_do_not_interfere(lock_manager: LockManager) -> None:
    first = await lock_manager.acquire("lock:browser:a", ttl_seconds=LONG_TTL)
    second = await lock_manager.acquire("lock:browser:b", ttl_seconds=LONG_TTL)

    assert first is not None
    assert second is not None
    assert first.token != second.token
