"""Bounded resource reservations (browser slots, model slots, accounts).

Every reservation has a lease. A worker that dies holding a slot must not shrink the
pool forever, so slots are reclaimed by expiry rather than by trusting cleanup.

Like locks, this is coordination only: losing Redis may over- or under-admit for a
moment, but it cannot change a run's confirmed result (docs/09).
"""

from dataclasses import dataclass
from typing import Protocol

DEFAULT_SLOT_TTL_SECONDS = 60.0


@dataclass(frozen=True)
class SlotReservation:
    resource: str
    token: str


class ResourceSemaphore(Protocol):
    async def acquire(
        self, resource: str, *, capacity: int, ttl_seconds: float
    ) -> SlotReservation | None:
        """Take a slot, or None when the resource is already at capacity."""
        ...

    async def renew(self, reservation: SlotReservation, *, ttl_seconds: float) -> bool:
        """Extend a held slot. False when the lease already lapsed."""
        ...

    async def release(self, reservation: SlotReservation) -> bool:
        """Give the slot back. False when this reservation no longer holds one."""
        ...

    async def in_use(self, resource: str) -> int:
        """Slots currently held, excluding lapsed ones."""
        ...
