"""In-memory repository doubles used by contract and use-case tests.

They copy entities on the way in and out so callers cannot mutate stored state by
holding a reference — the same isolation a real database gives.
"""

from dataclasses import replace

from agentic_qa.application.errors import AlreadyExistsError
from agentic_qa.domain.projects.project import Project
from agentic_qa.domain.qa.user_story import UserStory
from agentic_qa.domain.runs.run import Run


class InMemoryProjectRepository:
    def __init__(self) -> None:
        self._items: dict[str, Project] = {}

    async def add(self, project: Project) -> None:
        if project.project_id in self._items:
            raise AlreadyExistsError("project", project.project_id)
        self._items[project.project_id] = replace(project)

    async def get(self, project_id: str) -> Project | None:
        stored = self._items.get(project_id)
        return replace(stored) if stored is not None else None


class InMemoryStoryRepository:
    def __init__(self) -> None:
        self._items: dict[str, UserStory] = {}

    async def add(self, story: UserStory) -> None:
        if story.story_id in self._items:
            raise AlreadyExistsError("user_story", story.story_id)
        self._items[story.story_id] = replace(story)

    async def get(self, story_id: str) -> UserStory | None:
        stored = self._items.get(story_id)
        return replace(stored) if stored is not None else None

    async def list_for_project(self, project_id: str, *, limit: int) -> list[UserStory]:
        matching = sorted(
            (s for s in self._items.values() if s.project_id == project_id),
            key=lambda s: s.story_id,
        )
        return [replace(story) for story in matching[:limit]]


class InMemoryRunRepository:
    def __init__(self) -> None:
        self._items: dict[str, Run] = {}

    async def add(self, run: Run) -> None:
        if run.run_id in self._items:
            raise AlreadyExistsError("run", run.run_id)
        self._items[run.run_id] = replace(run)

    async def get(self, run_id: str) -> Run | None:
        stored = self._items.get(run_id)
        return replace(stored) if stored is not None else None
