"""Create a run draft.

A draft is only CREATED: nothing is queued, no workflow is started and no target is
touched. Starting a run is Temporal's job and lands in Phase 02, so this use case
must not acquire side effects here.
"""

from dataclasses import dataclass
from uuid import uuid4

from agentic_qa.application.errors import NotFoundError
from agentic_qa.application.ports.repositories import ProjectRepository, RunRepository
from agentic_qa.domain.runs.run import Run, RunStatus


@dataclass(frozen=True)
class CreateRunDraftCommand:
    project_id: str


async def create_run_draft(
    projects: ProjectRepository,
    runs: RunRepository,
    command: CreateRunDraftCommand,
) -> Run:
    if await projects.get(command.project_id) is None:
        raise NotFoundError("project", command.project_id)

    run = Run(run_id=str(uuid4()), project_id=command.project_id, status=RunStatus.CREATED)
    await runs.add(run)
    return run
