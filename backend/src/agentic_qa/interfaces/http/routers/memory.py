"""Learned-memory administration.

Three operations, and the split between them is the point. `status` reports and never
changes anything; `validate` looks for disagreement between the durable side and the
projection without repairing it; `rebuild` repairs. Folding validation into rebuild
would mean the only way to find out whether the graph is healthy is to rewrite it,
which destroys the evidence of what went wrong.

Every one of them answers from PostgreSQL, so they all still work when the graph is
down — which is exactly when somebody runs them.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi import status as http_status

from agentic_qa.application.commands.sync_knowledge_graph import (
    SyncReport,
    rebuild_project,
    sync_pending,
)
from agentic_qa.application.ports.graph import GraphMemoryPort
from agentic_qa.application.queries.memory_status import MemoryStatus, memory_status
from agentic_qa.bootstrap.container import Container
from agentic_qa.interfaces.http.dependencies import get_container
from agentic_qa.interfaces.http.schemas import (
    MemoryRebuildResponse,
    MemoryStatusResponse,
    MemoryValidateResponse,
)

router = APIRouter(prefix="/api/v1/projects/{project_id}/memory", tags=["memory"])

ContainerDep = Annotated[Container, Depends(get_container)]
ProjectPath = Annotated[str, Path(min_length=1, max_length=200)]
EnvironmentQuery = Annotated[str, Query(min_length=1, max_length=200)]
"""Environment stays a query parameter, not another path segment: memory belongs to a
project, and an environment selects which of that project's memory to look at."""


@router.get("/status", response_model=MemoryStatusResponse)
async def read_status(
    container: ContainerDep,
    project_id: ProjectPath,
    environment_id: EnvironmentQuery = "default",
) -> MemoryStatusResponse:
    report = await memory_status(
        container.unit_of_work(),
        container.graph,
        project_id=project_id,
        environment_id=environment_id,
    )
    return _status_response(report)


@router.post("/validate", response_model=MemoryValidateResponse)
async def validate(
    container: ContainerDep,
    project_id: ProjectPath,
    environment_id: EnvironmentQuery = "default",
) -> MemoryValidateResponse:
    """Report disagreement between durable knowledge and the projection.

    Read-only by design. An operator deciding whether to rebuild needs to see the
    damage first; a validate that silently repaired would answer "healthy" every time
    and hide a graph that keeps falling out of step.
    """
    report = await memory_status(
        container.unit_of_work(),
        container.graph,
        project_id=project_id,
        environment_id=environment_id,
    )
    problems: list[str] = []
    if not report.graph_available:
        problems.append("graph store unreachable")
    if report.sync_pending:
        problems.append(f"{report.sync_pending} candidate(s) not yet projected")
    if report.sync_failed:
        problems.append(f"{report.sync_failed} candidate(s) failed to project")

    return MemoryValidateResponse(
        project_id=project_id,
        environment_id=environment_id,
        healthy=not problems,
        problems=problems,
        status=_status_response(report),
    )


@router.post("/rebuild", response_model=MemoryRebuildResponse)
async def rebuild(
    container: ContainerDep,
    project_id: ProjectPath,
    environment_id: EnvironmentQuery = "default",
) -> MemoryRebuildResponse:
    """Rebuild one project's projection from durable knowledge.

    No idempotency key: rebuilding is naturally idempotent. It derives the projection
    from rows that already exist, so running it twice produces the same graph and
    running it after a partial failure simply finishes the job.
    """
    graph = _require_graph(container)
    outcome = await rebuild_project(
        container.unit_of_work,
        graph,
        project_id=project_id,
        environment_id=environment_id,
        now=datetime.now(UTC),
    )
    return _rebuild_response(project_id, environment_id, outcome)


@router.post("/sync", response_model=MemoryRebuildResponse)
async def sync(
    container: ContainerDep,
    project_id: ProjectPath,
    environment_id: EnvironmentQuery = "default",
) -> MemoryRebuildResponse:
    """Drain the projection backlog without rebuilding.

    What an operator runs after the graph comes back: it catches the projection up
    from the queue instead of rewriting everything the project has ever learned.
    """
    graph = _require_graph(container)
    outcome = await sync_pending(container.unit_of_work, graph, now=datetime.now(UTC))
    return _rebuild_response(project_id, environment_id, outcome)


def _require_graph(container: Container) -> GraphMemoryPort:
    if container.graph is None:
        # Honest rather than a no-op success: an operator who asked for a rebuild and
        # got 200 would believe the projection exists.
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="no learned-memory projection is configured",
        )
    return container.graph


def _status_response(report: MemoryStatus) -> MemoryStatusResponse:
    return MemoryStatusResponse(
        project_id=report.project_id,
        environment_id=report.environment_id,
        graph_available=report.graph_available,
        graph_schema_version=report.graph_schema_version,
        durable_candidates=report.durable_candidates,
        actionable_candidates=report.actionable_candidates,
        sync_pending=report.sync_pending,
        sync_failed=report.sync_failed,
        by_status=report.by_status,
    )


def _rebuild_response(
    project_id: str, environment_id: str, report: SyncReport
) -> MemoryRebuildResponse:
    return MemoryRebuildResponse(
        project_id=project_id,
        environment_id=environment_id,
        materialized=report.materialized,
        forgotten=report.forgotten,
        failed=report.failed,
        graph_available=not report.unavailable,
    )
