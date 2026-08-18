"""Read one project."""

from agentic_qa.application.errors import NotFoundError
from agentic_qa.application.ports.repositories import ProjectRepository
from agentic_qa.domain.projects.project import Project


async def get_project(projects: ProjectRepository, project_id: str) -> Project:
    """Return the project or raise NotFoundError; delivery maps it to its protocol."""
    project = await projects.get(project_id)
    if project is None:
        raise NotFoundError("project", project_id)
    return project
