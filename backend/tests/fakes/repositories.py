"""In-memory repository doubles.

They copy entities on the way in and out so callers cannot mutate stored state by
holding a reference — the same isolation a real database gives. All repositories of
one unit of work share a single `InMemoryStore`, which is what makes the fake
transaction able to roll back for real.
"""

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from uuid import uuid4

from agentic_qa.application.errors import AlreadyExistsError, NotFoundError
from agentic_qa.application.ports.events import NewRunEvent, RunEvent
from agentic_qa.application.ports.idempotency import IdempotencyRecord
from agentic_qa.domain.projects.environment import Environment
from agentic_qa.domain.projects.project import Project
from agentic_qa.domain.projects.run_policy import RunPolicy
from agentic_qa.domain.qa.user_story import UserStory
from agentic_qa.domain.runs.recovery import RecoveryPoint
from agentic_qa.domain.runs.run import Run


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
