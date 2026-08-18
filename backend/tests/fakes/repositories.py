"""In-memory repository doubles.

They copy entities on the way in and out so callers cannot mutate stored state by
holding a reference — the same isolation a real database gives. All repositories of
one unit of work share a single `InMemoryStore`, which is what makes the fake
transaction able to roll back for real.
"""

from dataclasses import dataclass, field, replace

from agentic_qa.application.errors import AlreadyExistsError
from agentic_qa.domain.projects.project import Project
from agentic_qa.domain.qa.user_story import UserStory
from agentic_qa.domain.runs.run import Run


@dataclass
class InMemoryStore:
    projects: dict[str, Project] = field(default_factory=dict)
    stories: dict[str, UserStory] = field(default_factory=dict)
    runs: dict[str, Run] = field(default_factory=dict)

    def snapshot(self) -> "InMemoryStore":
        return InMemoryStore(
            projects=dict(self.projects),
            stories=dict(self.stories),
            runs=dict(self.runs),
        )

    def restore(self, snapshot: "InMemoryStore") -> None:
        # Restored in place so repositories holding this store see the rollback.
        self.projects.clear()
        self.projects.update(snapshot.projects)
        self.stories.clear()
        self.stories.update(snapshot.stories)
        self.runs.clear()
        self.runs.update(snapshot.runs)


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
