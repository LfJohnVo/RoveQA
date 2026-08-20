"""What `memory status` answers.

Written so that it still answers when the graph is down — that is the moment somebody
runs it. A status command that fails because the thing it monitors has failed tells
an operator nothing they did not already suspect.

The two numbers that matter are separate on purpose: how much durable knowledge exists,
and how much of it the projection is missing. Reporting only the second would make a
project with no knowledge look identical to one whose graph is perfectly in sync.
"""

from dataclasses import dataclass, field

from agentic_qa.application.ports.graph import GRAPH_SCHEMA_VERSION, GraphMemoryPort
from agentic_qa.application.ports.knowledge import GraphSyncState
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.domain.knowledge.experience import CandidateStatus


@dataclass(frozen=True)
class MemoryStatus:
    project_id: str
    environment_id: str
    graph_available: bool
    graph_schema_version: str
    durable_candidates: int
    actionable_candidates: int
    """What a planner could be offered right now, straight from PostgreSQL. This is
    the number that survives losing the graph entirely."""

    sync_pending: int
    sync_failed: int
    by_status: dict[str, int] = field(default_factory=dict)

    @property
    def graph_is_behind(self) -> bool:
        return self.sync_pending > 0 or self.sync_failed > 0


STATUS_SCAN_LIMIT = 1000


async def memory_status(
    uow: UnitOfWork,
    graph: GraphMemoryPort | None,
    *,
    project_id: str,
    environment_id: str,
) -> MemoryStatus:
    async with uow:
        candidates = await uow.knowledge.list_for_scope(
            project_id=project_id, environment_id=environment_id, limit=STATUS_SCAN_LIMIT
        )
        counts = await uow.graph_sync.count_by_state()

    by_status: dict[str, int] = {}
    for candidate in candidates:
        by_status[candidate.status.value] = by_status.get(candidate.status.value, 0) + 1

    return MemoryStatus(
        project_id=project_id,
        environment_id=environment_id,
        # `is_available` never raises, so an unreachable store reports as unavailable
        # rather than turning the whole status call into an error.
        graph_available=await graph.is_available() if graph is not None else False,
        graph_schema_version=GRAPH_SCHEMA_VERSION,
        durable_candidates=len(candidates),
        actionable_candidates=sum(1 for candidate in candidates if candidate.is_actionable),
        sync_pending=counts.get(GraphSyncState.PENDING, 0),
        sync_failed=counts.get(GraphSyncState.FAILED, 0),
        by_status={status.value: by_status.get(status.value, 0) for status in CandidateStatus},
    )
