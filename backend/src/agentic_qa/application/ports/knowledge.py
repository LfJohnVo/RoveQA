"""Knowledge repository port.

PostgreSQL owns these rows; the graph is a projection rebuilt from them (ADR 0008).
The port therefore has no notion of a graph at all — an adapter that lost FalkorDB
entirely must still answer everything here.

`merge` rather than `add`: the same fact observed by a second run is not a second
candidate, it is more support for the first. Storing both would make "how many runs
agree" unanswerable, which is exactly the number promotion depends on.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from agentic_qa.domain.knowledge.experience import (
    CandidateStatus,
    KnowledgeExperienceCandidate,
)
from agentic_qa.domain.knowledge.feedback import MemoryFeedback


class KnowledgeRepository(Protocol):
    async def merge(self, candidate: KnowledgeExperienceCandidate) -> KnowledgeExperienceCandidate:
        """Store a candidate, folding it into an equivalent one when it already exists.

        Returns what is now stored, so the caller sees the accumulated support rather
        than what it happened to submit.
        """
        ...

    async def get(self, candidate_id: str) -> KnowledgeExperienceCandidate | None: ...

    async def list_for_scope(
        self,
        *,
        project_id: str,
        environment_id: str,
        statuses: Sequence[CandidateStatus] | None = None,
        limit: int = 100,
    ) -> list[KnowledgeExperienceCandidate]:
        """Candidates for one project and environment, newest first.

        Scope is a parameter, never a filter applied afterwards: a query that could
        return another project's memory and then removes it is one missed line away
        from leaking it.
        """
        ...

    async def save(self, candidate: KnowledgeExperienceCandidate) -> None:
        """Persist a status or quality change on an existing candidate."""
        ...


class MemoryFeedbackRepository(Protocol):
    async def record(self, feedback: MemoryFeedback) -> bool:
        """Store one outcome. Returns False when this occurrence was already recorded.

        Idempotent rather than failing: the caller is usually a retried activity, and
        the honest answer to "record this again" is "already have it", not an error.
        Reliability counts independent outcomes, so a retry must not add one.
        """
        ...

    async def list_for_candidate(
        self, candidate_id: str, *, limit: int = 100
    ) -> list[MemoryFeedback]:
        """The evidence trail behind a candidate's current reliability, newest first."""
        ...


class GraphSyncState(StrEnum):
    PENDING = "pending"
    SYNCED = "synced"
    FAILED = "failed"


@dataclass(frozen=True)
class GraphSyncRecord:
    """Whether one durable candidate has reached the graph projection.

    Deliberately not part of the candidate: an outage must not be able to change what
    the system believes, only what the graph currently holds (ADR 0008).
    """

    candidate_id: str
    state: GraphSyncState = GraphSyncState.PENDING
    graph_schema_version: str | None = None
    graph_node_id: str | None = None
    attempts: int = 0
    last_error: str | None = None
    synced_at: datetime | None = None


class GraphSyncStateRepository(Protocol):
    async def mark(self, record: GraphSyncRecord) -> None:
        """Upsert the sync state of one candidate."""
        ...

    async def get(self, candidate_id: str) -> GraphSyncRecord | None: ...

    async def list_pending(self, *, limit: int = 500) -> list[GraphSyncRecord]:
        """The rebuild backlog: what the graph is missing, oldest first.

        This is what makes losing FalkorDB survivable — the projection is rebuilt from
        PostgreSQL rather than by re-running anybody's tests.
        """
        ...

    async def count_by_state(self) -> dict[GraphSyncState, int]:
        """What `memory status` reports. A growing pending count is the signal that
        the graph has been down or is falling behind."""
        ...
