"""In-memory unit of work with real transaction semantics.

Snapshot on enter, restore on exit unless committed. A fake that always persists
would let a use case forget its commit and still pass — hiding the contract instead
of testing it.
"""

from types import TracebackType
from typing import Self

from tests.fakes.repositories import (
    InMemoryIdempotencyRepository,
    InMemoryProjectRepository,
    InMemoryRunEventLog,
    InMemoryRunRepository,
    InMemoryStore,
    InMemoryStoryRepository,
)


class InMemoryUnitOfWork:
    def __init__(self, store: InMemoryStore | None = None) -> None:
        self._store = store if store is not None else InMemoryStore()
        self._baseline: InMemoryStore | None = None
        self.committed = False

    def _require_active(self) -> InMemoryStore:
        if self._baseline is None:
            raise RuntimeError("unit of work used outside its context")
        return self._store

    @property
    def projects(self) -> InMemoryProjectRepository:
        return InMemoryProjectRepository(self._require_active())

    @property
    def stories(self) -> InMemoryStoryRepository:
        return InMemoryStoryRepository(self._require_active())

    @property
    def runs(self) -> InMemoryRunRepository:
        return InMemoryRunRepository(self._require_active())

    @property
    def idempotency(self) -> InMemoryIdempotencyRepository:
        return InMemoryIdempotencyRepository(self._require_active())

    @property
    def events(self) -> InMemoryRunEventLog:
        return InMemoryRunEventLog(self._require_active())

    async def __aenter__(self) -> Self:
        self._baseline = self._store.snapshot()
        self.committed = False
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._baseline is not None:
            # Writes after the last commit roll back, exactly as a session would.
            self._store.restore(self._baseline)
        self._baseline = None

    async def commit(self) -> None:
        self._require_active()
        self._baseline = self._store.snapshot()
        self.committed = True
