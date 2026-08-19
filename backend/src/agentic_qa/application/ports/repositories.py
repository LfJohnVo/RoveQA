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

    async def list(self, *, limit: int) -> list[Project]:
        """Newest first, bounded. There is no unbounded listing: a page size is a
        promise about response size, and "all of them" is not one."""
        ...

    async def save(self, project: Project) -> None:
        """Persist changes to an existing project. Raises NotFoundError when gone."""
        ...


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

    async def save(self, run: Run) -> None:
        """Persist changes to an existing run. Raises NotFoundError when it is gone."""
        ...
