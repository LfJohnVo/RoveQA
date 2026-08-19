"""PostgreSQL repository adapters implementing the Application ports.

Each adapter owns a session but never commits: the caller controls the transaction
boundary, so a use case can group writes and keep transactions short.
"""

from collections.abc import Sequence
from uuid import uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from agentic_qa.application.errors import AlreadyExistsError, NotFoundError
from agentic_qa.application.ports.events import NewRunEvent, RunEvent
from agentic_qa.application.ports.idempotency import IdempotencyRecord
from agentic_qa.domain.browser.evidence import EvidenceRef
from agentic_qa.domain.projects.environment import Environment
from agentic_qa.domain.projects.project import Project
from agentic_qa.domain.projects.run_policy import RunPolicy
from agentic_qa.domain.qa.test_plan import TestPlan
from agentic_qa.domain.qa.user_story import UserStory
from agentic_qa.domain.qa.verification import CriterionResult
from agentic_qa.domain.runs.recovery import (
    BrowserRecoveryData,
    RecoveryPoint,
    RecoveryTrigger,
)
from agentic_qa.domain.runs.run import Run
from agentic_qa.infrastructure.persistence.postgres.mappers import (
    artifact_to_domain,
    artifact_to_model,
    criterion_result_to_domain,
    criterion_result_to_model,
    environment_to_domain,
    environment_to_model,
    plan_to_domain,
    plan_to_model,
    policy_to_domain,
    policy_to_model,
    project_to_domain,
    project_to_model,
    run_to_domain,
    run_to_model,
    story_to_domain,
    story_to_model,
)
from agentic_qa.infrastructure.persistence.postgres.models import (
    ArtifactModel,
    CriterionResultModel,
    EnvironmentModel,
    IdempotencyRecordModel,
    ProjectModel,
    RecoveryPointModel,
    RunEventModel,
    RunModel,
    RunPolicyModel,
    TestPlanModel,
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

    async def list(self, *, limit: int) -> list[Project]:
        result = await self._session.execute(
            select(ProjectModel).order_by(ProjectModel.created_at.desc()).limit(limit)
        )
        return [project_to_domain(model) for model in result.scalars()]

    async def save(self, project: Project) -> None:
        model = await self._session.get(ProjectModel, project.project_id)
        if model is None:
            raise NotFoundError("project", project.project_id)
        model.name = project.name
        model.default_run_policy_id = project.default_run_policy_id


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


class PostgresRunPolicyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, policy: RunPolicy) -> None:
        if await self.get(policy.policy_id) is not None:
            raise AlreadyExistsError("run_policy", policy.policy_id)
        try:
            async with self._session.begin_nested():
                self._session.add(policy_to_model(policy))
        except IntegrityError as error:
            if _is_unique_violation(error):
                raise AlreadyExistsError("run_policy", policy.policy_id) from error
            raise

    async def get(self, policy_id: str) -> RunPolicy | None:
        model = await self._session.get(RunPolicyModel, policy_id)
        return policy_to_domain(model) if model is not None else None


class PostgresEnvironmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, environment: Environment) -> None:
        if await self.get(environment.environment_id) is not None:
            raise AlreadyExistsError("environment", environment.environment_id)
        try:
            async with self._session.begin_nested():
                self._session.add(environment_to_model(environment))
        except IntegrityError as error:
            if _is_unique_violation(error):
                raise AlreadyExistsError("environment", environment.environment_id) from error
            raise

    async def get(self, environment_id: str) -> Environment | None:
        model = await self._session.get(EnvironmentModel, environment_id)
        return environment_to_domain(model) if model is not None else None


class PostgresRecoveryPointRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, point: RecoveryPoint) -> None:
        self._session.add(
            RecoveryPointModel(
                recovery_point_id=point.recovery_point_id,
                run_id=point.run_id,
                episode_index=point.episode_index,
                trigger=point.trigger.value,
                graph_checkpoint_id=point.graph_checkpoint_id,
                browser_url=point.browser.url,
                page_fingerprint=point.browser.page_fingerprint,
                storage_state_ref=point.browser.storage_state_ref,
                last_verified_action=point.browser.last_verified_action,
            )
        )
        await self._session.flush()

    async def latest_for_run(self, run_id: str) -> RecoveryPoint | None:
        points = await self.list_for_run(run_id, limit=1)
        return points[0] if points else None

    async def list_for_run(self, run_id: str, *, limit: int) -> list[RecoveryPoint]:
        statement = (
            select(RecoveryPointModel)
            .where(RecoveryPointModel.run_id == run_id)
            .order_by(RecoveryPointModel.created_at.desc(), RecoveryPointModel.episode_index.desc())
            .limit(limit)
        )
        result = await self._session.scalars(statement)
        return [_recovery_to_domain(model) for model in result]


def _recovery_to_domain(model: RecoveryPointModel) -> RecoveryPoint:
    return RecoveryPoint(
        recovery_point_id=model.recovery_point_id,
        run_id=model.run_id,
        episode_index=model.episode_index,
        trigger=RecoveryTrigger(model.trigger),
        graph_checkpoint_id=model.graph_checkpoint_id,
        browser=BrowserRecoveryData(
            url=model.browser_url,
            page_fingerprint=model.page_fingerprint,
            storage_state_ref=model.storage_state_ref,
            last_verified_action=model.last_verified_action,
        ),
        created_at=model.created_at,
    )


class PostgresTestPlanRepository:
    """Plan versions are append-only: no `save`, because a plan changes by versioning."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, plan: TestPlan) -> None:
        identity = f"{plan.plan_id}@{plan.plan_version}"
        if await self.get(plan.plan_id, plan.plan_version) is not None:
            raise AlreadyExistsError("test_plan", identity)
        try:
            async with self._session.begin_nested():
                self._session.add(plan_to_model(plan))
        except IntegrityError as error:
            if _is_unique_violation(error):
                raise AlreadyExistsError("test_plan", identity) from error
            raise

    async def get(self, plan_id: str, plan_version: str) -> TestPlan | None:
        model = await self._session.get(TestPlanModel, (plan_id, plan_version))
        return plan_to_domain(model) if model is not None else None

    async def latest(self, plan_id: str) -> TestPlan | None:
        result = await self._session.execute(
            select(TestPlanModel)
            .where(TestPlanModel.plan_id == plan_id)
            .order_by(TestPlanModel.created_at.desc(), TestPlanModel.plan_version.desc())
            .limit(1)
        )
        model = result.scalar_one_or_none()
        return plan_to_domain(model) if model is not None else None

    async def list_for_story(self, story_id: str, *, limit: int) -> list[TestPlan]:
        result = await self._session.execute(
            select(TestPlanModel)
            .where(TestPlanModel.source_story_id == story_id)
            .order_by(TestPlanModel.created_at.desc())
            .limit(limit)
        )
        return [plan_to_domain(model) for model in result.scalars()]


class PostgresCriterionResultRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, run_id: str, results: Sequence[CriterionResult]) -> None:
        """Replace, not append. A retried activity must not leave two answers for one
        criterion, and the second answer is the one that completed."""
        if not results:
            return
        await self._session.execute(
            delete(CriterionResultModel)
            .where(CriterionResultModel.run_id == run_id)
            .where(
                CriterionResultModel.criterion_id.in_([result.criterion_id for result in results])
            )
        )
        await self._session.flush()
        self._session.add_all(criterion_result_to_model(run_id, result) for result in results)

    async def list_for_run(self, run_id: str) -> list[CriterionResult]:
        result = await self._session.execute(
            select(CriterionResultModel)
            .where(CriterionResultModel.run_id == run_id)
            .order_by(CriterionResultModel.id)
        )
        return [criterion_result_to_domain(model) for model in result.scalars()]


class PostgresArtifactIndex:
    """Durable index of captured artifacts. The bytes live on the filesystem."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, ref: EvidenceRef) -> None:
        # Idempotent by artifact id: an activity that retried after a lost
        # acknowledgement must not index the same capture twice.
        if await self._session.get(ArtifactModel, ref.artifact_id) is not None:
            return
        try:
            async with self._session.begin_nested():
                self._session.add(artifact_to_model(ref))
        except IntegrityError as error:
            if _is_unique_violation(error):
                return
            raise

    async def get(self, artifact_id: str) -> EvidenceRef | None:
        model = await self._session.get(ArtifactModel, artifact_id)
        return artifact_to_domain(model) if model is not None else None

    async def list_for_run(self, run_id: str) -> list[EvidenceRef]:
        result = await self._session.execute(
            select(ArtifactModel)
            .where(ArtifactModel.run_id == run_id)
            .order_by(ArtifactModel.captured_at, ArtifactModel.artifact_id)
        )
        return [artifact_to_domain(model) for model in result.scalars()]
