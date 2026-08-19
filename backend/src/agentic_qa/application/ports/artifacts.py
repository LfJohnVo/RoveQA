"""Artifact storage port.

Filesystem today, S3/MinIO later (ADR 0005) — which is why callers never see a path,
only an `EvidenceRef` carrying identity, hash and size.

Writes are bounded: an artifact that would exceed the cap is refused rather than
filling the disk with something nobody asked for (docs/11 bounded reads/writes).
"""

from collections.abc import AsyncIterator
from typing import Protocol

from agentic_qa.domain.browser.evidence import EvidenceRef

MAX_ARTIFACT_BYTES = 50 * 1024 * 1024


class ArtifactTooLargeError(Exception):
    """The artifact exceeded the configured cap and was not stored."""


class ArtifactRepository(Protocol):
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
        """Persist one artifact and return its identity, hash and size."""
        ...

    async def read(self, ref: EvidenceRef) -> bytes:
        """Read an artifact back, verifying it still matches its recorded hash."""
        ...


class ArtifactIndex(Protocol):
    """Durable index of captured artifacts (docs/11: references in the database).

    Separate from `ArtifactRepository` because the two answer different questions:
    the repository owns bytes, this owns "what does run X have, and does it all
    belong to the same evidence set". A failure bundle cannot be checked for
    contamination without the second.
    """

    async def record(self, ref: EvidenceRef) -> None:
        """Index one artifact. Idempotent by artifact id."""
        ...

    async def list_for_run(self, run_id: str) -> list[EvidenceRef]: ...
