"""Composition root.

The only place that knows both Application ports and Infrastructure adapters, so
Interfaces can stay a protocol translator and never import a concrete adapter.
"""

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine

from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.bootstrap.settings import Settings
from agentic_qa.infrastructure.persistence.postgres.engine import (
    create_engine,
    create_session_factory,
)
from agentic_qa.infrastructure.persistence.postgres.unit_of_work import PostgresUnitOfWork


@dataclass(frozen=True)
class Container:
    unit_of_work: Callable[[], UnitOfWork]
    engine: AsyncEngine | None = None
    """Present only for containers that own a database connection pool.

    A container wired with in-memory adapters legitimately has none, so this is
    optional rather than a value tests have to fake.
    """

    async def aclose(self) -> None:
        if self.engine is not None:
            await self.engine.dispose()


def build_container(settings: Settings) -> Container:
    engine = create_engine(settings.postgres_dsn, echo=settings.sql_echo)
    session_factory = create_session_factory(engine)
    return Container(
        unit_of_work=lambda: PostgresUnitOfWork(session_factory),
        engine=engine,
    )
