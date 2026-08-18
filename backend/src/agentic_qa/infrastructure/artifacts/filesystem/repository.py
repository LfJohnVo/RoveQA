"""Filesystem artifact storage.

Layout follows docs/11: `data/runs/{run_id}/evidence/{evidence_set_id}/...`, so the
path itself carries provenance and a stray file cannot be mistaken for another run's.

Content is hashed and counted while streaming, never buffered whole, and a write that
exceeds the cap is aborted and cleaned up instead of half-landing.
"""

import hashlib
import logging
import re
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from agentic_qa.application.ports.artifacts import MAX_ARTIFACT_BYTES, ArtifactTooLargeError
from agentic_qa.domain.browser.evidence import EvidenceRef

logger = logging.getLogger(__name__)

_SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")
CHUNK_SIZE = 64 * 1024


class UnsafeArtifactNameError(Exception):
    """A filename that could escape its evidence directory was refused."""


class ArtifactIntegrityError(Exception):
    """Stored bytes no longer match the hash recorded when they were written."""


class FilesystemArtifactRepository:
    def __init__(self, root: Path, *, max_bytes: int = MAX_ARTIFACT_BYTES) -> None:
        self._root = root
        self._max_bytes = max_bytes

    def _evidence_dir(self, run_id: str, evidence_set_id: str) -> Path:
        return self._root / "runs" / run_id / "evidence" / evidence_set_id

    async def store(
        self,
        *,
        run_id: str,
        evidence_set_id: str,
        kind: str,
        filename: str,
        content: AsyncIterator[bytes] | bytes,
        step_id: str | None = None,
    ) -> EvidenceRef:
        _require_safe_name(filename)
        _require_safe_name(run_id)
        _require_safe_name(evidence_set_id)

        directory = self._evidence_dir(run_id, evidence_set_id)
        directory.mkdir(parents=True, exist_ok=True)
        destination = directory / filename

        digest = hashlib.sha256()
        written = 0
        try:
            with destination.open("wb") as handle:
                async for chunk in _chunks(content):
                    written += len(chunk)
                    if written > self._max_bytes:
                        raise ArtifactTooLargeError(f"{filename} exceeded {self._max_bytes} bytes")
                    digest.update(chunk)
                    handle.write(chunk)
        except ArtifactTooLargeError:
            # Never leave a truncated file that later looks like valid evidence.
            destination.unlink(missing_ok=True)
            raise

        return EvidenceRef(
            artifact_id=str(uuid4()),
            run_id=run_id,
            evidence_set_id=evidence_set_id,
            kind=kind,
            relative_path=f"runs/{run_id}/evidence/{evidence_set_id}/{filename}",
            sha256=digest.hexdigest(),
            size_bytes=written,
            captured_at=datetime.now(UTC),
            step_id=step_id,
        )

    async def read(self, ref: EvidenceRef) -> bytes:
        path = self._root / ref.relative_path
        data = path.read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        if actual != ref.sha256:
            # Corrupted or swapped evidence must never be presented as the real thing.
            raise ArtifactIntegrityError(
                f"{ref.artifact_id} hash mismatch: expected {ref.sha256}, found {actual}"
            )
        return data


def _require_safe_name(value: str) -> None:
    if not _SAFE_NAME.match(value):
        raise UnsafeArtifactNameError(f"unsafe artifact path component: {value!r}")


async def _chunks(content: AsyncIterator[bytes] | bytes) -> AsyncIterator[bytes]:
    if isinstance(content, bytes):
        for start in range(0, len(content), CHUNK_SIZE):
            yield content[start : start + CHUNK_SIZE]
        return
    async for chunk in content:
        yield chunk
