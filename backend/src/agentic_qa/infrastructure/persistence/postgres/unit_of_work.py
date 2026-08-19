"""PostgreSQL unit of work: one session, one transaction, one boundary."""

from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agentic_qa.infrastructure.persistence.postgres.repositories import (
    PostgresCriterionResultRepository,
    PostgresEnvironmentRepository,
    PostgresIdempotencyRepository,
    PostgresProjectRepository,
    PostgresRecoveryPointRepository,
    PostgresRunEventLog,
    PostgresRunPolicyRepository,
    PostgresRunRepository,
    PostgresStoryRepository,
    PostgresTestPlanRepository,
)


class PostgresUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("unit of work used outside its context")
        return self._session

    # Repositories are cheap stateless wrappers, so they are built per access and
    # always bound to the session of the transaction currently open.
    @property
    def projects(self) -> PostgresProjectRepository:
        return PostgresProjectRepository(self.session)

    @property
    def stories(self) -> PostgresStoryRepository:
        return PostgresStoryRepository(self.session)

    @property
    def runs(self) -> PostgresRunRepository:
        return PostgresRunRepository(self.session)

    @property
    def idempotency(self) -> PostgresIdempotencyRepository:
        return PostgresIdempotencyRepository(self.session)

    @property
    def events(self) -> PostgresRunEventLog:
        return PostgresRunEventLog(self.session)

    @property
    def policies(self) -> PostgresRunPolicyRepository:
        return PostgresRunPolicyRepository(self.session)

    @property
    def environments(self) -> PostgresEnvironmentRepository:
        return PostgresEnvironmentRepository(self.session)

    @property
    def recovery_points(self) -> PostgresRecoveryPointRepository:
        return PostgresRecoveryPointRepository(self.session)

    @property
    def criterion_results(self) -> PostgresCriterionResultRepository:
        return PostgresCriterionResultRepository(self.session)

    @property
    def plans(self) -> PostgresTestPlanRepository:
        return PostgresTestPlanRepository(self.session)

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        await self._session.begin()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        session = self._session
        self._session = None
        if session is None:
            return
        try:
            # No-op when commit() already closed the transaction; a real rollback
            # otherwise, including when the block raised.
            await session.rollback()
        finally:
            await session.close()

    async def commit(self) -> None:
        await self.session.commit()
