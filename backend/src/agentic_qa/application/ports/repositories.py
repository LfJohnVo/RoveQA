"""Repository ports consumed by the Application layer.

Protocols only: no ORM, driver or framework type may appear here. Adapters live in
infrastructure and raise `AlreadyExistsError` for identity conflicts.
"""

from typing import Protocol

from agentic_qa.domain.projects.project import Project
from agentic_qa.domain.qa.user_story import UserStory
from agentic_qa.domain.runs.run import Run


class ProjectRepository(Protocol):
    async def add(self, project: Project) -> None:
        """Persist a new project. Raises AlreadyExistsError when the id is taken."""
        ...

    async def get(self, project_id: str) -> Project | None: ...


class StoryRepository(Protocol):
    async def add(self, story: UserStory) -> None:
        """Persist a new story. Raises AlreadyExistsError when the id is taken."""
        ...

    async def get(self, story_id: str) -> UserStory | None: ...

    async def list_for_project(self, project_id: str, *, limit: int) -> list[UserStory]:
        """Stories of one project ordered by story_id, capped at `limit`.

        The explicit limit keeps reads bounded (docs/11) and the deterministic order
        keeps client-side diffing stable.
        """
        ...


class RunRepository(Protocol):
    async def add(self, run: Run) -> None:
        """Persist a new run. Raises AlreadyExistsError when the id is taken."""
        ...

    async def get(self, run_id: str) -> Run | None: ...
