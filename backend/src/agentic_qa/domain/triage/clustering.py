"""Grouping failures, and telling causes apart from consequences.

Two jobs, both done without a model:

**Clustering.** Failures that share their structural signals are one problem with many
witnesses. Reducing them to a cluster with a representative is what keeps a batch of
duplicates from becoming a batch of separate investigations — and, later, from becoming
a batch of expensive model calls that each rediscover the same thing.

**Cascade.** When a run's setup fails — the target was unreachable, the policy refused
the action that logs in — everything after it fails too. Counting those as independent
defects is how one broken environment turns into a report claiming twelve bugs. They
are marked `blocked_downstream` instead: still recorded, never counted.

A model may later propose *why* a cluster happened. It never decides *what* is in one:
the members and the evidence that justify a cluster stay deterministic and separate
from any interpretation of them (`plans/phase-11-airllm-deep-analysis.md`).
"""

import hashlib
import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum

from agentic_qa.domain.triage.signals import FailureSignal


class ClusterStatus(StrEnum):
    INDEPENDENT = "independent"
    """A problem in its own right. Worth investigating, and worth counting."""

    BLOCKED_DOWNSTREAM = "blocked_downstream"
    """It failed after something else in the same run had already broken.

    Recorded but never counted as a defect: an environment that went down does not
    produce one bug per criterion that came after it.
    """


@dataclass(frozen=True)
class FailureCluster:
    """One problem, and every failure that witnessed it."""

    cluster_id: str
    """Derived from the grouping key, so the same problem gets the same id across
    batches and two triage passes over the same failures agree."""

    representative: FailureSignal
    """The failure a human — or a model — should look at. One of the members, never a
    synthesised summary: an investigation has to start at something real."""

    members: tuple[FailureSignal, ...]
    status: ClusterStatus
    reason: str
    """Why these were grouped, in the terms that actually grouped them. A cluster that
    cannot say what it matched on is one nobody can disagree with."""

    blocked_by: str | None = None
    """The setup failure this one came after, when the status says so."""

    @property
    def run_ids(self) -> tuple[str, ...]:
        """Every run that hit this. Ordered and deduplicated so a report is stable."""
        seen: dict[str, None] = {}
        for member in self.members:
            seen.setdefault(member.run_id, None)
        return tuple(seen)

    @property
    def size(self) -> int:
        return len(self.members)

    @property
    def is_counted_as_defect(self) -> bool:
        return self.status is ClusterStatus.INDEPENDENT


@dataclass(frozen=True)
class TriageResult:
    clusters: tuple[FailureCluster, ...]
    """Ordered by size, largest first: the problem the most runs hit is the one worth
    looking at first."""

    @property
    def independent(self) -> tuple[FailureCluster, ...]:
        return tuple(cluster for cluster in self.clusters if cluster.is_counted_as_defect)

    @property
    def blocked(self) -> tuple[FailureCluster, ...]:
        return tuple(cluster for cluster in self.clusters if not cluster.is_counted_as_defect)

    @property
    def reduction(self) -> float:
        """How much smaller the investigation got. 0.0 when nothing was duplicated."""
        total = sum(cluster.size for cluster in self.clusters)
        if total == 0:
            return 0.0
        return round(1 - len(self.clusters) / total, 4)

    def representatives(self) -> tuple[FailureSignal, ...]:
        """What is worth sending to a model, if anything is.

        Only independent clusters: asking for a root cause of a failure that happened
        because the environment was down would spend a large model on an answer the
        deterministic pass already gave.
        """
        return tuple(cluster.representative for cluster in self.independent)


def triage(signals: Iterable[FailureSignal]) -> TriageResult:
    """Group failures and mark the ones that were only consequences.

    Deterministic and total: the same input always produces the same clusters, in the
    same order, with the same representatives. That is what lets this run with no model
    configured at all and still be worth reading.
    """
    ordered = list(signals)
    if not ordered:
        return TriageResult(clusters=())

    blockers = _setup_failure_per_run(ordered)

    grouped: dict[tuple[str, ...], list[FailureSignal]] = {}
    for signal in ordered:
        grouped.setdefault(signal.grouping_key, []).append(signal)

    clusters = [_build_cluster(key, members, blockers) for key, members in grouped.items()]
    # Biggest first, then by id so equal-sized clusters do not reorder between runs.
    clusters.sort(key=lambda cluster: (-cluster.size, cluster.cluster_id))
    return TriageResult(clusters=tuple(clusters))


def _setup_failure_per_run(signals: Sequence[FailureSignal]) -> dict[str, FailureSignal]:
    """The first setup failure in each run, if there was one.

    First rather than worst: within a run the ordering of results is the ordering they
    were checked in, so the earliest setup failure is the one everything after it may
    have inherited.
    """
    blockers: dict[str, FailureSignal] = {}
    for signal in signals:
        if signal.is_setup_failure and signal.run_id not in blockers:
            blockers[signal.run_id] = signal
    return blockers


def _build_cluster(
    key: tuple[str, ...],
    members: list[FailureSignal],
    blockers: dict[str, FailureSignal],
) -> FailureCluster:
    representative = members[0]
    blocker = blockers.get(representative.run_id)

    # Only downstream of a *different* failure. A setup failure is not blocked by
    # itself, and marking it so would hide the one thing worth fixing.
    downstream = (
        blocker is not None
        and not representative.is_setup_failure
        and all(blockers.get(member.run_id) is not None for member in members)
    )

    return FailureCluster(
        cluster_id=_cluster_id(key),
        representative=representative,
        members=tuple(members),
        status=ClusterStatus.BLOCKED_DOWNSTREAM if downstream else ClusterStatus.INDEPENDENT,
        reason=_reason(representative, len(members), downstream, blocker),
        blocked_by=blocker.criterion_id if downstream and blocker is not None else None,
    )


def _cluster_id(key: tuple[str, ...]) -> str:
    # JSON rather than a joined string: a separator that can appear inside a
    # component makes two different keys collide, and a cluster id that collides
    # silently merges two problems into one.
    digest = hashlib.sha256(json.dumps(key).encode("utf-8")).hexdigest()[:16]
    # The kind stays readable so a human scanning a list can tell clusters apart
    # without resolving hashes.
    return f"{key[0]}:{digest}"


def _reason(
    representative: FailureSignal,
    size: int,
    downstream: bool,
    blocker: FailureSignal | None,
) -> str:
    matched = [f"{representative.failure_kind} on {representative.criterion_id}"]
    if representative.http_status is not None:
        matched.append(f"HTTP {representative.http_status}")
    if representative.route is not None:
        matched.append(f"route {representative.route}")
    if representative.page_fingerprint is not None:
        matched.append(f"fingerprint {representative.page_fingerprint}")

    witnesses = "1 failure" if size == 1 else f"{size} failures"
    reason = f"{witnesses} matching {', '.join(matched)}"
    if downstream and blocker is not None:
        reason += f"; each run had already failed setup at {blocker.criterion_id}"
    return reason
