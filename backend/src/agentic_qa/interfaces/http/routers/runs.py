"""Run endpoints.

The handler translates protocol and nothing else: identity, idempotency semantics and
the commit point live in the use case (ADR 0010), and status is only ever written by
the workflow's activities — never here.
"""

from fastapi import APIRouter, Response, status

from agentic_qa.application.commands.start_run import StartRunCommand, start_run
from agentic_qa.application.errors import NotFoundError
from agentic_qa.interfaces.http.dependencies import (
    IdempotencyKeyDep,
    UnitOfWorkDep,
    WorkflowGatewayDep,
)
from agentic_qa.interfaces.http.schemas import (
    CreateRunRequest,
    RunAcceptedResponse,
    RunResponse,
)

router = APIRouter(prefix="/api/v1/runs", tags=["runs"])


@router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def create_run(
    payload: CreateRunRequest,
    idempotency_key: IdempotencyKeyDep,
    uow: UnitOfWorkDep,
    workflows: WorkflowGatewayDep,
    response: Response,
) -> RunResponse:
    """Start a run.

    A repeated request with the same key returns the same run with 200 instead of 201,
    so a client that lost the first response can tell a replay from a fresh creation.
    """
    result = await start_run(
        uow,
        workflows,
        StartRunCommand(project_id=payload.project_id, idempotency_key=idempotency_key),
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


async def _ensure_run_exists(run_id: str, uow: UnitOfWorkDep) -> None:
    if await uow.runs.get(run_id) is None:
        raise NotFoundError("run", run_id)


@router.post(
    "/{run_id}/pause", response_model=RunAcceptedResponse, status_code=status.HTTP_202_ACCEPTED
)
async def pause_run(
    run_id: str, uow: UnitOfWorkDep, workflows: WorkflowGatewayDep
) -> RunAcceptedResponse:
    """Ask the run to pause at its next safe point. Status changes when it does."""
    await _ensure_run_exists(run_id, uow)
    await workflows.request_pause(run_id)
    return RunAcceptedResponse(run_id=run_id, accepted="pause")


@router.post(
    "/{run_id}/resume", response_model=RunAcceptedResponse, status_code=status.HTTP_202_ACCEPTED
)
async def resume_run(
    run_id: str, uow: UnitOfWorkDep, workflows: WorkflowGatewayDep
) -> RunAcceptedResponse:
    await _ensure_run_exists(run_id, uow)
    await workflows.request_resume(run_id)
    return RunAcceptedResponse(run_id=run_id, accepted="resume")


@router.post(
    "/{run_id}/cancel", response_model=RunAcceptedResponse, status_code=status.HTTP_202_ACCEPTED
)
async def cancel_run(
    run_id: str, uow: UnitOfWorkDep, workflows: WorkflowGatewayDep
) -> RunAcceptedResponse:
    """Explicit cancellation, naturally idempotent.

    A client that stops waiting has only detached; only this endpoint cancels.
    """
    await _ensure_run_exists(run_id, uow)
    await workflows.request_cancel(run_id)
    return RunAcceptedResponse(run_id=run_id, accepted="cancel")
