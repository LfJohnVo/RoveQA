"""Create a project.

Use cases never commit: the caller owns the transaction boundary, so an adapter can
group several writes and keep transactions short (docs/09 + postgresql skill).
"""

from dataclasses import dataclass
from uuid import uuid4

from agentic_qa.application.ports.repositories import ProjectRepository
from agentic_qa.domain.projects.project import Project


@dataclass(frozen=True)
class CreateProjectCommand:
    name: str


async def create_project(projects: ProjectRepository, command: CreateProjectCommand) -> Project:
    project = Project(project_id=str(uuid4()), name=command.name)
    await projects.add(project)
    return project
