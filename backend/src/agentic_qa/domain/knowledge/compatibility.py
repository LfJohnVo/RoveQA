"""Whether knowledge from an earlier run still applies to this one.

Retrieval ranks by relevance, but relevance is the *last* question. First comes
whether the situation the knowledge was learned in is the situation the run is in now,
and that is a hard yes/no/verify — not a score that a high semantic match can outvote.

`revalidate` is why two answers would not do. `compatible` and `incompatible` cannot
express the common case: the app moved to a new version, so the knowledge is probably
still right but nobody has checked. Collapsing that into `compatible` replays stale
playbooks blindly; collapsing it into `incompatible` throws away memory on every
deploy and leaves the system permanently cold. `revalidate` makes the third case
usable and safe: the agent may follow it only after verifying its preconditions.

`exact` separates knowledge learned in *this* situation from knowledge that merely
does not contradict it, which is the difference ranking needs — otherwise a vague
memory recorded with no context outranks a specific one purely on reliability.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from agentic_qa.domain.knowledge.experience import (
    CandidateStatus,
    KnowledgeExperienceCandidate,
)


class Compatibility(StrEnum):
    EXACT = "exact"
    """Learned in precisely this situation: every context the run knows was recorded
    on the candidate and matches. The strongest thing memory can say."""

    COMPATIBLE = "compatible"
    """Nothing mismatched, but the knowledge was recorded with less context than this
    run has. It applies; it was just not learned here specifically."""

    REVALIDATE = "revalidate"
    """Plausibly still true, unconfirmed in this context. Preconditions must be
    checked before acting; it is never followed blind."""

    INCOMPATIBLE = "incompatible"
    """A different situation, or knowledge that has been withdrawn. Not offered."""


@dataclass(frozen=True)
class MemoryScope:
    """The situation the current run is in.

    `None` means "not known in this run" rather than "no constraint" — the two are
    distinguished below, because not knowing whether the context matches is exactly
    the case that has to be verified rather than assumed.
    """

    project_id: str
    environment_id: str
    origin: str | None = None
    role: str | None = None
    app_version: str | None = None
    page_fingerprint: str | None = None
    policy_id: str | None = None


def compatibility_of(
    candidate: KnowledgeExperienceCandidate, scope: MemoryScope, *, now: datetime
) -> Compatibility:
    """Judge one candidate against one run's situation.

    Deliberately independent of how the candidate was fetched. A retrieval query
    filters scope in SQL so foreign memory never loads; this is the check that still
    holds when someone adds a second query, a graph traversal or a rebuild path — the
    places where a filter is easiest to forget.
    """
    if candidate.project_id != scope.project_id or candidate.environment_id != scope.environment_id:
        # Not "less relevant": knowledge about a different deployment entirely.
        return Compatibility.INCOMPATIBLE

    if candidate.status in {CandidateStatus.INVALIDATED, CandidateStatus.REJECTED}:
        return Compatibility.INCOMPATIBLE

    if candidate.validity.is_expired_at(now):
        return Compatibility.INCOMPATIBLE

    if _differs(candidate.validity.origin, scope.origin):
        # An origin is not a version of the app, it is a different app.
        return Compatibility.INCOMPATIBLE

    if _differs(candidate.validity.role, scope.role):
        # What an admin can do says nothing about what a guest can do, and acting on
        # the difference is how a run ends up blocked or, worse, escalated.
        return Compatibility.INCOMPATIBLE

    dimensions = (
        (candidate.validity.origin, scope.origin),
        (candidate.validity.role, scope.role),
        (candidate.validity.app_version, scope.app_version),
        (candidate.validity.page_fingerprint, scope.page_fingerprint),
        (candidate.validity.policy_id, scope.policy_id),
    )
    if any(_needs_check(recorded, current) for recorded, current in dimensions):
        return Compatibility.REVALIDATE
    if all(_confirmed(recorded, current) for recorded, current in dimensions):
        return Compatibility.EXACT
    # Nothing mismatched, but the candidate was recorded with less context than this
    # run has, so it was not learned in exactly this situation.
    return Compatibility.COMPATIBLE


def _differs(recorded: str | None, current: str | None) -> bool:
    """Both sides known and not equal — a positive mismatch, not a gap."""
    return recorded is not None and current is not None and recorded != current


def _confirmed(recorded: str | None, current: str | None) -> bool:
    """Both sides known and equal — the situation was actually checked, not assumed."""
    return recorded is not None and current is not None and recorded == current


def _needs_check(recorded: str | None, current: str | None) -> bool:
    """Version-like context: a mismatch is not disqualifying, but it is not free.

    A new app version or a changed page fingerprint usually leaves knowledge intact
    and sometimes silently invalidates it, which is precisely what `revalidate` is
    for. A candidate that recorded no version at all was never version-bound, so it
    imposes no check.
    """
    if recorded is None:
        return False
    return current is None or recorded != current
