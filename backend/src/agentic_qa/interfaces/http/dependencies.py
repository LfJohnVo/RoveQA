"""Request-scoped dependencies.

The unit of work is opened per request and closed with it: leaving the block without
a commit rolls back, so a handler that raises can never half-persist (ADR 0010).
"""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, WebSocket, status

from agentic_qa.application.ports.artifacts import ArtifactRepository
from agentic_qa.application.ports.streams import RunEventPublisher
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.application.ports.workflows import WorkflowGateway
from agentic_qa.bootstrap.container import Container

MAX_IDEMPOTENCY_KEY_LENGTH = 200


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


def container_from_websocket(websocket: WebSocket) -> Container:
    """Separate from the HTTP version on purpose.

    A `Request | WebSocket` union is not something FastAPI can analyse as a
    dependency parameter, so each protocol gets its own tiny accessor.
    """
    container: Container = websocket.app.state.container
    return container


def get_workflows(
    container: Annotated[Container, Depends(get_container)],
) -> WorkflowGateway:
    if container.workflows is None:
        # Fail loudly rather than accepting a run the durable engine will never see.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="workflow engine is not connected",
        )
    return container.workflows


async def get_unit_of_work(
    container: Annotated[Container, Depends(get_container)],
) -> AsyncIterator[UnitOfWork]:
    async with container.unit_of_work() as uow:
        yield uow


UnitOfWorkDep = Annotated[UnitOfWork, Depends(get_unit_of_work)]
WorkflowGatewayDep = Annotated[WorkflowGateway, Depends(get_workflows)]

IdempotencyKeyDep = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=1,
        max_length=MAX_IDEMPOTENCY_KEY_LENGTH,
        description="Required: a retry after a lost response must not create a second run.",
    ),
]


def get_event_publisher(
    container: Annotated[Container, Depends(get_container)],
) -> RunEventPublisher | None:
    """Optional on purpose: without realtime, clients still get durable catch-up."""
    return container.events


EventPublisherDep = Annotated[RunEventPublisher | None, Depends(get_event_publisher)]


def get_artifacts(
    container: Annotated[Container, Depends(get_container)],
) -> ArtifactRepository:
    if container.artifacts is None:
        # Fail loudly rather than reporting a stored artifact as missing.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="artifact storage is not configured",
        )
    return container.artifacts


ArtifactRepositoryDep = Annotated[ArtifactRepository, Depends(get_artifacts)]
