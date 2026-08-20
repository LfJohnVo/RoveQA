"""Deep analysis port: what a large model may be asked about a failure cluster.

Deep analysis is the cold path (docs/08). It never runs between browser steps — a
model that takes minutes to answer cannot sit on the per-action loop — and it is
optional: with no deep endpoint configured, triage still groups failures and the run
still reports them (`plans/phase-11-airllm-deep-analysis.md`).

Two boundaries are enforced by the types here rather than by discipline:

**A hypothesis never becomes evidence.** `ClusterHypothesis` is returned *beside* the
cluster, not merged into it. What is in a cluster and why stays deterministic; only the
suggested cause is model-derived, and it says so in a field that cannot be unset.

**The model sees a summary, not the archive.** `ClusterAnalysisRequest` has nowhere to
put evidence references, artifact paths or page dumps, so no amount of prompt work can
end up shipping every video and trace in a cluster to a large model.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from agentic_qa.application.ports.models import ModelInvocation
from agentic_qa.domain.triage.clustering import FailureCluster


@dataclass(frozen=True)
class ClusterAnalysisRequest:
    """One cluster, reduced to what is worth a large model's time.

    Built from the representative plus the aggregate — how many runs, how they were
    grouped — because that is the question deep analysis answers: not "what happened in
    run 7" but "what explains all of these at once".
    """

    cluster_id: str
    failure_kind: str
    criterion_id: str
    observation: str
    """The representative's normalized observation. Already stripped of the ids and
    numbers that differ per run, so the model is not handed noise to explain."""

    grouping_reason: str
    affected_runs: int
    route: str | None = None
    http_status: str | None = None
    page_fingerprint: str | None = None

    @classmethod
    def from_cluster(cls, cluster: FailureCluster) -> "ClusterAnalysisRequest":
        representative = cluster.representative
        return cls(
            cluster_id=cluster.cluster_id,
            failure_kind=representative.failure_kind.value,
            criterion_id=representative.criterion_id,
            observation=representative.normalized_observation,
            grouping_reason=cluster.reason,
            affected_runs=len(cluster.run_ids),
            route=representative.route,
            http_status=representative.http_status,
            page_fingerprint=representative.page_fingerprint,
        )


class HypothesisConfidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class ClusterHypothesis:
    """A model's guess at why a cluster happened, labelled as a guess.

    `failure` set and everything else empty is a valid, expected result: the deep
    endpoint being down or slow leaves the cluster exactly as triage left it. That is
    the difference between deep analysis being unavailable and a run being broken.
    """

    cluster_id: str
    probable_cause: str = ""
    recommended_check: str = ""
    """What a human could do to confirm or kill the hypothesis. A cause nobody can
    check is a sentence, not a finding."""

    confidence: HypothesisConfidence = HypothesisConfidence.LOW
    model_derived: bool = True
    """Always true, like `CriterionJudgement.model_derived`. Kept as a field so it
    survives serialisation into reports and the durable store."""

    invocation: ModelInvocation | None = None
    failure: str | None = None

    def __post_init__(self) -> None:
        if self.failure is not None and self.probable_cause:
            raise ValueError("a failed analysis cannot also carry a cause")
        if not self.model_derived:
            raise ValueError("a hypothesis is model-derived by definition")


@dataclass(frozen=True)
class AnalyzedCluster:
    """Deterministic evidence and model interpretation, side by side and never merged.

    The separation is structural: `cluster` holds the members, the grouping reason and
    the evidence that justify it, and no hypothesis can rewrite them. A report can show
    both and a reader can always tell which half was observed.
    """

    cluster: FailureCluster
    hypothesis: ClusterHypothesis | None = None
    """Absent when nothing was asked — no analyst configured, or the cluster was
    already explained deterministically."""


class DeepAnalyst(Protocol):
    async def analyze(self, request: ClusterAnalysisRequest) -> ClusterHypothesis: ...
