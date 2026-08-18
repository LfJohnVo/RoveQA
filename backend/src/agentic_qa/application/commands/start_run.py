"""Start a run, idempotently.

Ordering is the durability contract (ADR 0010): the run and its idempotency record
are committed *before* the workflow is started. If starting then fails, a queued run
exists and is recoverable; the reverse order could leave a workflow with no durable
row behind it.
"""

from dataclasses import dataclass
from uuid import uuid4

from agentic_qa.application.errors import IdempotencyConflictError, NotFoundError
from agentic_qa.application.ports.idempotency import (
    RUN_CREATION_SCOPE,
    IdempotencyRecord,
    request_fingerprint,
)
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.application.ports.workflows import WorkflowGateway
from agentic_qa.domain.runs.run import Run, RunStatus


@dataclass(frozen=True)
class StartRunCommand:
    project_id: str
    idempotency_key: str

    def fingerprint(self) -> str:
        return request_fingerprint(RUN_CREATION_SCOPE, {"project_id": self.project_id})


@dataclass(frozen=True)
class StartRunResult:
    run: Run
    replayed: bool
    """True when an existing run was returned for a repeated request."""


async def start_run(
    uow: UnitOfWork, workflows: WorkflowGateway, command: StartRunCommand
) -> StartRunResult:
    fingerprint = command.fingerprint()
    existing = await uow.idempotency.get(RUN_CREATION_SCOPE, command.idempotency_key)

    if existing is not None:
        if existing.request_fingerprint != fingerprint:
            raise IdempotencyConflictError(RUN_CREATION_SCOPE, command.idempotency_key)
        replayed = await uow.runs.get(existing.resource_id)
        if replayed is None:
            # Record and run commit together, so this cannot happen without data loss.
            raise NotFoundError("run", existing.resource_id)
        return StartRunResult(run=replayed, replayed=True)

    if await uow.projects.get(command.project_id) is None:
        raise NotFoundError("project", command.project_id)

    run = Run(run_id=str(uuid4()), project_id=command.project_id)
    run.transition_to(RunStatus.QUEUED)  # accepted; the worker will pick it up
    await uow.runs.add(run)
    await uow.idempotency.add(
        IdempotencyRecord(
            scope=RUN_CREATION_SCOPE,
            key=command.idempotency_key,
            request_fingerprint=fingerprint,
            resource_id=run.run_id,
        )
    )
    await uow.commit()

    # Durable first, side effect second. Starting is itself idempotent, so a retry
    # after a lost acknowledgement cannot produce a second workflow.
    await workflows.start_run(run.run_id, run.project_id)
    return StartRunResult(run=run, replayed=False)
