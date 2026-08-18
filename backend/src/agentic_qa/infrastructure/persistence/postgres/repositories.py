"""PostgreSQL repository adapters implementing the Application ports.

Each adapter owns a session but never commits: the caller controls the transaction
boundary, so a use case can group writes and keep transactions short.
"""

from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from agentic_qa.application.errors import AlreadyExistsError, NotFoundError
from agentic_qa.application.ports.events import NewRunEvent, RunEvent
from agentic_qa.application.ports.idempotency import IdempotencyRecord
from agentic_qa.domain.projects.project import Project
from agentic_qa.domain.qa.user_story import UserStory
from agentic_qa.domain.runs.run import Run
from agentic_qa.infrastructure.persistence.postgres.mappers import (
    project_to_domain,
    project_to_model,
    run_to_domain,
    run_to_model,
    story_to_domain,
    story_to_model,
)
from agentic_qa.infrastructure.persistence.postgres.models import (
    IdempotencyRecordModel,
    ProjectModel,
    RunEventModel,
    RunModel,
    UserStoryModel,
)

UNIQUE_VIOLATION_SQLSTATE = "23505"


def _is_unique_violation(error: IntegrityError) -> bool:
    """Only a duplicate identity maps to AlreadyExistsError.

    A foreign-key or check violation is a different failure and must not be
    reported (or retried) as a harmless duplicate.
    """
    return getattr(error.orig, "sqlstate", None) == UNIQUE_VIOLATION_SQLSTATE


class PostgresProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, project: Project) -> None:
        if await self.get(project.project_id) is not None:
            raise AlreadyExistsError("project", project.project_id)
        try:
            # SAVEPOINT: a rejected insert must not poison the caller's transaction.
            async with self._session.begin_nested():
                self._session.add(project_to_model(project))
        except IntegrityError as error:  # lost a concurrent race; the DB had last word
            if _is_unique_violation(error):
                raise AlreadyExistsError("project", project.project_id) from error
            raise

    async def get(self, project_id: str) -> Project | None:
        model = await self._session.get(ProjectModel, project_id)
        return project_to_domain(model) if model is not None else None


class PostgresStoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, story: UserStory) -> None:
        if await self.get(story.story_id) is not None:
            raise AlreadyExistsError("user_story", story.story_id)
        try:
            async with self._session.begin_nested():
                self._session.add(story_to_model(story))
        except IntegrityError as error:  # lost a concurrent race; the DB had last word
            if _is_unique_violation(error):
                raise AlreadyExistsError("user_story", story.story_id) from error
            raise

    async def get(self, story_id: str) -> UserStory | None:
        model = await self._session.get(UserStoryModel, story_id)
        return story_to_domain(model) if model is not None else None

    async def list_for_project(self, project_id: str, *, limit: int) -> list[UserStory]:
        statement = (
            select(UserStoryModel)
            .where(UserStoryModel.project_id == project_id)
            .order_by(UserStoryModel.story_id)
            .limit(limit)
        )
        result = await self._session.scalars(statement)
        return [story_to_domain(model) for model in result]


class PostgresRunEventLog:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, event: NewRunEvent) -> RunEvent:
        # Sequence is derived inside the caller's transaction; the unique constraint
        # on (run_id, sequence) is the real guarantee if two appends ever race.
        next_sequence = await self._session.scalar(
            select(func.coalesce(func.max(RunEventModel.sequence), 0) + 1).where(
                RunEventModel.run_id == event.run_id
            )
        )
        model = RunEventModel(
            event_id=str(uuid4()),
            run_id=event.run_id,
            sequence=next_sequence or 1,
            type=event.type,
            payload=dict(event.payload),
            request_id=event.request_id,
        )
        self._session.add(model)
        await self._session.flush()
        return _event_to_domain(model)

    async def list_for_run(self, run_id: str, *, after: int, limit: int) -> list[RunEvent]:
        statement = (
            select(RunEventModel)
            .where(RunEventModel.run_id == run_id, RunEventModel.sequence > after)
            .order_by(RunEventModel.sequence)
            .limit(limit)
        )
        result = await self._session.scalars(statement)
        return [_event_to_domain(model) for model in result]


def _event_to_domain(model: RunEventModel) -> RunEvent:
    return RunEvent(
        event_id=model.event_id,
        run_id=model.run_id,
        sequence=model.sequence,
        type=model.type,
        occurred_at=model.occurred_at,
        payload=dict(model.payload),
        request_id=model.request_id,
    )


class PostgresIdempotencyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, scope: str, key: str) -> IdempotencyRecord | None:
        model = await self._session.get(IdempotencyRecordModel, (scope, key))
        if model is None:
            return None
        return IdempotencyRecord(
            scope=model.scope,
            key=model.idempotency_key,
            request_fingerprint=model.request_fingerprint,
            resource_id=model.resource_id,
            created_at=model.created_at,
        )

    async def add(self, record: IdempotencyRecord) -> None:
        if await self.get(record.scope, record.key) is not None:
            raise AlreadyExistsError("idempotency_record", f"{record.scope}/{record.key}")
        try:
            async with self._session.begin_nested():
                self._session.add(
                    IdempotencyRecordModel(
                        scope=record.scope,
                        idempotency_key=record.key,
                        request_fingerprint=record.request_fingerprint,
                        resource_id=record.resource_id,
                    )
                )
        except IntegrityError as error:  # concurrent request won the race
            if _is_unique_violation(error):
                raise AlreadyExistsError(
                    "idempotency_record", f"{record.scope}/{record.key}"
                ) from error
            raise


class PostgresRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, run: Run) -> None:
        if await self.get(run.run_id) is not None:
            raise AlreadyExistsError("run", run.run_id)
        try:
            async with self._session.begin_nested():
                self._session.add(run_to_model(run))
        except IntegrityError as error:  # lost a concurrent race; the DB had last word
            if _is_unique_violation(error):
                raise AlreadyExistsError("run", run.run_id) from error
            raise

    async def get(self, run_id: str) -> Run | None:
        model = await self._session.get(RunModel, run_id)
        return run_to_domain(model) if model is not None else None

    async def save(self, run: Run) -> None:
        model = await self._session.get(RunModel, run.run_id)
        if model is None:
            raise NotFoundError("run", run.run_id)
        model.status = run.status
        model.verdict = run.verdict
