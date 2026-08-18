"""Run endpoints.

The handler translates protocol and nothing else: identity, idempotency semantics and
the commit point live in the use case (ADR 0010), and status is only ever written by
the workflow's activities — never here.
"""

from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from agentic_qa.application.commands.start_run import StartRunCommand, start_run
from agentic_qa.application.errors import NotFoundError
from agentic_qa.application.ports.events import (
    DEFAULT_EVENT_PAGE_SIZE,
    MAX_EVENT_PAGE_SIZE,
)
from agentic_qa.application.queries.list_run_events import list_run_events
from agentic_qa.interfaces.http.dependencies import (
    EventPublisherDep,
    IdempotencyKeyDep,
    UnitOfWorkDep,
    WorkflowGatewayDep,
)
from agentic_qa.interfaces.http.request_context import get_request_id
from agentic_qa.interfaces.http.schemas import (
    CreateRunRequest,
    RunAcceptedResponse,
    RunEventPageResponse,
    RunEventResponse,
    RunResponse,
)

router = APIRouter(prefix="/api/v1/runs", tags=["runs"])


@router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def create_run(
    payload: CreateRunRequest,
    idempotency_key: IdempotencyKeyDep,
    uow: UnitOfWorkDep,
    workflows: WorkflowGatewayDep,
    publisher: EventPublisherDep,
    response: Response,
) -> RunResponse:
    """Start a run.

    A repeated request with the same key returns the same run with 200 instead of 201,
    so a client that lost the first response can tell a replay from a fresh creation.
    """
    result = await start_run(
        uow,
        workflows,
        StartRunCommand(
            project_id=payload.project_id,
            idempotency_key=idempotency_key,
            environment_id=payload.environment_id,
            run_policy_id=payload.run_policy_id,
            request_id=get_request_id(),
        ),
        publisher=publisher,
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


@router.get("/{run_id}/events", response_model=RunEventPageResponse)
async def list_events(
    run_id: str,
    uow: UnitOfWorkDep,
    after: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=MAX_EVENT_PAGE_SIZE)] = DEFAULT_EVENT_PAGE_SIZE,
) -> RunEventPageResponse:
    """Durable event catch-up.

    A client that lost its realtime connection resumes from the last sequence it saw;
    realtime delivery may drop events, this path may not.
    """
    events = await list_run_events(uow, run_id, after=after, limit=limit)
    return RunEventPageResponse(
        events=[RunEventResponse.from_domain(event) for event in events],
        next_after=events[-1].sequence if events else after,
    )


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
