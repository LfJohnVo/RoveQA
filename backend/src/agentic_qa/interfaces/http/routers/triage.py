"""Failure triage: what a project keeps failing at, grouped.

Read-only. The clusters are written at run boundaries by a durable activity, not on
demand — grouping is a consequence of runs finishing, and a GET that recomputed it
would give a different answer depending on who asked and when.

The response keeps the two halves apart in the shape itself: the members and the
grouping reason are what was observed, `hypothesis` is what a large model guessed, and
a client rendering them has no way to accidentally present the second as the first.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from agentic_qa.application.ports.triage import StoredCluster
from agentic_qa.bootstrap.container import Container
from agentic_qa.interfaces.http.dependencies import get_container
from agentic_qa.interfaces.http.schemas import (
    ClusterHypothesisResponse,
    ClusterMemberResponse,
    FailureClusterPageResponse,
    FailureClusterResponse,
)

router = APIRouter(prefix="/api/v1/projects/{project_id}/failure-clusters", tags=["triage"])

ContainerDep = Annotated[Container, Depends(get_container)]
ProjectPath = Annotated[str, Path(min_length=1, max_length=200)]
LimitQuery = Annotated[int, Query(ge=1, le=200)]


@router.get("", response_model=FailureClusterPageResponse)
async def list_clusters(
    container: ContainerDep,
    project_id: ProjectPath,
    limit: LimitQuery = 50,
) -> FailureClusterPageResponse:
    async with container.unit_of_work() as uow:
        clusters = await uow.failure_clusters.list_for_project(project_id, limit=limit)
    return FailureClusterPageResponse(
        project_id=project_id,
        clusters=[_response(cluster) for cluster in clusters],
        # Counted here rather than left to the client: a report that says "3 problems"
        # while listing eleven rows is how a cascade gets read as eleven defects.
        counted_as_defects=sum(1 for cluster in clusters if cluster.status == "independent"),
    )


def _response(cluster: StoredCluster) -> FailureClusterResponse:
    return FailureClusterResponse(
        cluster_id=cluster.cluster_id,
        failure_kind=cluster.failure_kind,
        criterion_id=cluster.criterion_id,
        status=cluster.status,
        reason=cluster.reason,
        observation=cluster.observation,
        http_status=cluster.http_status,
        route=cluster.route,
        blocked_by=cluster.blocked_by,
        representative_run_id=cluster.representative_run_id,
        first_seen_at=cluster.first_seen_at,
        last_seen_at=cluster.last_seen_at,
        size=cluster.size,
        members=[
            ClusterMemberResponse(run_id=member.run_id, criterion_id=member.criterion_id)
            for member in cluster.members
        ],
        hypothesis=(
            ClusterHypothesisResponse(
                probable_cause=cluster.hypothesis.probable_cause,
                recommended_check=cluster.hypothesis.recommended_check,
                confidence=cluster.hypothesis.confidence.value,
                model_derived=cluster.hypothesis.model_derived,
                failure=cluster.hypothesis.failure,
                model_name=(
                    cluster.hypothesis.invocation.model
                    if cluster.hypothesis.invocation is not None
                    else None
                ),
                prompt_version=(
                    cluster.hypothesis.invocation.prompt_version
                    if cluster.hypothesis.invocation is not None
                    else None
                ),
            )
            if cluster.hypothesis is not None
            else None
        ),
    )
