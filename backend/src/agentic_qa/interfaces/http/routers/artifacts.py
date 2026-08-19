"""Artifact download.

An artifact id is an identifier, never a filesystem path (docs/25). The row in the
index is what resolves it to bytes, and the repository verifies the hash on read — so
an artifact that was swapped or corrupted on disk is refused rather than served as
the real evidence.
"""

from fastapi import APIRouter, Response

from agentic_qa.application.errors import NotFoundError
from agentic_qa.interfaces.http.dependencies import ArtifactRepositoryDep, UnitOfWorkDep

router = APIRouter(prefix="/api/v1/artifacts", tags=["artifacts"])


@router.get("/{artifact_id}")
async def download_artifact(
    artifact_id: str, uow: UnitOfWorkDep, artifacts: ArtifactRepositoryDep
) -> Response:
    ref = await uow.artifacts.get(artifact_id)
    if ref is None:
        raise NotFoundError("artifact", artifact_id)

    data = await artifacts.read(ref)
    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={
            # Provenance travels with the bytes, so a downloaded file can still be
            # checked against the manifest that referenced it.
            "X-Artifact-Sha256": ref.sha256,
            "X-Run-Id": ref.run_id,
            "X-Evidence-Set-Id": ref.evidence_set_id,
        },
    )
