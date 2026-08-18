"""Composition root.

The only place that knows both Application ports and Infrastructure adapters, so
Interfaces can stay a protocol translator and never import a concrete adapter.
"""

from collections.abc import Callable
from dataclasses import dataclass

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine
from temporalio.client import Client

from agentic_qa.application.ports.episodes import EpisodeRunner
from agentic_qa.application.ports.streams import RunEventPublisher
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.application.ports.workflows import WorkflowGateway
from agentic_qa.bootstrap.settings import Settings
from agentic_qa.infrastructure.cache.redis.streams import RedisRunEventPublisher
from agentic_qa.infrastructure.persistence.postgres.engine import (
    create_engine,
    create_session_factory,
)
from agentic_qa.infrastructure.persistence.postgres.unit_of_work import PostgresUnitOfWork
from agentic_qa.infrastructure.workflows.temporal.gateway import TemporalWorkflowGateway


@dataclass(frozen=True)
class Container:
    unit_of_work: Callable[[], UnitOfWork]
    workflows: WorkflowGateway | None = None
    """Absent until the API is connected to Temporal; endpoints that need it say so."""

    events: RunEventPublisher | None = None
    """Realtime fan-out. Absent means clients fall back to durable REST catch-up."""

    episodes: EpisodeRunner | None = None
    """Absent until a model gateway exists (Phase 06); the worker then says so
    honestly instead of pretending to run an agent."""

    redis: Redis | None = None
    """Owned connection to Redis, closed with the container."""

    engine: AsyncEngine | None = None
    """Present only for containers that own a database connection pool.

    A container wired with in-memory adapters legitimately has none, so this is
    optional rather than a value tests have to fake.
    """

    async def aclose(self) -> None:
        if self.engine is not None:
            await self.engine.dispose()
        if self.redis is not None:
            await self.redis.aclose()


def build_container(settings: Settings) -> Container:
    """Database-only container. Temporal needs an async connect, see `connect_workflows`."""
    engine = create_engine(settings.postgres_dsn, echo=settings.sql_echo)
    session_factory = create_session_factory(engine)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    return Container(
        unit_of_work=lambda: PostgresUnitOfWork(session_factory),
        events=RedisRunEventPublisher(redis),
        redis=redis,
        engine=engine,
    )


async def connect_workflows(container: Container, settings: Settings) -> Container:
    client = await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)
    return Container(
        unit_of_work=container.unit_of_work,
        workflows=TemporalWorkflowGateway(client, settings.temporal_task_queue),
        events=container.events,
        redis=container.redis,
        engine=container.engine,
    )
