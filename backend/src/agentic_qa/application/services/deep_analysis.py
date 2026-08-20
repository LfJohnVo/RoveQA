"""Asking a large model about what triage could not explain.

The order is the point (`plans/phase-11-airllm-deep-analysis.md`): failures are grouped
deterministically first, and only then does anything reach a model. Twenty runs that hit
one wall become one question instead of twenty, and the clusters triage already
explained — the ones that failed downstream of a broken setup — are not asked about at
all, because the deterministic pass has the answer.

Everything here is optional work. No deep endpoint, a saturated one, one that times out:
each ends with `hypothesis=None` or a hypothesis carrying its failure, and the clusters
come back regardless. A run's findings never depend on a large model being up.
"""

from collections.abc import Callable

from agentic_qa.application.ports.deep_analysis import (
    AnalyzedCluster,
    ClusterAnalysisRequest,
    DeepAnalyst,
)
from agentic_qa.domain.triage.clustering import FailureCluster, TriageResult

DEFAULT_MAX_ANALYZED = 5
"""How many clusters one run boundary may spend deep inference on.

Bounded because a deep call costs minutes: a run that fell apart into thirty distinct
problems must not turn into thirty sequential large-model calls. Clusters arrive sorted
by size, so the cap keeps the problems the most runs hit.
"""


class DeepAnalysisService:
    """Decides which clusters are worth a large model, and asks about those only.

    Three filters, cheapest first: the cluster must be a defect in its own right rather
    than a consequence triage already explained; it must pass `worth_asking`, which is
    where a caller says "nothing has changed about this one since last time"; and the
    pass must still have budget.
    """

    def __init__(
        self,
        analyst: DeepAnalyst | None = None,
        *,
        max_clusters: int = DEFAULT_MAX_ANALYZED,
        worth_asking: Callable[[FailureCluster], bool] | None = None,
    ) -> None:
        self._analyst = analyst
        self._max_clusters = max_clusters
        self._worth_asking = worth_asking

    async def analyze(self, triaged: TriageResult) -> tuple[AnalyzedCluster, ...]:
        """One result per cluster, in triage order, whether or not a model was asked."""
        budget = self._max_clusters if self._analyst is not None else 0
        analyzed = []
        for cluster in triaged.clusters:
            if budget > 0 and self._analyst is not None and self._should_ask(cluster):
                hypothesis = await self._analyst.analyze(
                    ClusterAnalysisRequest.from_cluster(cluster)
                )
                budget -= 1
                analyzed.append(AnalyzedCluster(cluster=cluster, hypothesis=hypothesis))
            else:
                analyzed.append(AnalyzedCluster(cluster=cluster))
        return tuple(analyzed)

    def _should_ask(self, cluster: FailureCluster) -> bool:
        if not cluster.is_counted_as_defect:
            return False
        return self._worth_asking is None or self._worth_asking(cluster)
