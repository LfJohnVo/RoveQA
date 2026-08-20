"""What memory is doing, and whether it is worth its cost.

Same shape as the inference metrics: in-process counters plus a structured log line,
which is what a single-node deployment needs before there is a backend to scrape.

The numbers are chosen so the phase's own claim can be checked in production rather
than only in the benchmark. A retrieval hit rate that collapses, or a projection that
never catches up, is how "warm runs are faster" stops being true — and neither shows up
in a run's verdict, so nothing else would notice.

Summaries and payloads are never recorded. They derive from page content, which is
untrusted data and may carry fixture credentials (docs/13).
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MemoryMetrics:
    retrievals: int = 0
    warm_retrievals: int = 0
    """Retrievals that returned at least one item. The rest ran cold."""

    items_offered: int = 0
    items_needing_revalidation: int = 0
    model_derived_offered: int = 0
    """Hypotheses offered. Worth watching on its own: a context filling up with guesses
    means promotion has stalled, which a total item count would hide."""

    candidates_learned: int = 0
    candidates_contradicted: int = 0
    graph_writes: int = 0
    graph_removals: int = 0
    graph_failures: int = 0

    @property
    def hit_rate(self) -> float:
        return self.warm_retrievals / self.retrievals if self.retrievals else 0.0

    def record_retrieval(
        self, *, project_id: str, items: int, revalidate: int, model_derived: int
    ) -> None:
        self.retrievals += 1
        if items:
            self.warm_retrievals += 1
        self.items_offered += items
        self.items_needing_revalidation += revalidate
        self.model_derived_offered += model_derived
        logger.info(
            "memory.retrieval",
            extra={
                "project_id": project_id,
                "items": items,
                "revalidate": revalidate,
                "model_derived": model_derived,
                "hit_rate": round(self.hit_rate, 3),
            },
        )

    def record_consolidation(self, *, run_id: str, learned: int, contradicted: int) -> None:
        self.candidates_learned += learned
        self.candidates_contradicted += contradicted
        logger.info(
            "memory.consolidation",
            extra={"run_id": run_id, "learned": learned, "contradicted": contradicted},
        )

    def record_sync(self, *, materialized: int, forgotten: int, failed: int) -> None:
        self.graph_writes += materialized
        self.graph_removals += forgotten
        self.graph_failures += failed
        logger.info(
            "memory.sync",
            extra={"materialized": materialized, "forgotten": forgotten, "failed": failed},
        )
