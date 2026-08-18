"""In-memory run event publisher with the same delivery semantics as Redis."""

import asyncio
from collections.abc import AsyncIterator

from agentic_qa.application.ports.events import RunEvent


class InMemoryRunEventSubscription:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[RunEvent] = asyncio.Queue()
        self._closed = False

    def offer(self, event: RunEvent) -> None:
        if not self._closed:
            self._queue.put_nowait(event)

    async def __aiter__(self) -> AsyncIterator[RunEvent]:
        while not self._closed:
            yield await self._queue.get()

    async def aclose(self) -> None:
        self._closed = True


class InMemoryRunEventPublisher:
    def __init__(self) -> None:
        self.published: list[RunEvent] = []
        self._subscriptions: dict[str, list[InMemoryRunEventSubscription]] = {}

    async def publish(self, event: RunEvent) -> None:
        self.published.append(event)
        for subscription in self._subscriptions.get(event.run_id, []):
            subscription.offer(event)

    async def subscribe(self, run_id: str) -> InMemoryRunEventSubscription:
        subscription = InMemoryRunEventSubscription()
        self._subscriptions.setdefault(run_id, []).append(subscription)
        return subscription


class BrokenRunEventPublisher:
    """Realtime transport is down; the run must not notice."""

    async def publish(self, event: RunEvent) -> None:
        raise ConnectionError("redis unreachable")

    async def subscribe(self, run_id: str) -> InMemoryRunEventSubscription:
        raise ConnectionError("redis unreachable")
