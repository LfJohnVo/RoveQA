"""PostgreSQL repository adapters implementing the Application ports.

Each adapter owns a session but never commits: the caller controls the transaction
boundary, so a use case can group writes and keep transactions short.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import delete, desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from agentic_qa.application.errors import AlreadyExistsError, NotFoundError
from agentic_qa.application.ports.deep_analysis import ClusterHypothesis, HypothesisConfidence
from agentic_qa.application.ports.events import NewRunEvent, RunEvent
from agentic_qa.application.ports.idempotency import IdempotencyRecord
from agentic_qa.application.ports.knowledge import GraphSyncRecord, GraphSyncState
from agentic_qa.application.ports.models import ModelInvocation
from agentic_qa.application.ports.results import RunCriterionResult
from agentic_qa.application.ports.triage import ClusterMember, StoredCluster
from agentic_qa.domain.browser.evidence import EvidenceRef
from agentic_qa.domain.exploration.comparison import StateMap
from agentic_qa.domain.exploration.frontier import ExplorationReport, StopReason
from agentic_qa.domain.exploration.state import Affordance, PageState
from agentic_qa.domain.knowledge.experience import (
    CandidateStatus,
    KnowledgeExperienceCandidate,
)
from agentic_qa.domain.knowledge.feedback import MemoryFeedback
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
from agentic_qa.domain.triage.clustering import FailureCluster
from agentic_qa.infrastructure.persistence.postgres.mappers import (
    artifact_to_domain,
    artifact_to_model,
    criterion_result_to_domain,
    criterion_result_to_model,
    environment_to_domain,
    environment_to_model,
    feedback_to_domain,
    feedback_to_model,
    graph_sync_to_domain,
    knowledge_candidate_to_domain,
    knowledge_candidate_to_model,
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
    ClusterHypothesisModel,
    CriterionResultModel,
    EnvironmentModel,
    ExplorationRunModel,
    ExploredStateModel,
    FailureClusterMemberModel,
    FailureClusterModel,
    GraphSyncStateModel,
    IdempotencyRecordModel,
    KnowledgeCandidateModel,
    MemoryFeedbackModel,
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

    async def list_recent_failures(
        self, project_id: str, *, limit: int
    ) -> list[RunCriterionResult]:
        result = await self._session.execute(
            select(CriterionResultModel, RunModel.run_id)
            .join(RunModel, RunModel.run_id == CriterionResultModel.run_id)
            .where(RunModel.project_id == project_id)
            .where(CriterionResultModel.outcome == "not_met")
            # Excluded in SQL, not afterwards: an opinion is not something to group on,
            # and a caller that forgot to filter would cluster on one.
            .where(CriterionResultModel.model_derived.is_(False))
            # Newest run first so the bound keeps what is current, but the order
            # *within* a run is its own: cascade detection depends on it.
            .order_by(desc(RunModel.created_at), RunModel.run_id, CriterionResultModel.id)
            .limit(limit)
        )
        return [
            RunCriterionResult(run_id=run_id, result=criterion_result_to_domain(model))
            for model, run_id in result.all()
        ]


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


class PostgresKnowledgeRepository:
    """Durable knowledge. The graph is rebuilt from these rows, never the reverse."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def merge(self, candidate: KnowledgeExperienceCandidate) -> KnowledgeExperienceCandidate:
        model = await self._locked(
            candidate.project_id, candidate.environment_id, candidate.dedup_key
        )
        if model is None:
            try:
                async with self._session.begin_nested():
                    self._session.add(knowledge_candidate_to_model(candidate))
                return candidate
            except IntegrityError as error:
                if not _is_unique_violation(error):
                    raise
                # Another worker learned the same thing first. Its row is the identity
                # now, so fold into that instead of failing the run that was learning.
                model = await self._locked(
                    candidate.project_id, candidate.environment_id, candidate.dedup_key
                )
                if model is None:  # pragma: no cover - the row that just conflicted
                    raise

        merged = knowledge_candidate_to_domain(model).reinforced_by(candidate)
        model.support_count = merged.quality.support_count
        model.success_count = merged.quality.success_count
        model.failure_count = merged.quality.failure_count
        model.contradiction_count = merged.quality.contradiction_count
        model.reliability = merged.quality.reliability
        model.last_verified_at = merged.quality.last_verified_at
        model.status = merged.status.value
        await self._session.flush()
        return merged

    async def get(self, candidate_id: str) -> KnowledgeExperienceCandidate | None:
        model = await self._session.get(KnowledgeCandidateModel, candidate_id)
        return knowledge_candidate_to_domain(model) if model is not None else None

    async def list_for_scope(
        self,
        *,
        project_id: str,
        environment_id: str,
        statuses: Sequence[CandidateStatus] | None = None,
        limit: int = 100,
    ) -> list[KnowledgeExperienceCandidate]:
        # Scope is in the WHERE clause, not applied to the results afterwards: a query
        # that can return another project's memory is one missed line from leaking it.
        query = (
            select(KnowledgeCandidateModel)
            .where(KnowledgeCandidateModel.project_id == project_id)
            .where(KnowledgeCandidateModel.environment_id == environment_id)
        )
        if statuses:
            query = query.where(
                KnowledgeCandidateModel.status.in_([status.value for status in statuses])
            )
        result = await self._session.execute(
            query.order_by(
                KnowledgeCandidateModel.reliability.desc(),
                KnowledgeCandidateModel.created_at.desc(),
            ).limit(limit)
        )
        return [knowledge_candidate_to_domain(model) for model in result.scalars()]

    async def save(self, candidate: KnowledgeExperienceCandidate) -> None:
        model = await self._session.get(KnowledgeCandidateModel, candidate.candidate_id)
        if model is None:
            raise NotFoundError("knowledge candidate", candidate.candidate_id)
        model.status = candidate.status.value
        model.support_count = candidate.quality.support_count
        model.success_count = candidate.quality.success_count
        model.failure_count = candidate.quality.failure_count
        model.contradiction_count = candidate.quality.contradiction_count
        model.reliability = candidate.quality.reliability
        model.last_verified_at = candidate.quality.last_verified_at
        model.valid_to = candidate.validity.valid_to
        await self._session.flush()

    async def _locked(
        self, project_id: str, environment_id: str, dedup_key: str
    ) -> KnowledgeCandidateModel | None:
        """Read the row for update so two workers learning the same thing at the same
        time produce one row with two supports, not a lost update."""
        result = await self._session.execute(
            select(KnowledgeCandidateModel)
            .where(KnowledgeCandidateModel.project_id == project_id)
            .where(KnowledgeCandidateModel.environment_id == environment_id)
            .where(KnowledgeCandidateModel.dedup_key == dedup_key)
            .with_for_update()
        )
        return result.scalars().one_or_none()


class PostgresMemoryFeedbackRepository:
    """The evidence trail behind every reliability number."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, feedback: MemoryFeedback) -> bool:
        try:
            async with self._session.begin_nested():
                self._session.add(feedback_to_model(feedback))
            return True
        except IntegrityError as error:
            if _is_unique_violation(error):
                # This occurrence is already counted. Saying so beats failing a retried
                # activity, and beats counting one outcome twice.
                return False
            raise

    async def list_for_candidate(
        self, candidate_id: str, *, limit: int = 100
    ) -> list[MemoryFeedback]:
        result = await self._session.execute(
            select(MemoryFeedbackModel)
            .where(MemoryFeedbackModel.candidate_id == candidate_id)
            .order_by(MemoryFeedbackModel.created_at.desc(), MemoryFeedbackModel.feedback_id)
            .limit(limit)
        )
        return [feedback_to_domain(model) for model in result.scalars()]


class PostgresGraphSyncStateRepository:
    """What the graph projection is missing. Never authoritative about knowledge."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def mark(self, record: GraphSyncRecord) -> None:
        model = await self._session.get(GraphSyncStateModel, record.candidate_id)
        if model is None:
            model = GraphSyncStateModel(candidate_id=record.candidate_id)
            self._session.add(model)
        model.state = record.state.value
        model.graph_schema_version = record.graph_schema_version
        model.graph_node_id = record.graph_node_id
        model.attempts = record.attempts
        model.last_error = record.last_error
        model.synced_at = record.synced_at
        model.updated_at = datetime.now(UTC)
        await self._session.flush()

    async def get(self, candidate_id: str) -> GraphSyncRecord | None:
        model = await self._session.get(GraphSyncStateModel, candidate_id)
        return graph_sync_to_domain(model) if model is not None else None

    async def list_pending(self, *, limit: int = 500) -> list[GraphSyncRecord]:
        # Failed rows are part of the backlog: a write that errored is still missing
        # from the graph, and leaving it out would make a rebuild quietly incomplete.
        result = await self._session.execute(
            select(GraphSyncStateModel)
            .where(
                GraphSyncStateModel.state.in_(
                    [GraphSyncState.PENDING.value, GraphSyncState.FAILED.value]
                )
            )
            .order_by(GraphSyncStateModel.updated_at)
            .limit(limit)
        )
        return [graph_sync_to_domain(model) for model in result.scalars()]

    async def count_by_state(self) -> dict[GraphSyncState, int]:
        result = await self._session.execute(
            select(GraphSyncStateModel.state, func.count())
            .select_from(GraphSyncStateModel)
            .group_by(GraphSyncStateModel.state)
        )
        counts = {state: 0 for state in GraphSyncState}
        for state, total in result.all():
            counts[GraphSyncState(state)] = total
        return counts


class PostgresFailureClusterRepository:
    """Durable triage. Clusters accumulate across runs; hypotheses hang off them."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self, project_id: str, clusters: Sequence[FailureCluster], *, now: datetime
    ) -> None:
        for cluster in clusters:
            model = await self._find(project_id, cluster.cluster_id)
            if model is None:
                model = FailureClusterModel(
                    project_id=project_id,
                    cluster_id=cluster.cluster_id,
                    first_seen_at=now,
                    members=[],
                )
                self._session.add(model)
            self._apply(model, cluster, now=now)
            await self._session.flush()
            await self._merge_members(model, cluster)

    def _apply(self, model: FailureClusterModel, cluster: FailureCluster, *, now: datetime) -> None:
        """Overwrite the derived fields, never `first_seen_at`.

        Status and reason are recomputed by every pass and can legitimately change — a
        cluster that looked independent becomes downstream once the setup failure that
        caused it lands in the same batch. When it first appeared cannot change.
        """
        representative = cluster.representative
        model.failure_kind = representative.failure_kind.value
        model.criterion_id = representative.criterion_id
        model.status = cluster.status.value
        model.reason = cluster.reason
        model.observation = representative.normalized_observation
        model.http_status = representative.http_status
        model.route = representative.route
        model.representative_run_id = representative.run_id
        model.blocked_by = cluster.blocked_by
        model.last_seen_at = now

    async def _merge_members(self, model: FailureClusterModel, cluster: FailureCluster) -> None:
        """Add what is new. Members are never removed: a run that once hit this problem
        still hit it, and dropping it would quietly shrink the evidence for a cluster."""
        known = {(member.run_id, member.criterion_id) for member in model.members}
        for signal in cluster.members:
            pair = (signal.run_id, signal.criterion_id)
            if pair in known:
                continue
            known.add(pair)
            self._session.add(
                FailureClusterMemberModel(
                    cluster_pk=model.id, run_id=signal.run_id, criterion_id=signal.criterion_id
                )
            )
        await self._session.flush()

    async def record_hypothesis(
        self,
        project_id: str,
        cluster_id: str,
        *,
        analyzed_run_id: str,
        hypothesis: ClusterHypothesis,
    ) -> bool:
        model = await self._find(project_id, cluster_id)
        if model is None:
            # A guess about something with no recorded evidence is exactly what must
            # never enter the store.
            raise NotFoundError("failure_cluster", cluster_id)
        try:
            async with self._session.begin_nested():
                self._session.add(
                    ClusterHypothesisModel(
                        cluster_pk=model.id,
                        analyzed_run_id=analyzed_run_id,
                        probable_cause=hypothesis.probable_cause,
                        recommended_check=hypothesis.recommended_check,
                        confidence=hypothesis.confidence.value,
                        model_derived=hypothesis.model_derived,
                        failure=hypothesis.failure,
                        model_invocation_id=(
                            hypothesis.invocation.invocation_id if hypothesis.invocation else None
                        ),
                        model_name=(hypothesis.invocation.model if hypothesis.invocation else None),
                        prompt_version=(
                            hypothesis.invocation.prompt_version if hypothesis.invocation else None
                        ),
                    )
                )
        except IntegrityError as error:
            # This pass already recorded one. A retried activity re-asking the model is
            # wasteful; a retried activity storing a second answer would be wrong.
            if _is_unique_violation(error):
                return False
            raise
        return True

    async def list_for_project(self, project_id: str, *, limit: int) -> list[StoredCluster]:
        result = await self._session.execute(
            select(FailureClusterModel)
            .where(FailureClusterModel.project_id == project_id)
            .order_by(desc(FailureClusterModel.last_seen_at), FailureClusterModel.cluster_id)
            .limit(limit)
        )
        return [_stored_cluster(model) for model in result.scalars()]

    async def _find(self, project_id: str, cluster_id: str) -> FailureClusterModel | None:
        result = await self._session.execute(
            select(FailureClusterModel)
            .where(FailureClusterModel.project_id == project_id)
            .where(FailureClusterModel.cluster_id == cluster_id)
        )
        return result.scalar_one_or_none()


def _stored_cluster(model: FailureClusterModel) -> StoredCluster:
    latest = max(model.hypotheses, key=lambda row: (row.created_at, row.id), default=None)
    return StoredCluster(
        cluster_id=model.cluster_id,
        project_id=model.project_id,
        failure_kind=model.failure_kind,
        criterion_id=model.criterion_id,
        status=model.status,
        reason=model.reason,
        observation=model.observation,
        representative_run_id=model.representative_run_id,
        first_seen_at=model.first_seen_at,
        last_seen_at=model.last_seen_at,
        members=tuple(
            ClusterMember(run_id=member.run_id, criterion_id=member.criterion_id)
            for member in sorted(model.members, key=lambda row: row.id)
        ),
        http_status=model.http_status,
        route=model.route,
        blocked_by=model.blocked_by,
        hypothesis=(
            _hypothesis(latest, cluster_id=model.cluster_id) if latest is not None else None
        ),
    )


def _hypothesis(model: ClusterHypothesisModel, *, cluster_id: str) -> ClusterHypothesis:
    # The id is passed in rather than read through `model.cluster`: that back
    # reference is a lazy load, and a lazy load inside an async session is the
    # kind of failure that only shows up under a code path nobody tested.
    invocation = (
        ModelInvocation(
            invocation_id=model.model_invocation_id,
            model=model.model_name or "",
            prompt_version=model.prompt_version or "",
        )
        if model.model_invocation_id is not None
        else None
    )
    return ClusterHypothesis(
        cluster_id=cluster_id,
        probable_cause=model.probable_cause,
        recommended_check=model.recommended_check,
        confidence=HypothesisConfidence(model.confidence),
        model_derived=model.model_derived,
        invocation=invocation,
        failure=model.failure,
    )


class PostgresStateMapRepository:
    """Exploration maps, one per run."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self, run_id: str, project_id: str, state_map: StateMap, report: ExplorationReport
    ) -> None:
        # Replace rather than append. A retried activity explored the same application
        # and must not double what it found; rewriting is also cheaper than reconciling.
        await self._session.execute(
            delete(ExploredStateModel).where(ExploredStateModel.run_id == run_id)
        )
        await self._session.flush()
        self._session.add_all(
            ExploredStateModel(
                run_id=run_id,
                project_id=project_id,
                signature=state.signature,
                route=state.route,
                url=state.url,
                title=state.title,
                affordance_keys=list(state.affordance_keys),
            )
            for state in state_map.states
        )
        existing = await self._session.get(ExplorationRunModel, run_id)
        if existing is None:
            existing = ExplorationRunModel(run_id=run_id, project_id=project_id)
            self._session.add(existing)
        existing.stop_reason = report.stop_reason.value
        existing.complete = report.complete
        existing.actions_taken = report.actions_taken
        existing.states_discovered = report.states_discovered
        existing.max_depth_reached = report.max_depth_reached
        existing.frontier_remaining = report.frontier_remaining
        existing.declined = report.declined
        await self._session.flush()

    async def get(self, run_id: str) -> StateMap | None:
        summary = await self._session.get(ExplorationRunModel, run_id)
        if summary is None:
            return None
        result = await self._session.execute(
            select(ExploredStateModel)
            .where(ExploredStateModel.run_id == run_id)
            .order_by(ExploredStateModel.id)
        )
        return StateMap(
            states=tuple(_explored_state(model) for model in result.scalars()),
            complete=summary.complete,
        )

    async def report_for(self, run_id: str) -> ExplorationReport | None:
        summary = await self._session.get(ExplorationRunModel, run_id)
        if summary is None:
            return None
        return ExplorationReport(
            stop_reason=StopReason(summary.stop_reason),
            actions_taken=summary.actions_taken,
            states_discovered=summary.states_discovered,
            max_depth_reached=summary.max_depth_reached,
            frontier_remaining=summary.frontier_remaining,
            # No budget: it is a property of the run's policy, which is already
            # durable and already pinned onto the run. A stored copy would be a second
            # version free to disagree with the first.
            declined=summary.declined,
        )

    async def previous_run(self, project_id: str, *, before_run_id: str) -> str | None:
        current = await self._session.get(ExplorationRunModel, before_run_id)
        if current is None:
            return None
        result = await self._session.execute(
            select(ExplorationRunModel.run_id)
            .where(ExplorationRunModel.project_id == project_id)
            .where(ExplorationRunModel.recorded_at < current.recorded_at)
            .order_by(desc(ExplorationRunModel.recorded_at), desc(ExplorationRunModel.run_id))
            .limit(1)
        )
        return result.scalar_one_or_none()


def _explored_state(model: ExploredStateModel) -> PageState:
    """Rebuild a state from its stored keys.

    The affordances come back as role/name pairs split from the normalised keys, which
    is enough for a comparison to say what a page gained or lost. The original accessible
    names are not kept: they are page content, and a state map is not an evidence store.
    """
    return PageState(
        url=model.url,
        title=model.title,
        affordances=tuple(_affordance_from_key(key) for key in model.affordance_keys),
    )


def _affordance_from_key(key: str) -> Affordance:
    role, _, name = key.partition(":")
    return Affordance(role=role, name=name)
