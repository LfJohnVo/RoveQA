"""Run endpoints.

The handler translates protocol and nothing else: identity, idempotency semantics and
the commit point live in the use case (ADR 0010).
"""

from fastapi import APIRouter, Response, status

from agentic_qa.application.commands.create_run_draft import (
    CreateRunDraftCommand,
    create_run_draft,
)
from agentic_qa.application.errors import NotFoundError
from agentic_qa.interfaces.http.dependencies import IdempotencyKeyDep, UnitOfWorkDep
from agentic_qa.interfaces.http.schemas import CreateRunRequest, RunResponse

router = APIRouter(prefix="/api/v1/runs", tags=["runs"])


@router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def create_run(
    payload: CreateRunRequest,
    idempotency_key: IdempotencyKeyDep,
    uow: UnitOfWorkDep,
    response: Response,
) -> RunResponse:
    """Create a run.

    A repeated request with the same key returns the same run with 200 instead of 201,
    so a client that lost the first response can tell a replay from a fresh creation.
    """
    result = await create_run_draft(
        uow,
        CreateRunDraftCommand(project_id=payload.project_id, idempotency_key=idempotency_key),
    )
    if result.replayed:
        response.status_code = status.HTTP_200_OK
    return RunResponse.from_domain(result.run)


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(run_id: str, uow: UnitOfWorkDep) -> RunResponse:
    """Durable status, read from PostgreSQL — never from ephemeral presence.

    Bounded long-poll (`wait_seconds`) lands in Phase 08 as an extension of this
    handler; it must never host an hours-long loop inside the request.
    """
    run = await uow.runs.get(run_id)
    if run is None:
        raise NotFoundError("run", run_id)
    return RunResponse.from_domain(run)
