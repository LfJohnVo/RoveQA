"""Distributed lock port.

Locks are coordination, never truth (docs/09, ADR 0003): losing Redis may let two
workers contend, but it must never change what a run already confirmed.

Every lock carries an ownership token. A holder whose TTL expired has *lost* the
lock, so its release must not free the lock someone else now holds — that silent
mutual-exclusion break is the failure this port exists to prevent.
"""

from dataclasses import dataclass
from typing import Protocol

DEFAULT_LOCK_TTL_SECONDS = 30.0


@dataclass(frozen=True)
class LockHandle:
    key: str
    token: str


class LockManager(Protocol):
    async def acquire(self, key: str, *, ttl_seconds: float) -> LockHandle | None:
        """Return a handle, or None when the lock is already held."""
        ...

    async def renew(self, handle: LockHandle, *, ttl_seconds: float) -> bool:
        """Extend the lease. False when the token no longer owns the key."""
        ...

    async def release(self, handle: LockHandle) -> bool:
        """Release only if still the owner. False when the token no longer owns it."""
        ...
