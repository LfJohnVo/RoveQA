"""In-memory doubles for the graph projection.

`InMemoryGraphMemory` is a working projection; `UnavailableGraph` is the outage. Both
exist because the interesting behaviour of this subsystem is what happens when it is
*not* working — a run must keep its correctness, the backlog must keep the work, and a
rebuild must restore the projection from PostgreSQL alone.
"""

from dataclasses import dataclass, field

from agentic_qa.application.ports.graph import GraphHit, GraphUnavailableError
from agentic_qa.domain.knowledge.experience import KnowledgeExperienceCandidate


@dataclass
class InMemoryGraphMemory:
    """A projection that behaves like the real one, including being wipeable."""

    nodes: dict[str, KnowledgeExperienceCandidate] = field(default_factory=dict)
    available: bool = True
    writes: int = 0
    """Every accepted materialize, including repeats — how a test proves that syncing
    twice updates one node instead of growing the graph."""

    async def materialize(self, candidate: KnowledgeExperienceCandidate) -> str:
        self._require_available()
        self.nodes[candidate.candidate_id] = candidate
        self.writes += 1
        return f"node:{candidate.candidate_id}"

    async def forget(self, candidate_id: str) -> None:
        self._require_available()
        self.nodes.pop(candidate_id, None)

    async def search(
        self, query: str, *, project_id: str, environment_id: str, limit: int = 20
    ) -> list[GraphHit]:
        self._require_available()
        # Substring matching stands in for hybrid search. What the tests care about is
        # that scope is applied before matching and that only ids come back.
        needle = query.lower()
        hits = [
            GraphHit(candidate_id=candidate_id, score=1.0)
            for candidate_id, candidate in self.nodes.items()
            if candidate.project_id == project_id
            and candidate.environment_id == environment_id
            and needle in str(candidate.payload.get("summary", "")).lower()
        ]
        return hits[:limit]

    async def clear(self, project_id: str) -> None:
        self._require_available()
        for candidate_id in [
            candidate_id
            for candidate_id, candidate in self.nodes.items()
            if candidate.project_id == project_id
        ]:
            del self.nodes[candidate_id]

    async def is_available(self) -> bool:
        return self.available

    def _require_available(self) -> None:
        if not self.available:
            raise GraphUnavailableError("graph store is down")


@dataclass
class UnavailableGraph:
    """A store that is never reachable. Used where the point is that nothing else
    breaks — not that some operations still work."""

    async def materialize(self, candidate: KnowledgeExperienceCandidate) -> str:
        raise GraphUnavailableError("graph store is down")

    async def forget(self, candidate_id: str) -> None:
        raise GraphUnavailableError("graph store is down")

    async def search(
        self, query: str, *, project_id: str, environment_id: str, limit: int = 20
    ) -> list[GraphHit]:
        raise GraphUnavailableError("graph store is down")

    async def clear(self, project_id: str) -> None:
        raise GraphUnavailableError("graph store is down")

    async def is_available(self) -> bool:
        # Never raises: this is what a status command calls, and it has to be able to
        # report "down" rather than fail because something is down.
        return False
