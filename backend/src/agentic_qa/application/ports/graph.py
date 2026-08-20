"""The learned-memory graph projection.

Everything here is about a store that is allowed to be missing. FalkorDB holds a
projection of `knowledge_candidates`, rebuildable from PostgreSQL at any time, so the
port is shaped so that every operation has a sane answer when the graph is down: a
write is deferred, a search returns nothing, and the run carries on (ADR 0008).

Deliberately narrow. The graph is asked for *more candidates to consider*, never for
permission: scope filtering and promotion gates stay in PostgreSQL and in the domain,
so a compromised or stale projection cannot widen what a run is allowed to see.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from agentic_qa.domain.knowledge.experience import KnowledgeExperienceCandidate

GRAPH_SCHEMA_VERSION = "roveqa.graph.v1"
"""Shape of the projection. Changing it makes every node written under an older
version a rebuild target rather than a silent mismatch."""


class GraphUnavailableError(Exception):
    """The projection could not be reached or written.

    Typed so callers can tell it apart from a bug in what they asked for. This one is
    always recoverable by leaving the candidate pending and syncing later; nothing
    about a run's correctness depends on it.
    """


@dataclass(frozen=True)
class GraphHit:
    candidate_id: str
    score: float
    """How well the projection matched the query. Used to *widen* the pool that
    deterministic ranking then orders — never as the ranking itself, because a
    similarity score has no idea whether the knowledge is reliable or still valid."""


class GraphMemoryPort(Protocol):
    async def materialize(self, candidate: KnowledgeExperienceCandidate) -> str:
        """Write one candidate into the projection and return its node id.

        Idempotent by candidate id: syncing the same candidate twice updates one node
        rather than growing the graph, so a retried sync and a rebuild are both safe.

        Raises `GraphUnavailableError` when the store cannot be reached.
        """
        ...

    async def forget(self, candidate_id: str) -> None:
        """Remove one candidate from the projection.

        Used when knowledge is invalidated or rejected: leaving it in the graph would
        let traversal keep surfacing something the durable side has withdrawn.
        """
        ...

    async def search(
        self, query: str, *, project_id: str, environment_id: str, limit: int = 20
    ) -> list[GraphHit]:
        """Candidate ids the projection considers relevant, scoped before searching.

        Returns ids only. The caller re-reads the durable rows, so a projection that
        is stale or has been tampered with can at worst suggest the wrong *existing*
        candidates — it can never invent knowledge or change what one says.
        """
        ...

    async def clear(self, project_id: str) -> None:
        """Drop one project's projection, for a rebuild."""
        ...

    async def is_available(self) -> bool:
        """Whether the store answers. Never raises: this is what `memory status`
        reports, and a status command that fails when the thing it monitors is down is
        useless exactly when it is needed."""
        ...


class GraphIngestion(Protocol):
    """Bulk write used by rebuild, kept separate so a normal sync cannot accidentally
    clear a project."""

    async def materialize_many(
        self, candidates: Sequence[KnowledgeExperienceCandidate]
    ) -> dict[str, str]:
        """candidate_id -> node id, for those that made it. Partial success is normal
        and is what the sync state table exists to record."""
        ...
