"""Create an environment: one deployment of a project's application.

Commands own their transaction and commit; queries take repositories (ADR 0010).
"""

from dataclasses import dataclass
from uuid import uuid4

from agentic_qa.application.errors import NotFoundError
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.domain.projects.environment import Environment


@dataclass(frozen=True)
class CreateEnvironmentCommand:
    project_id: str
    name: str
    default_run_policy_id: str | None = None


async def create_environment(uow: UnitOfWork, command: CreateEnvironmentCommand) -> Environment:
    """The project is checked first, so a typo in the id is a 404 and not an orphan row
    pointing at nothing."""
    if await uow.projects.get(command.project_id) is None:
        raise NotFoundError("project", command.project_id)

    environment = Environment(
        environment_id=str(uuid4()),
        project_id=command.project_id,
        name=command.name,
        default_run_policy_id=command.default_run_policy_id,
    )
    await uow.environments.add(environment)
    await uow.commit()
    return environment
