"""Create a run, idempotently.

A draft is only CREATED: nothing is queued and no target is touched. Starting the
workflow happens after this transaction commits (ADR 0010), so a failure to start
leaves a recoverable run rather than an orphan workflow.
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
from agentic_qa.domain.runs.run import Run, RunStatus


@dataclass(frozen=True)
class CreateRunDraftCommand:
    project_id: str
    idempotency_key: str

    def fingerprint(self) -> str:
        return request_fingerprint(RUN_CREATION_SCOPE, {"project_id": self.project_id})


@dataclass(frozen=True)
class CreateRunDraftResult:
    run: Run
    replayed: bool
    """True when an existing run was returned for a repeated request."""


async def create_run_draft(uow: UnitOfWork, command: CreateRunDraftCommand) -> CreateRunDraftResult:
    fingerprint = command.fingerprint()
    existing = await uow.idempotency.get(RUN_CREATION_SCOPE, command.idempotency_key)

    if existing is not None:
        if existing.request_fingerprint != fingerprint:
            raise IdempotencyConflictError(RUN_CREATION_SCOPE, command.idempotency_key)
        replayed = await uow.runs.get(existing.resource_id)
        if replayed is None:
            # Record and run commit together, so this cannot happen without data loss.
            raise NotFoundError("run", existing.resource_id)
        return CreateRunDraftResult(run=replayed, replayed=True)

    if await uow.projects.get(command.project_id) is None:
        raise NotFoundError("project", command.project_id)

    run = Run(run_id=str(uuid4()), project_id=command.project_id, status=RunStatus.CREATED)
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
    return CreateRunDraftResult(run=run, replayed=False)
