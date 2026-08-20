"""Keep the graph projection in step with durable knowledge.

One queue, one direction: PostgreSQL decides what is true and the graph is brought to
match. Nothing here ever reads the graph to decide what to store, because a projection
that can influence its own source is no longer a projection — it is a second source of
truth that nobody can reconcile (ADR 0008).

The queue holds *what changed*, not *what to do*. Each entry is resolved against the
durable row at sync time: a candidate that is actionable gets written, one that has
been invalidated or rejected gets removed. That makes the sync self-healing — however
far behind or however wrong the graph got, replaying the queue converges on whatever
PostgreSQL currently says.

Every failure leaves the entry in the queue. An outage costs freshness in the
projection and nothing else: the durable side is untouched and the next run reads its
memory from PostgreSQL regardless.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from agentic_qa.application.ports.graph import (
    GRAPH_SCHEMA_VERSION,
    GraphMemoryPort,
    GraphUnavailableError,
)
from agentic_qa.application.ports.knowledge import GraphSyncRecord, GraphSyncState
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.domain.knowledge.experience import CandidateStatus

logger = logging.getLogger(__name__)

UnitOfWorkFactory = Callable[[], UnitOfWork]

SYNC_BATCH = 200
"""How much of the backlog one pass drains. Bounded so a rebuild of a large project
makes visible progress in steps rather than one long transaction that either finishes
or loses everything."""

MAX_SYNC_ATTEMPTS = 5
"""After this many failures an entry stops being retried automatically and waits for
an explicit rebuild. Retrying forever would turn one poisoned candidate into a queue
that never drains and a status that never goes green."""


@dataclass(frozen=True)
class SyncReport:
    materialized: int = 0
    forgotten: int = 0
    failed: int = 0
    unavailable: bool = False
    """True when the graph could not be reached at all. Distinguished from failures so
    an operator can tell "the store is down" from "these items are bad"."""


async def enqueue_for_sync(uow: UnitOfWork, candidate_id: str) -> None:
    """Mark one candidate as needing the projection updated.

    Called inside the transaction that changed it, so the queue entry and the change
    commit together. Recorded even when the change was an invalidation: the graph has
    to be told to forget, and "nothing to do" is decided at sync time from the durable
    row rather than guessed here.
    """
    existing = await uow.graph_sync.get(candidate_id)
    await uow.graph_sync.mark(
        GraphSyncRecord(
            candidate_id=candidate_id,
            state=GraphSyncState.PENDING,
            graph_schema_version=existing.graph_schema_version if existing else None,
            graph_node_id=existing.graph_node_id if existing else None,
            # Attempts reset: this is a new change, not another try at the old one.
            attempts=0,
            synced_at=existing.synced_at if existing else None,
        )
    )


async def sync_pending(
    factory: UnitOfWorkFactory,
    graph: GraphMemoryPort,
    *,
    now: datetime,
    limit: int = SYNC_BATCH,
) -> SyncReport:
    """Drain the backlog once. Safe to call repeatedly and safe to interrupt."""
    async with factory() as uow:
        backlog = await uow.graph_sync.list_pending(limit=limit)
        candidates = {
            record.candidate_id: await uow.knowledge.get(record.candidate_id) for record in backlog
        }

    materialized = forgotten = failed = 0
    for record in backlog:
        if record.attempts >= MAX_SYNC_ATTEMPTS:
            continue

        candidate = candidates.get(record.candidate_id)
        try:
            if candidate is not None and candidate.status in _PROJECTED_STATUSES:
                node_id = await graph.materialize(candidate)
                outcome = GraphSyncRecord(
                    candidate_id=record.candidate_id,
                    state=GraphSyncState.SYNCED,
                    graph_schema_version=GRAPH_SCHEMA_VERSION,
                    graph_node_id=node_id,
                    attempts=record.attempts,
                    synced_at=now,
                )
                materialized += 1
            else:
                # Withdrawn durably, or gone entirely. Leaving it in the graph would
                # let traversal keep surfacing knowledge the system has retracted.
                await graph.forget(record.candidate_id)
                outcome = GraphSyncRecord(
                    candidate_id=record.candidate_id,
                    state=GraphSyncState.SYNCED,
                    graph_schema_version=GRAPH_SCHEMA_VERSION,
                    graph_node_id=None,
                    attempts=record.attempts,
                    synced_at=now,
                )
                forgotten += 1
        except GraphUnavailableError as error:
            # The store is down. Stop the pass rather than burning every entry's
            # attempt budget on the same outage.
            logger.warning("graph unavailable, %d entries left pending: %s", len(backlog), error)
            await _record(factory, _failure(record, str(error)))
            return SyncReport(
                materialized=materialized,
                forgotten=forgotten,
                failed=failed + 1,
                unavailable=True,
            )
        except Exception as error:  # noqa: BLE001 - one bad entry must not stop the queue
            logger.exception("projecting candidate %s failed", record.candidate_id)
            await _record(factory, _failure(record, str(error)))
            failed += 1
            continue

        await _record(factory, outcome)

    return SyncReport(materialized=materialized, forgotten=forgotten, failed=failed)


async def rebuild_project(
    factory: UnitOfWorkFactory,
    graph: GraphMemoryPort,
    *,
    project_id: str,
    environment_id: str,
    now: datetime,
) -> SyncReport:
    """Rebuild one project's projection from durable knowledge.

    The recovery path for a lost or corrupted FalkorDB, and the reason losing it is a
    performance event rather than a data loss: no test is re-run, nothing is
    re-observed, and the result is derived entirely from rows PostgreSQL already has.
    """
    try:
        await graph.clear(project_id)
    except GraphUnavailableError as error:
        # Nothing was cleared, so the existing projection is intact and the backlog is
        # unchanged. Reported rather than raised: the durable side is fine, and telling
        # an operator the request failed would suggest something worse happened.
        logger.warning("cannot rebuild %s while the graph is unreachable: %s", project_id, error)
        return SyncReport(unavailable=True)

    async with factory() as uow:
        candidates = await uow.knowledge.list_for_scope(
            project_id=project_id,
            environment_id=environment_id,
            statuses=list(_PROJECTED_STATUSES),
            limit=SYNC_BATCH,
        )
        for candidate in candidates:
            await enqueue_for_sync(uow, candidate.candidate_id)
        await uow.commit()

    logger.info(
        "rebuilding graph for %s/%s from %d durable candidate(s)",
        project_id,
        environment_id,
        len(candidates),
    )
    return await sync_pending(factory, graph, now=now, limit=SYNC_BATCH)


_PROJECTED_STATUSES = frozenset({CandidateStatus.PROMOTED, CandidateStatus.TRUSTED})
"""Only knowledge a planner may act on is projected.

The graph exists to speed up retrieval of usable memory. Projecting unpromoted
observations would fill it with things retrieval must then filter out, and every
filter that runs after retrieval is one that can be forgotten.
"""


def _failure(record: GraphSyncRecord, error: str) -> GraphSyncRecord:
    return GraphSyncRecord(
        candidate_id=record.candidate_id,
        state=GraphSyncState.FAILED,
        graph_schema_version=record.graph_schema_version,
        graph_node_id=record.graph_node_id,
        attempts=record.attempts + 1,
        last_error=error[:500],
        synced_at=record.synced_at,
    )


async def _record(factory: UnitOfWorkFactory, outcome: GraphSyncRecord) -> None:
    """Committed per entry, not per batch: an interrupted pass must keep the progress
    it made rather than replaying writes the graph already accepted."""
    async with factory() as uow:
        await uow.graph_sync.mark(outcome)
        await uow.commit()
