"""Evidence provenance, artifact integrity and page fingerprints.

The contamination tests are the point of Phase 04's evidence gates: a manifest must
be impossible to assemble from more than one run or evidence set.
"""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from agentic_qa.application.ports.artifacts import ArtifactTooLargeError
from agentic_qa.domain.browser.evidence import (
    EvidenceContaminationError,
    EvidenceRef,
    EvidenceSet,
)
from agentic_qa.domain.browser.fingerprint import PageFingerprint, route_pattern
from agentic_qa.infrastructure.artifacts.filesystem.repository import (
    ArtifactIntegrityError,
    FilesystemArtifactRepository,
    UnsafeArtifactNameError,
)


@pytest.fixture
def repository(tmp_path: Path) -> FilesystemArtifactRepository:
    return FilesystemArtifactRepository(tmp_path)


def ref(run_id: str = "r-1", evidence_set_id: str = "es-1") -> EvidenceRef:
    return EvidenceRef(
        artifact_id="a-1",
        run_id=run_id,
        evidence_set_id=evidence_set_id,
        kind="screenshot",
        relative_path="runs/r-1/evidence/es-1/shot.png",
        sha256="0" * 64,
        size_bytes=10,
        captured_at=datetime.now(UTC),
    )


class TestEvidenceProvenance:
    def test_artifacts_of_the_same_run_and_set_are_accepted(self) -> None:
        evidence = EvidenceSet(evidence_set_id="es-1", run_id="r-1")
        evidence.add(ref())

        assert len(evidence.artifacts) == 1

    def test_an_artifact_from_another_run_is_refused(self) -> None:
        """The cross-run contamination the failure-bundle rules forbid."""
        evidence = EvidenceSet(evidence_set_id="es-1", run_id="r-1")

        with pytest.raises(EvidenceContaminationError):
            evidence.add(ref(run_id="r-2"))

    def test_an_artifact_from_another_evidence_set_is_refused(self) -> None:
        evidence = EvidenceSet(evidence_set_id="es-1", run_id="r-1")

        with pytest.raises(EvidenceContaminationError):
            evidence.add(ref(evidence_set_id="es-2"))

    def test_a_contaminated_set_cannot_even_be_constructed(self) -> None:
        with pytest.raises(EvidenceContaminationError):
            EvidenceSet(
                evidence_set_id="es-1",
                run_id="r-1",
                artifacts=[ref(), ref(run_id="r-2")],
            )


class TestArtifactStorage:
    async def test_stores_content_with_hash_size_and_provenance(
        self, repository: FilesystemArtifactRepository
    ) -> None:
        stored = await repository.store(
            run_id="r-1",
            evidence_set_id="es-1",
            kind="screenshot",
            filename="shot.png",
            content=b"binary-content",
        )

        assert stored.run_id == "r-1"
        assert stored.evidence_set_id == "es-1"
        assert stored.size_bytes == len(b"binary-content")
        assert len(stored.sha256) == 64
        # The path itself carries provenance, so a stray file cannot be confused.
        assert stored.relative_path == "runs/r-1/evidence/es-1/shot.png"

    async def test_round_trips_and_verifies_the_hash(
        self, repository: FilesystemArtifactRepository
    ) -> None:
        stored = await repository.store(
            run_id="r-1",
            evidence_set_id="es-1",
            kind="screenshot",
            filename="shot.png",
            content=b"binary-content",
        )

        assert await repository.read(stored) == b"binary-content"

    async def test_tampered_content_is_refused_on_read(
        self, repository: FilesystemArtifactRepository, tmp_path: Path
    ) -> None:
        """Swapped evidence must never be presented as the real thing."""
        stored = await repository.store(
            run_id="r-1",
            evidence_set_id="es-1",
            kind="screenshot",
            filename="shot.png",
            content=b"original",
        )
        (tmp_path / stored.relative_path).write_bytes(b"tampered")

        with pytest.raises(ArtifactIntegrityError):
            await repository.read(stored)

    async def test_streamed_content_is_hashed_without_buffering_it_whole(
        self, repository: FilesystemArtifactRepository
    ) -> None:
        async def stream() -> AsyncIterator[bytes]:
            for part in (b"one", b"two", b"three"):
                yield part

        stored = await repository.store(
            run_id="r-1",
            evidence_set_id="es-1",
            kind="trace",
            filename="trace.bin",
            content=stream(),
        )

        assert stored.size_bytes == len(b"onetwothree")
        assert await repository.read(stored) == b"onetwothree"

    async def test_oversized_artifacts_are_refused_and_leave_nothing_behind(
        self, tmp_path: Path
    ) -> None:
        repository = FilesystemArtifactRepository(tmp_path, max_bytes=8)

        with pytest.raises(ArtifactTooLargeError):
            await repository.store(
                run_id="r-1",
                evidence_set_id="es-1",
                kind="video",
                filename="huge.bin",
                content=b"x" * 100,
            )

        # A truncated file would later look like valid evidence.
        assert not (tmp_path / "runs/r-1/evidence/es-1/huge.bin").exists()

    @pytest.mark.parametrize("name", ["../escape.png", "nested/shot.png", "sh ot.png", ""])
    async def test_unsafe_names_cannot_escape_the_evidence_directory(
        self, repository: FilesystemArtifactRepository, name: str
    ) -> None:
        with pytest.raises(UnsafeArtifactNameError):
            await repository.store(
                run_id="r-1",
                evidence_set_id="es-1",
                kind="screenshot",
                filename=name,
                content=b"x",
            )


class TestPageFingerprint:
    def test_identifier_segments_collapse_so_sibling_records_agree(self) -> None:
        assert route_pattern("http://app.test/records/42") == "/records/{id}"
        assert (
            route_pattern("http://app.test/records/2b7f7f4e-4c1c-4a4e-9f6a-0f2a2f7a5c11/edit")
            == "/records/{id}/edit"
        )

    def test_the_same_screen_with_different_data_has_one_fingerprint(self) -> None:
        first = PageFingerprint.build(
            url="http://app.test/records/1", title="Record", controls=("button:Save",)
        )
        second = PageFingerprint.build(
            url="http://app.test/records/999", title="Record", controls=("button:Save",)
        )

        assert first.matches(second)

    def test_control_order_does_not_change_the_fingerprint(self) -> None:
        first = PageFingerprint.build(
            url="http://app.test/x", title="X", controls=("button:Save", "textbox:Name")
        )
        second = PageFingerprint.build(
            url="http://app.test/x", title="X", controls=("textbox:Name", "button:Save")
        )

        assert first.matches(second)

    def test_a_changed_control_set_changes_the_fingerprint(self) -> None:
        """A redesign must force revalidation rather than reuse a stale playbook."""
        before = PageFingerprint.build(
            url="http://app.test/x", title="X", controls=("button:Save",)
        )
        after = PageFingerprint.build(
            url="http://app.test/x", title="X", controls=("button:Save", "button:Delete")
        )

        assert not before.matches(after)

    def test_a_different_route_changes_the_fingerprint(self) -> None:
        assert not PageFingerprint.build(url="http://app.test/a", title="X", controls=()).matches(
            PageFingerprint.build(url="http://app.test/b", title="X", controls=())
        )
