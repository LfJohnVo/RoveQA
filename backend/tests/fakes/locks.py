"""In-memory lock manager with real TTL semantics.

Expiry is evaluated on access using a monotonic clock, so the fake can lose a lock
the same way Redis does — a fake that never expired would let the ownership tests
pass without proving anything.
"""

import time
from dataclasses import dataclass
from uuid import uuid4

from agentic_qa.application.ports.locks import LockHandle


@dataclass
class _Entry:
    token: str
    expires_at: float


class InMemoryLockManager:
    def __init__(self) -> None:
        self._entries: dict[str, _Entry] = {}

    def _live_entry(self, key: str) -> _Entry | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at <= time.monotonic():
            del self._entries[key]
            return None
        return entry

    async def acquire(self, key: str, *, ttl_seconds: float) -> LockHandle | None:
        if self._live_entry(key) is not None:
            return None
        token = str(uuid4())
        self._entries[key] = _Entry(token=token, expires_at=time.monotonic() + ttl_seconds)
        return LockHandle(key=key, token=token)

    async def renew(self, handle: LockHandle, *, ttl_seconds: float) -> bool:
        entry = self._live_entry(handle.key)
        if entry is None or entry.token != handle.token:
            return False
        entry.expires_at = time.monotonic() + ttl_seconds
        return True

    async def release(self, handle: LockHandle) -> bool:
        entry = self._live_entry(handle.key)
        if entry is None or entry.token != handle.token:
            return False
        del self._entries[handle.key]
        return True
