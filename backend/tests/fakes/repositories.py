"""In-memory repository doubles.

They copy entities on the way in and out so callers cannot mutate stored state by
holding a reference — the same isolation a real database gives. All repositories of
one unit of work share a single `InMemoryStore`, which is what makes the fake
transaction able to roll back for real.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from uuid import uuid4

from agentic_qa.application.errors import AlreadyExistsError, NotFoundError
from agentic_qa.application.ports.deep_analysis import ClusterHypothesis
from agentic_qa.application.ports.events import NewRunEvent, RunEvent
from agentic_qa.application.ports.idempotency import IdempotencyRecord
from agentic_qa.application.ports.knowledge import GraphSyncRecord, GraphSyncState
from agentic_qa.application.ports.results import RunCriterionResult
from agentic_qa.application.ports.triage import ClusterMember, StoredCluster
from agentic_qa.domain.browser.evidence import EvidenceRef
from agentic_qa.domain.exploration.comparison import StateMap
from agentic_qa.domain.exploration.frontier import ExplorationReport
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
from agentic_qa.domain.qa.verification import CriterionOutcome, CriterionResult
from agentic_qa.domain.runs.recovery import RecoveryPoint
from agentic_qa.domain.runs.run import Run
from agentic_qa.domain.triage.clustering import FailureCluster


@dataclass
class InMemoryStore:
    projects: dict[str, Project] = field(default_factory=dict)
    stories: dict[str, UserStory] = field(default_factory=dict)
    runs: dict[str, Run] = field(default_factory=dict)
    idempotency: dict[tuple[str, str], IdempotencyRecord] = field(default_factory=dict)
    events: list[RunEvent] = field(default_factory=list)
    policies: dict[str, RunPolicy] = field(default_factory=dict)
    environments: dict[str, Environment] = field(default_factory=dict)
    recovery_points: list[RecoveryPoint] = field(default_factory=list)
    plans: dict[tuple[str, str], TestPlan] = field(default_factory=dict)
    criterion_results: dict[str, dict[str, CriterionResult]] = field(default_factory=dict)
    artifacts: dict[str, EvidenceRef] = field(default_factory=dict)
    knowledge: dict[tuple[str, str, str], KnowledgeExperienceCandidate] = field(
        default_factory=dict
    )
    """Keyed the way the table is unique: scope plus the identity of the fact."""

    memory_feedback: dict[tuple[str, str, str, str], MemoryFeedback] = field(default_factory=dict)
    """Keyed by occurrence — candidate, run, episode, kind — so a retry is one record."""

    graph_sync: dict[str, GraphSyncRecord] = field(default_factory=dict)
    failure_clusters: dict[tuple[str, str], StoredCluster] = field(default_factory=dict)
    """Keyed the way the table is unique: project plus the derived cluster id."""

    cluster_hypotheses: dict[tuple[str, str, str], ClusterHypothesis] = field(default_factory=dict)
    """Keyed by the analysis pass that produced it, so a retried pass adds nothing."""

    state_maps: dict[str, tuple[str, StateMap, ExplorationReport]] = field(default_factory=dict)
    """run_id -> (project_id, map, report). Insertion order stands in for recording
    order, which is what "the previous exploration" means."""

    def snapshot(self) -> "InMemoryStore":
        return InMemoryStore(
            projects=dict(self.projects),
            stories=dict(self.stories),
            runs=dict(self.runs),
            idempotency=dict(self.idempotency),
            events=list(self.events),
            policies=dict(self.policies),
            environments=dict(self.environments),
            recovery_points=list(self.recovery_points),
            plans=dict(self.plans),
            criterion_results={
                run: dict(results) for run, results in self.criterion_results.items()
            },
            artifacts=dict(self.artifacts),
            knowledge=dict(self.knowledge),
            memory_feedback=dict(self.memory_feedback),
            graph_sync=dict(self.graph_sync),
            failure_clusters=dict(self.failure_clusters),
            cluster_hypotheses=dict(self.cluster_hypotheses),
            state_maps=dict(self.state_maps),
        )

    def restore(self, snapshot: "InMemoryStore") -> None:
        # Restored in place so repositories holding this store see the rollback.
        self.projects.clear()
        self.projects.update(snapshot.projects)
        self.stories.clear()
        self.stories.update(snapshot.stories)
        self.runs.clear()
        self.runs.update(snapshot.runs)
        self.idempotency.clear()
        self.idempotency.update(snapshot.idempotency)
        self.events.clear()
        self.events.extend(snapshot.events)
        self.policies.clear()
        self.policies.update(snapshot.policies)
        self.environments.clear()
        self.environments.update(snapshot.environments)
        self.recovery_points.clear()
        self.recovery_points.extend(snapshot.recovery_points)
        self.plans.clear()
        self.plans.update(snapshot.plans)
        self.criterion_results.clear()
        self.criterion_results.update(
            {run: dict(results) for run, results in snapshot.criterion_results.items()}
        )
        self.artifacts.clear()
        self.artifacts.update(snapshot.artifacts)
        self.knowledge.clear()
        self.knowledge.update(snapshot.knowledge)
        self.memory_feedback.clear()
        self.memory_feedback.update(snapshot.memory_feedback)
        self.graph_sync.clear()
        self.graph_sync.update(snapshot.graph_sync)
        self.failure_clusters.clear()
        self.failure_clusters.update(snapshot.failure_clusters)
        self.cluster_hypotheses.clear()
        self.cluster_hypotheses.update(snapshot.cluster_hypotheses)
        self.state_maps.clear()
        self.state_maps.update(snapshot.state_maps)


class InMemoryProjectRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def add(self, project: Project) -> None:
        if project.project_id in self._store.projects:
            raise AlreadyExistsError("project", project.project_id)
        self._store.projects[project.project_id] = replace(project)

    async def get(self, project_id: str) -> Project | None:
        stored = self._store.projects.get(project_id)
        return replace(stored) if stored is not None else None

    async def list(self, *, limit: int) -> list[Project]:
        return [replace(project) for project in self._store.projects.values()][:limit]

    async def save(self, project: Project) -> None:
        if project.project_id not in self._store.projects:
            raise NotFoundError("project", project.project_id)
        self._store.projects[project.project_id] = replace(project)


class InMemoryStoryRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def add(self, story: UserStory) -> None:
        if story.story_id in self._store.stories:
            raise AlreadyExistsError("user_story", story.story_id)
        self._store.stories[story.story_id] = replace(story)

    async def get(self, story_id: str) -> UserStory | None:
        stored = self._store.stories.get(story_id)
        return replace(stored) if stored is not None else None

    async def list_for_project(self, project_id: str, *, limit: int) -> list[UserStory]:
        matching = sorted(
            (s for s in self._store.stories.values() if s.project_id == project_id),
            key=lambda s: s.story_id,
        )
        return [replace(story) for story in matching[:limit]]


class InMemoryIdempotencyRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def get(self, scope: str, key: str) -> IdempotencyRecord | None:
        return self._store.idempotency.get((scope, key))

    async def add(self, record: IdempotencyRecord) -> None:
        identity = (record.scope, record.key)
        if identity in self._store.idempotency:
            raise AlreadyExistsError("idempotency_record", f"{record.scope}/{record.key}")
        self._store.idempotency[identity] = record


class InMemoryRunEventLog:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def append(self, event: NewRunEvent) -> RunEvent:
        existing = [e for e in self._store.events if e.run_id == event.run_id]
        stored = RunEvent(
            event_id=str(uuid4()),
            run_id=event.run_id,
            sequence=len(existing) + 1,
            type=event.type,
            occurred_at=datetime.now(UTC),
            payload=dict(event.payload),
            request_id=event.request_id,
        )
        self._store.events.append(stored)
        return stored

    async def list_for_run(self, run_id: str, *, after: int, limit: int) -> list[RunEvent]:
        matching = [e for e in self._store.events if e.run_id == run_id and e.sequence > after]
        return sorted(matching, key=lambda e: e.sequence)[:limit]


class InMemoryRunRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def add(self, run: Run) -> None:
        if run.run_id in self._store.runs:
            raise AlreadyExistsError("run", run.run_id)
        self._store.runs[run.run_id] = replace(run)

    async def get(self, run_id: str) -> Run | None:
        stored = self._store.runs.get(run_id)
        return replace(stored) if stored is not None else None

    async def save(self, run: Run) -> None:
        if run.run_id not in self._store.runs:
            raise NotFoundError("run", run.run_id)
        self._store.runs[run.run_id] = replace(run)


class InMemoryRunPolicyRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def add(self, policy: RunPolicy) -> None:
        if policy.policy_id in self._store.policies:
            raise AlreadyExistsError("run_policy", policy.policy_id)
        self._store.policies[policy.policy_id] = replace(policy)

    async def get(self, policy_id: str) -> RunPolicy | None:
        stored = self._store.policies.get(policy_id)
        return replace(stored) if stored is not None else None


class InMemoryEnvironmentRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def add(self, environment: Environment) -> None:
        if environment.environment_id in self._store.environments:
            raise AlreadyExistsError("environment", environment.environment_id)
        self._store.environments[environment.environment_id] = replace(environment)

    async def get(self, environment_id: str) -> Environment | None:
        stored = self._store.environments.get(environment_id)
        return replace(stored) if stored is not None else None


class InMemoryRecoveryPointRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def add(self, point: RecoveryPoint) -> None:
        self._store.recovery_points.append(point)

    async def latest_for_run(self, run_id: str) -> RecoveryPoint | None:
        points = await self.list_for_run(run_id, limit=1)
        return points[0] if points else None

    async def list_for_run(self, run_id: str, *, limit: int) -> list[RecoveryPoint]:
        matching = [p for p in self._store.recovery_points if p.run_id == run_id]
        return list(reversed(matching))[:limit]


class InMemoryTestPlanRepository:
    """Append-only, like the real one: a plan version is never overwritten."""

    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def add(self, plan: TestPlan) -> None:
        key = (plan.plan_id, plan.plan_version)
        if key in self._store.plans:
            raise AlreadyExistsError("test_plan", f"{plan.plan_id}@{plan.plan_version}")
        self._store.plans[key] = plan

    async def get(self, plan_id: str, plan_version: str) -> TestPlan | None:
        return self._store.plans.get((plan_id, plan_version))

    async def latest(self, plan_id: str) -> TestPlan | None:
        versions = [plan for (pid, _), plan in self._store.plans.items() if pid == plan_id]
        return versions[-1] if versions else None

    async def list_for_story(self, story_id: str, *, limit: int) -> list[TestPlan]:
        matches = [plan for plan in self._store.plans.values() if plan.source_story_id == story_id]
        return list(reversed(matches))[:limit]


class InMemoryCriterionResultRepository:
    """Keyed by criterion, like the real unique constraint: a retried activity replaces
    its answer instead of leaving two contradictory ones."""

    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def record(self, run_id: str, results: Sequence[CriterionResult]) -> None:
        for_run = self._store.criterion_results.setdefault(run_id, {})
        for result in results:
            for_run[result.criterion_id] = result

    async def list_for_run(self, run_id: str) -> list[CriterionResult]:
        return list(self._store.criterion_results.get(run_id, {}).values())

    async def list_recent_failures(
        self, project_id: str, *, limit: int
    ) -> list[RunCriterionResult]:
        failures = []
        # Newest run first, like the real ordering; insertion order stands in for
        # creation order, and the order within a run is preserved either way.
        for run_id in reversed(list(self._store.criterion_results)):
            run = self._store.runs.get(run_id)
            if run is None or run.project_id != project_id:
                continue
            for result in self._store.criterion_results[run_id].values():
                if result.outcome is not CriterionOutcome.NOT_MET or result.model_derived:
                    continue
                failures.append(RunCriterionResult(run_id=run_id, result=result))
                if len(failures) == limit:
                    return failures
        return failures


class InMemoryArtifactIndex:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def record(self, ref: EvidenceRef) -> None:
        self._store.artifacts.setdefault(ref.artifact_id, ref)

    async def get(self, artifact_id: str) -> EvidenceRef | None:
        return self._store.artifacts.get(artifact_id)

    async def list_for_run(self, run_id: str) -> list[EvidenceRef]:
        return [ref for ref in self._store.artifacts.values() if ref.run_id == run_id]


class InMemoryKnowledgeRepository:
    """Same folding rule as PostgreSQL, because it calls the same domain method.

    A double with its own merge logic would let promotion behave one way in tests and
    another in production — precisely the thing these tests exist to catch.
    """

    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def _key(self, candidate: KnowledgeExperienceCandidate) -> tuple[str, str, str]:
        return (candidate.project_id, candidate.environment_id, candidate.dedup_key)

    async def merge(self, candidate: KnowledgeExperienceCandidate) -> KnowledgeExperienceCandidate:
        key = self._key(candidate)
        stored = self._store.knowledge.get(key)
        merged = candidate if stored is None else stored.reinforced_by(candidate)
        self._store.knowledge[key] = merged
        return merged

    async def get(self, candidate_id: str) -> KnowledgeExperienceCandidate | None:
        for candidate in self._store.knowledge.values():
            if candidate.candidate_id == candidate_id:
                return candidate
        return None

    async def list_for_scope(
        self,
        *,
        project_id: str,
        environment_id: str,
        statuses: Sequence[CandidateStatus] | None = None,
        limit: int = 100,
    ) -> list[KnowledgeExperienceCandidate]:
        allowed = set(statuses) if statuses else None
        found = [
            candidate
            for (stored_project, stored_environment, _), candidate in self._store.knowledge.items()
            if stored_project == project_id
            and stored_environment == environment_id
            and (allowed is None or candidate.status in allowed)
        ]
        found.sort(key=lambda item: (item.quality.reliability, item.created_at), reverse=True)
        return found[:limit]

    async def save(self, candidate: KnowledgeExperienceCandidate) -> None:
        key = self._key(candidate)
        if key not in self._store.knowledge:
            raise NotFoundError("knowledge candidate", candidate.candidate_id)
        self._store.knowledge[key] = candidate


class InMemoryMemoryFeedbackRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def record(self, feedback: MemoryFeedback) -> bool:
        # Same occurrence key as the unique constraint, so the double cannot accept a
        # duplicate the database would refuse.
        key = (
            feedback.candidate_id,
            feedback.run_id,
            feedback.episode_id or "",
            feedback.kind.value,
        )
        if key in self._store.memory_feedback:
            return False
        self._store.memory_feedback[key] = feedback
        return True

    async def list_for_candidate(
        self, candidate_id: str, *, limit: int = 100
    ) -> list[MemoryFeedback]:
        found = [
            item
            for item in self._store.memory_feedback.values()
            if item.candidate_id == candidate_id
        ]
        found.sort(key=lambda item: (item.created_at, item.feedback_id), reverse=True)
        return found[:limit]


class InMemoryGraphSyncStateRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def mark(self, record: GraphSyncRecord) -> None:
        self._store.graph_sync[record.candidate_id] = record

    async def get(self, candidate_id: str) -> GraphSyncRecord | None:
        return self._store.graph_sync.get(candidate_id)

    async def list_pending(self, *, limit: int = 500) -> list[GraphSyncRecord]:
        return [
            record
            for record in self._store.graph_sync.values()
            if record.state in {GraphSyncState.PENDING, GraphSyncState.FAILED}
        ][:limit]

    async def count_by_state(self) -> dict[GraphSyncState, int]:
        counts = {state: 0 for state in GraphSyncState}
        for record in self._store.graph_sync.values():
            counts[record.state] += 1
        return counts


class InMemoryFailureClusterRepository:
    """Accumulating triage, with the same two-write split as the tables.

    `record` never touches a hypothesis and `record_hypothesis` never touches members,
    so a test that gets this wrong fails here rather than in production.
    """

    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def record(
        self, project_id: str, clusters: Sequence[FailureCluster], *, now: datetime
    ) -> None:
        for cluster in clusters:
            key = (project_id, cluster.cluster_id)
            existing = self._store.failure_clusters.get(key)
            members = list(existing.members) if existing is not None else []
            known = {(member.run_id, member.criterion_id) for member in members}
            for signal in cluster.members:
                pair = (signal.run_id, signal.criterion_id)
                if pair not in known:
                    known.add(pair)
                    members.append(ClusterMember(run_id=signal.run_id, criterion_id=pair[1]))
            representative = cluster.representative
            self._store.failure_clusters[key] = StoredCluster(
                cluster_id=cluster.cluster_id,
                project_id=project_id,
                failure_kind=representative.failure_kind.value,
                criterion_id=representative.criterion_id,
                status=cluster.status.value,
                reason=cluster.reason,
                observation=representative.normalized_observation,
                representative_run_id=representative.run_id,
                first_seen_at=existing.first_seen_at if existing is not None else now,
                last_seen_at=now,
                members=tuple(members),
                http_status=representative.http_status,
                route=representative.route,
                blocked_by=cluster.blocked_by,
                hypothesis=existing.hypothesis if existing is not None else None,
            )

    async def record_hypothesis(
        self,
        project_id: str,
        cluster_id: str,
        *,
        analyzed_run_id: str,
        hypothesis: ClusterHypothesis,
    ) -> bool:
        key = (project_id, cluster_id)
        stored = self._store.failure_clusters.get(key)
        if stored is None:
            raise NotFoundError("failure_cluster", cluster_id)
        pass_key = (project_id, cluster_id, analyzed_run_id)
        if pass_key in self._store.cluster_hypotheses:
            return False
        self._store.cluster_hypotheses[pass_key] = hypothesis
        self._store.failure_clusters[key] = replace(stored, hypothesis=hypothesis)
        return True

    async def list_for_project(self, project_id: str, *, limit: int) -> list[StoredCluster]:
        stored = [
            cluster
            for (project, _), cluster in self._store.failure_clusters.items()
            if project == project_id
        ]
        stored.sort(key=lambda cluster: (cluster.last_seen_at, cluster.cluster_id), reverse=True)
        return stored[:limit]


class InMemoryStateMapRepository:
    """Exploration maps, keyed by run like the real table.

    `previous_run` reads insertion order, which is the double's stand-in for recording
    order — enough to prove a caller compares against the right map, and it fails the
    same way the real one would if a caller expected "the last good run" instead of
    "the last run".
    """

    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def record(
        self, run_id: str, project_id: str, state_map: StateMap, report: ExplorationReport
    ) -> None:
        self._store.state_maps[run_id] = (project_id, state_map, report)

    async def get(self, run_id: str) -> StateMap | None:
        stored = self._store.state_maps.get(run_id)
        return stored[1] if stored is not None else None

    async def report_for(self, run_id: str) -> ExplorationReport | None:
        stored = self._store.state_maps.get(run_id)
        return stored[2] if stored is not None else None

    async def previous_run(self, project_id: str, *, before_run_id: str) -> str | None:
        recorded = [
            run_id
            for run_id, (project, _map, _report) in self._store.state_maps.items()
            if project == project_id
        ]
        if before_run_id not in recorded:
            return None
        index = recorded.index(before_run_id)
        return recorded[index - 1] if index > 0 else None
