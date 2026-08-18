"""In-memory resource semaphore with real lease expiry."""

import time
from uuid import uuid4

from agentic_qa.application.ports.semaphores import SlotReservation


class InMemoryResourceSemaphore:
    def __init__(self) -> None:
        self._slots: dict[str, dict[str, float]] = {}

    def _live(self, resource: str) -> dict[str, float]:
        now = time.monotonic()
        held = self._slots.setdefault(resource, {})
        for token in [t for t, deadline in held.items() if deadline <= now]:
            del held[token]
        return held

    async def acquire(
        self, resource: str, *, capacity: int, ttl_seconds: float
    ) -> SlotReservation | None:
        held = self._live(resource)
        if len(held) >= capacity:
            return None
        token = str(uuid4())
        held[token] = time.monotonic() + ttl_seconds
        return SlotReservation(resource=resource, token=token)

    async def renew(self, reservation: SlotReservation, *, ttl_seconds: float) -> bool:
        held = self._live(reservation.resource)
        if reservation.token not in held:
            return False
        held[reservation.token] = time.monotonic() + ttl_seconds
        return True

    async def release(self, reservation: SlotReservation) -> bool:
        held = self._live(reservation.resource)
        return held.pop(reservation.token, None) is not None

    async def in_use(self, resource: str) -> int:
        return len(self._live(resource))
