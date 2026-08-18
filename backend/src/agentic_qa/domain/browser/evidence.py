"""Evidence identity and provenance (docs/11).

An `EvidenceSet` is a coherent collection captured within one run and context. Every
artifact carries the run and evidence set it belongs to, so a manifest can be checked
for consistency instead of trusted.

The rule this file exists to enforce: a bundle never mixes artifacts from different
runs, evidence sets or plan versions. "Latest artifact" lookups are how that happens
by accident, so identity travels with the artifact rather than being inferred later.
"""

from dataclasses import dataclass, field
from datetime import datetime

from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.domain.validation import require_identifier, require_text


@dataclass(frozen=True)
class EvidenceRef:
    """Identity of one captured artifact."""

    artifact_id: str
    run_id: str
    evidence_set_id: str
    kind: str
    relative_path: str
    sha256: str
    size_bytes: int
    captured_at: datetime
    step_id: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("artifact_id", "run_id", "evidence_set_id"):
            require_identifier(getattr(self, field_name), field=field_name)
        require_text(self.kind, field="kind", max_length=100)
        if len(self.sha256) != 64:
            raise InvalidEntityError("sha256 must be a 64 character hex digest")
        if self.size_bytes < 0:
            raise InvalidEntityError("size_bytes must not be negative")


class EvidenceContaminationError(InvalidEntityError):
    """A manifest was asked to hold artifacts that do not share one provenance."""


@dataclass
class EvidenceSet:
    """Artifacts captured under one run and one coherent context."""

    evidence_set_id: str
    run_id: str
    artifacts: list[EvidenceRef] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.evidence_set_id = require_identifier(self.evidence_set_id, field="evidence_set_id")
        self.run_id = require_identifier(self.run_id, field="run_id")
        for artifact in self.artifacts:
            self._require_same_provenance(artifact)

    def add(self, artifact: EvidenceRef) -> None:
        self._require_same_provenance(artifact)
        self.artifacts.append(artifact)

    def _require_same_provenance(self, artifact: EvidenceRef) -> None:
        if artifact.run_id != self.run_id:
            raise EvidenceContaminationError(
                f"artifact {artifact.artifact_id} belongs to run {artifact.run_id}, "
                f"not {self.run_id}"
            )
        if artifact.evidence_set_id != self.evidence_set_id:
            raise EvidenceContaminationError(
                f"artifact {artifact.artifact_id} belongs to evidence set "
                f"{artifact.evidence_set_id}, not {self.evidence_set_id}"
            )
