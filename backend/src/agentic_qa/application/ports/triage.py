"""Durable storage for failure triage (Phase 11).

Clusters outlive the run that produced them. "Twenty runs hit this wall" is a statement
about a project's history, and a grouping recomputed from scratch every time could not
say when a problem first appeared or that it is the same one as last week.

`record` takes deterministic clusters and `record_hypothesis` takes interpretations,
and they are separate calls on purpose: there is no operation that writes a model's
guess and a cluster's membership at the same time, so no bug can make one overwrite the
other.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from agentic_qa.application.ports.deep_analysis import ClusterHypothesis
from agentic_qa.domain.triage.clustering import FailureCluster


@dataclass(frozen=True)
class ClusterMember:
    """A pointer into `criterion_results`, not a copy of it.

    The observation, the evidence refs and whether the result was model-derived already
    live there under this same pair. Copying them here would create a second version of
    the truth, free to drift from the first.
    """

    run_id: str
    criterion_id: str


@dataclass(frozen=True)
class StoredCluster:
    """A cluster as it comes back out, with whatever was ever guessed about it."""

    cluster_id: str
    project_id: str
    failure_kind: str
    criterion_id: str
    status: str
    reason: str
    observation: str
    representative_run_id: str
    first_seen_at: datetime
    last_seen_at: datetime
    members: tuple[ClusterMember, ...] = field(default=())
    http_status: str | None = None
    route: str | None = None
    blocked_by: str | None = None
    hypothesis: ClusterHypothesis | None = None
    """The most recent one, or none. A cluster with no hypothesis is complete; it is
    simply one nobody asked a large model about."""

    @property
    def size(self) -> int:
        return len(self.members)

    @property
    def run_ids(self) -> tuple[str, ...]:
        seen: dict[str, None] = {}
        for member in self.members:
            seen.setdefault(member.run_id, None)
        return tuple(seen)


class FailureClusterRepository(Protocol):
    async def record(
        self, project_id: str, clusters: Sequence[FailureCluster], *, now: datetime
    ) -> None:
        """Upsert clusters and accumulate their members.

        Idempotent by `(project_id, cluster_id)` and by member pair: an analysis pass
        that ran twice leaves the same rows, which is what lets the activity be retried.
        """
        ...

    async def record_hypothesis(
        self,
        project_id: str,
        cluster_id: str,
        *,
        analyzed_run_id: str,
        hypothesis: ClusterHypothesis,
    ) -> bool:
        """Attach an interpretation to a cluster. False when this pass already did.

        Cannot create a cluster: a hypothesis about something with no recorded evidence
        is exactly what must never enter the store.
        """
        ...

    async def list_for_project(self, project_id: str, *, limit: int) -> list[StoredCluster]: ...
