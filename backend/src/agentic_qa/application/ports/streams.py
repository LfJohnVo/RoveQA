"""Realtime fan-out of run events.

A projection of the durable log, never a replacement for it: delivery here may drop,
duplicate or arrive out of a client's chosen window, and the client repairs itself
from `run_events` (docs/09 stream retention, ADR 0003).

Publishing failures must never fail a run — the truth is already committed.
"""

from collections.abc import AsyncIterator
from typing import Protocol

from agentic_qa.application.ports.events import RunEvent


class RunEventSubscription(Protocol):
    """An open subscription positioned before any event it will deliver."""

    def __aiter__(self) -> AsyncIterator[RunEvent]: ...

    async def aclose(self) -> None: ...


class RunEventPublisher(Protocol):
    async def publish(self, event: RunEvent) -> None: ...

    async def subscribe(self, run_id: str) -> RunEventSubscription:
        """Open a subscription *before* reading durable catch-up.

        Opening first is what closes the gap: an event published while the caller is
        still reading history is held by the subscription instead of being missed.
        """
        ...
