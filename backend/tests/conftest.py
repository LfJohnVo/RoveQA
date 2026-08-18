"""Shared fixtures.

`repositories` is parametrized over every repository implementation so the contract
suite in tests/contracts runs unchanged against fakes and real adapters.

The postgres parameter skips only when the database is unreachable, and the skip
reason names the DSN — a silent pass would hide a broken adapter.
"""

import os
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass

import pytest
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from agentic_qa.application.commands.create_project import (
    CreateProjectCommand,
    create_project,
)
from agentic_qa.application.ports.locks import LockManager
from agentic_qa.application.ports.repositories import (
    ProjectRepository,
    RunRepository,
    StoryRepository,
)
from agentic_qa.application.ports.semaphores import ResourceSemaphore
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.domain.projects.run_policy import RunPolicy
from agentic_qa.infrastructure.cache.redis.locks import RedisLockManager
from agentic_qa.infrastructure.cache.redis.semaphores import RedisResourceSemaphore
from agentic_qa.infrastructure.persistence.postgres.engine import (
    create_engine,
    create_session_factory,
)
from agentic_qa.infrastructure.persistence.postgres.models import Base
from agentic_qa.infrastructure.persistence.postgres.repositories import (
    PostgresProjectRepository,
    PostgresRunRepository,
    PostgresStoryRepository,
)
from agentic_qa.infrastructure.persistence.postgres.unit_of_work import PostgresUnitOfWork
from tests.fakes.locks import InMemoryLockManager
from tests.fakes.repositories import (
    InMemoryProjectRepository,
    InMemoryRunRepository,
    InMemoryStore,
    InMemoryStoryRepository,
)
from tests.fakes.semaphores import InMemoryResourceSemaphore
from tests.fakes.unit_of_work import InMemoryUnitOfWork

DEFAULT_TEST_DSN = "postgresql+asyncpg://agentic:agentic@localhost:5432/agentic_qa"
DEFAULT_TEST_REDIS_URL = "redis://localhost:6379/15"

# A run cannot start without a resolved policy, so tests that start runs seed one.
DEFAULT_POLICY_PAYLOAD = {
    "allowed_origins": ["http://localhost:3000"],
    "max_duration_seconds": 600,
    "max_actions": 100,
    "max_model_calls": 10,
    "set_as_project_default": True,
}
"""Database 15: coordination tests flush it, so they must never touch a real one."""

# Written by the committing unit-of-work tests; truncated in their teardown.
COMMITTED_TABLES = (
    "projects, user_stories, acceptance_criteria, runs, run_events, idempotency_records"
)

# The schema is created once per pytest process; engines stay per-test so every
# connection belongs to the event loop that uses it.
_schema_ready = False


def test_dsn() -> str:
    return os.environ.get("POSTGRES_TEST_DSN", DEFAULT_TEST_DSN)


def test_redis_url() -> str:
    return os.environ.get("REDIS_TEST_URL", DEFAULT_TEST_REDIS_URL)


@asynccontextmanager
async def redis_scope() -> AsyncIterator[Redis]:
    """A flushed test database, skipped with the URL when Redis is unreachable."""
    url = test_redis_url()
    client = Redis.from_url(url, decode_responses=True)
    try:
        await client.ping()
    except RedisError as error:
        await client.aclose()
        pytest.skip(f"Redis not reachable at {url}: {error}")
    await client.flushdb()
    try:
        yield client
    finally:
        await client.flushdb()
        await client.aclose()


@pytest.fixture
async def redis_client() -> AsyncIterator[Redis]:
    async with redis_scope() as client:
        yield client


@pytest.fixture(params=["memory", "redis"])
async def lock_manager(request: pytest.FixtureRequest) -> AsyncIterator[LockManager]:
    if request.param == "memory":
        yield InMemoryLockManager()
        return
    async with redis_scope() as client:
        yield RedisLockManager(client)


@pytest.fixture(params=["memory", "redis"])
async def resource_semaphore(
    request: pytest.FixtureRequest,
) -> AsyncIterator[ResourceSemaphore]:
    if request.param == "memory":
        yield InMemoryResourceSemaphore()
        return
    async with redis_scope() as client:
        yield RedisResourceSemaphore(client)


@dataclass
class Repositories:
    projects: ProjectRepository
    stories: StoryRepository
    runs: RunRepository


def in_memory_repositories() -> Repositories:
    store = InMemoryStore()
    return Repositories(
        projects=InMemoryProjectRepository(store),
        stories=InMemoryStoryRepository(store),
        runs=InMemoryRunRepository(store),
    )


async def _ensure_schema(engine: AsyncEngine, dsn: str) -> None:
    global _schema_ready
    try:
        async with engine.begin() as connection:
            if not _schema_ready:
                await connection.run_sync(Base.metadata.create_all)
    except OSError as error:  # database not reachable at all
        pytest.skip(f"PostgreSQL not reachable at {dsn}: {error}")
    _schema_ready = True


@asynccontextmanager
async def postgres_session_scope() -> AsyncIterator[AsyncSession]:
    """One engine and one always-rolled-back transaction per test.

    Per-test engines keep every connection inside the event loop that uses it; the
    rollback isolates tests without truncating tables.
    """
    dsn = test_dsn()
    engine = create_engine(dsn)
    try:
        await _ensure_schema(engine, dsn)
        async with create_session_factory(engine)() as session, session.begin():
            try:
                yield session
            finally:
                await session.rollback()
    finally:
        await engine.dispose()


@pytest.fixture
async def postgres_session() -> AsyncIterator[AsyncSession]:
    async with postgres_session_scope() as session:
        yield session


@pytest.fixture(params=["memory", "postgres"])
async def repositories(request: pytest.FixtureRequest) -> AsyncIterator[Repositories]:
    if request.param == "memory":
        yield in_memory_repositories()
        return

    async with postgres_session_scope() as session:
        yield Repositories(
            projects=PostgresProjectRepository(session),
            stories=PostgresStoryRepository(session),
            runs=PostgresRunRepository(session),
        )


@asynccontextmanager
async def postgres_unit_of_work_scope() -> AsyncIterator[Callable[[], UnitOfWork]]:
    """Units of work that really commit, with a truncating teardown."""
    dsn = test_dsn()
    engine = create_engine(dsn)
    try:
        await _ensure_schema(engine, dsn)
        session_factory = create_session_factory(engine)
        try:
            yield lambda: PostgresUnitOfWork(session_factory)
        finally:
            async with engine.begin() as connection:
                await connection.execute(
                    text(f"TRUNCATE {COMMITTED_TABLES} RESTART IDENTITY CASCADE")
                )
    finally:
        await engine.dispose()


@pytest.fixture
async def postgres_unit_of_work_factory() -> AsyncIterator[Callable[[], UnitOfWork]]:
    async with postgres_unit_of_work_scope() as factory:
        yield factory


@pytest.fixture(params=["memory", "postgres"])
async def unit_of_work_factory(
    request: pytest.FixtureRequest,
) -> AsyncIterator[Callable[[], UnitOfWork]]:
    """Build fresh units of work over one shared store/database.

    A factory rather than a single instance: proving a commit survived means opening
    a *new* transaction and finding the data there.
    """
    if request.param == "memory":
        store = InMemoryStore()
        yield lambda: InMemoryUnitOfWork(store)
        return

    async with postgres_unit_of_work_scope() as factory:
        yield factory


async def seed_project_with_default_policy(
    factory: Callable[[], UnitOfWork], name: str = "Seeded"
) -> str:
    """Create a project plus the default policy a run needs to start."""
    async with factory() as uow:
        project = await create_project(uow, CreateProjectCommand(name=name))
        policy = RunPolicy(
            policy_id=f"pol-{project.project_id}",
            project_id=project.project_id,
            allowed_origins=("http://localhost:3000",),
            max_duration_seconds=600,
            max_actions=100,
            max_model_calls=10,
        )
        await uow.policies.add(policy)
        project.default_run_policy_id = policy.policy_id
        await uow.projects.save(project)
        await uow.commit()
    return project.project_id
