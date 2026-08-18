"""Create a project.

Commands own their transaction and commit; queries take repositories (ADR 0010).
"""

from dataclasses import dataclass
from uuid import uuid4

from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.domain.projects.project import Project


@dataclass(frozen=True)
class CreateProjectCommand:
    name: str


async def create_project(uow: UnitOfWork, command: CreateProjectCommand) -> Project:
    project = Project(project_id=str(uuid4()), name=command.name)
    await uow.projects.add(project)
    await uow.commit()
    return project
