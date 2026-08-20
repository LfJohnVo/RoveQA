"""Analyse a finished run's failures: group first, ask a model second, store both.

Runs at a run boundary, after the verdict is durable. Like consolidation, it must never
be able to change what a run reported: a cluster is a second reading of results that
are already written, and a deep model being down is not a QA outcome.

The order of the writes is deliberate:

1. read the project's recent deterministic failures,
2. group them — no I/O, no model,
3. **commit the clusters**,
4. ask the deep model about the largest independent ones it has not already
   explained,
5. commit the hypotheses.

Step 3 before step 4 is what makes this safe to interrupt. Deep inference takes minutes;
a crash in the middle leaves the deterministic triage durable and useful, and the retry
re-derives the same clusters (their ids come from the grouping key) and asks again. And
holding a database transaction open across a call that costs minutes is exactly what
`.claude/rules` forbids — the model call happens between transactions, not inside one.
"""

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime

from agentic_qa.application.errors import AlreadyExistsError, NotFoundError
from agentic_qa.application.ports.deep_analysis import AnalyzedCluster, DeepAnalyst
from agentic_qa.application.ports.idempotency import (
    FAILURE_ANALYSIS_SCOPE,
    IdempotencyRecord,
    request_fingerprint,
)
from agentic_qa.application.ports.results import RunCriterionResult
from agentic_qa.application.ports.triage import StoredCluster
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.application.services.deep_analysis import (
    DEFAULT_MAX_ANALYZED,
    DeepAnalysisService,
)
from agentic_qa.domain.triage.clustering import FailureCluster, triage
from agentic_qa.domain.triage.signals import FailureSignal, signal_from

logger = logging.getLogger(__name__)

FAILURE_BATCH_LIMIT = 300
"""How many recent failures one pass groups.

Clustering across runs is the point — twenty runs hitting one wall is one problem — so
the batch is the project's recent history rather than this run alone. Bounded because
the history only grows, and a pass whose cost grows with it would eventually stop
running at all.
"""

CLUSTER_PAGE_LIMIT = 200

GROWTH_FACTOR_TO_REASK = 2
"""How much bigger a cluster must get before its explanation is bought again.

Doubling, rather than any growth at all: one more run hitting a known wall is
confirmation, not news, and paying for a fresh hypothesis on every confirmation is
how a cheap addition turns into the most expensive thing the system does."""


@dataclass(frozen=True)
class AnalyzeFailuresCommand:
    run_id: str


@dataclass(frozen=True)
class AnalyzeFailuresResult:
    clusters: tuple[StoredCluster, ...]
    hypotheses_recorded: int
    replayed: bool
    """True when this run's pass already ran. Nothing is re-asked and nothing is
    re-written; the stored clusters come back as they are."""


async def analyze_failures(
    uow_factory: Callable[[], UnitOfWork],
    command: AnalyzeFailuresCommand,
    *,
    analyst: DeepAnalyst | None = None,
    now: datetime,
    max_clusters: int = DEFAULT_MAX_ANALYZED,
    batch_limit: int = FAILURE_BATCH_LIMIT,
) -> AnalyzeFailuresResult:
    async with uow_factory() as uow:
        run = await uow.runs.get(command.run_id)
        if run is None:
            raise NotFoundError("run", command.run_id)
        project_id = run.project_id

        if await uow.idempotency.get(FAILURE_ANALYSIS_SCOPE, command.run_id) is not None:
            stored = await uow.failure_clusters.list_for_project(
                project_id, limit=CLUSTER_PAGE_LIMIT
            )
            return AnalyzeFailuresResult(
                clusters=tuple(stored), hypotheses_recorded=0, replayed=True
            )

        failures = await uow.criterion_results.list_recent_failures(project_id, limit=batch_limit)
        # Read *before* this pass overwrites it: deciding what is worth asking again
        # needs the size a cluster had when it was last explained.
        previous = await uow.failure_clusters.list_for_project(project_id, limit=CLUSTER_PAGE_LIMIT)

    triaged = triage(_signals(failures))
    if not triaged.clusters:
        return AnalyzeFailuresResult(clusters=(), hypotheses_recorded=0, replayed=False)

    # Durable before anything slow happens. From here on, an interruption costs
    # hypotheses, never the grouping.
    async with uow_factory() as uow:
        await uow.failure_clusters.record(project_id, triaged.clusters, now=now)
        await uow.commit()

    analyzed = await DeepAnalysisService(
        analyst, max_clusters=max_clusters, worth_asking=_freshness_rule(previous)
    ).analyze(triaged)

    async with uow_factory() as uow:
        recorded = await _store_hypotheses(uow, project_id, command.run_id, analyzed)
        try:
            await uow.idempotency.add(
                IdempotencyRecord(
                    scope=FAILURE_ANALYSIS_SCOPE,
                    key=command.run_id,
                    request_fingerprint=request_fingerprint(
                        FAILURE_ANALYSIS_SCOPE, {"run_id": command.run_id}
                    ),
                    resource_id=command.run_id,
                )
            )
        except AlreadyExistsError:
            # A concurrent pass for the same run got there first. Its hypotheses are
            # equivalent to ours and already durable, so this one has nothing to add.
            logger.info("failure analysis for run %s was already recorded", command.run_id)
            return AnalyzeFailuresResult(clusters=(), hypotheses_recorded=0, replayed=True)
        stored = await uow.failure_clusters.list_for_project(project_id, limit=CLUSTER_PAGE_LIMIT)
        await uow.commit()

    return AnalyzeFailuresResult(
        clusters=tuple(stored), hypotheses_recorded=recorded, replayed=False
    )


def _freshness_rule(previous: Sequence[StoredCluster]) -> Callable[[FailureCluster], bool]:
    """Ask about a cluster only when the answer could have changed.

    This is the "repeated-failure condition" of the phase plan, read as a spending rule.
    Every finished run triggers a pass, and a project with one long-standing wall would
    otherwise buy the same explanation of the same cluster once per run — minutes of
    deep inference for an answer already stored.

    Three cases are worth the call: a problem nobody has seen before, one that was never
    successfully explained (the deep endpoint was down, or answered unusably), and one
    that has grown enough that its earlier explanation may no longer fit.
    """
    known = {cluster.cluster_id: cluster for cluster in previous}

    def worth_asking(cluster: FailureCluster) -> bool:
        seen = known.get(cluster.cluster_id)
        if seen is None or seen.hypothesis is None or seen.hypothesis.failure is not None:
            return True
        return len(cluster.run_ids) >= max(2, len(seen.run_ids) * GROWTH_FACTOR_TO_REASK)

    return worth_asking


def _signals(failures: Sequence[RunCriterionResult]) -> list[FailureSignal]:
    """Reduce stored results to comparable signals, dropping what cannot be grouped.

    The route is not available here: `criterion_results` records the criterion's answer,
    not the URL it was answered on. Grouping still works on kind, criterion, status and
    the normalised observation — one fewer signal, not a broken one.
    """
    signals = []
    for failure in failures:
        signal = signal_from(failure.result, run_id=failure.run_id)
        if signal is not None:
            signals.append(signal)
    return signals


async def _store_hypotheses(
    uow: UnitOfWork,
    project_id: str,
    analyzed_run_id: str,
    analyzed: Sequence[AnalyzedCluster],
) -> int:
    recorded = 0
    for item in analyzed:
        if item.hypothesis is None:
            continue
        if await uow.failure_clusters.record_hypothesis(
            project_id,
            item.cluster.cluster_id,
            analyzed_run_id=analyzed_run_id,
            hypothesis=item.hypothesis,
        ):
            recorded += 1
    return recorded
