"""Composition root.

The only place that knows both Application ports and Infrastructure adapters, so
Interfaces can stay a protocol translator and never import a concrete adapter.
"""

from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

import httpx
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine
from temporalio.client import Client

from agentic_qa.application.ports.artifacts import ArtifactRepository
from agentic_qa.application.ports.deep_analysis import DeepAnalyst
from agentic_qa.application.ports.episodes import EpisodeRunner
from agentic_qa.application.ports.graph import GraphMemoryPort
from agentic_qa.application.ports.schedules import ScheduleGateway
from agentic_qa.application.ports.streams import RunEventPublisher
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.application.ports.workflows import WorkflowGateway
from agentic_qa.bootstrap.settings import Settings
from agentic_qa.infrastructure.artifacts.filesystem.repository import (
    FilesystemArtifactRepository,
)
from agentic_qa.infrastructure.cache.redis.streams import RedisRunEventPublisher
from agentic_qa.infrastructure.knowledge.graphiti.factory import build_graph_projection
from agentic_qa.infrastructure.persistence.postgres.engine import (
    create_engine,
    create_session_factory,
)
from agentic_qa.infrastructure.persistence.postgres.unit_of_work import PostgresUnitOfWork
from agentic_qa.infrastructure.workflows.temporal.gateway import TemporalWorkflowGateway
from agentic_qa.infrastructure.workflows.temporal.schedules import TemporalScheduleGateway


@dataclass(frozen=True)
class Container:
    unit_of_work: Callable[[], UnitOfWork]
    workflows: WorkflowGateway | None = None
    """Absent until the API is connected to Temporal; endpoints that need it say so."""

    schedules: ScheduleGateway | None = None
    """Recurring runs. Absent until the process is connected to Temporal, which owns
    them: there is no second copy of a schedule anywhere in this system."""

    events: RunEventPublisher | None = None
    """Realtime fan-out. Absent means clients fall back to durable REST catch-up."""

    episodes: EpisodeRunner | None = None
    """Absent when no model endpoint is configured; the worker then says so honestly
    instead of pretending to run an agent."""

    redis: Redis | None = None
    """Owned connection to Redis, closed with the container."""

    artifacts: ArtifactRepository | None = None
    """Artifact bytes. Absent means downloads are unavailable, which the endpoint
    reports rather than pretending an artifact is missing."""

    model_http: httpx.AsyncClient | None = None
    """Connection pool for model endpoints, closed with the container."""

    deep_analyst: DeepAnalyst | None = None
    """Cold-path analysis of failure clusters. Absent means clusters are reported with
    their deterministic evidence and no hypothesis, which is a complete report."""

    graph: GraphMemoryPort | None = None
    """The learned-memory projection. Optional by design: without it runs read their
    memory from PostgreSQL and lose only retrieval breadth (ADR 0008)."""

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
        if self.model_http is not None:
            await self.model_http.aclose()


def build_container(settings: Settings) -> Container:
    """Database-only container. Temporal needs an async connect, see `connect_workflows`."""
    engine = create_engine(settings.postgres_dsn, echo=settings.sql_echo)
    session_factory = create_session_factory(engine)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    return Container(
        unit_of_work=lambda: PostgresUnitOfWork(session_factory),
        events=RedisRunEventPublisher(redis),
        artifacts=FilesystemArtifactRepository(Path(settings.artifact_root)),
        redis=redis,
        engine=engine,
        # Optional by design: `None` here means memory is served from PostgreSQL
        # alone, which is a working system with less retrieval breadth (ADR 0008).
        graph=build_graph_projection(settings),
    )


async def connect_workflows(container: Container, settings: Settings) -> Container:
    client = await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)
    return replace(
        container,
        workflows=TemporalWorkflowGateway(client, settings.temporal_task_queue),
        schedules=TemporalScheduleGateway(client, settings.temporal_task_queue),
    )


def with_agent_runtime(container: Container, settings: Settings) -> Container:
    """Add the agent runtime. Worker-only: the API never plans or drives a browser.

    Imported lazily so the API process does not load Playwright and LangGraph just to
    answer a status query.
    """
    from agentic_qa.bootstrap.agent_runtime import (
        build_deep_analyst,
        build_episode_runner,
        build_model_router,
    )
    from agentic_qa.domain.inference.tasks import ModelCapability

    router = build_model_router(settings)
    if router is None:
        return container
    if container.redis is None:
        raise RuntimeError("the agent runtime needs Redis to bound model concurrency")

    http = httpx.AsyncClient()
    # Each capability wires what it can serve, independently. A worker configured only
    # for deep analysis gets no episode runner and says so, rather than accepting
    # episodes it would fail at the first planning call.
    runner = (
        build_episode_runner(
            settings,
            router=router,
            redis=container.redis,
            http=http,
            artifacts=container.artifacts,
        )
        if router.serves(ModelCapability.FAST)
        else None
    )
    return replace(
        container,
        episodes=runner,
        model_http=http,
        deep_analyst=build_deep_analyst(router=router, redis=container.redis, http=http),
    )
