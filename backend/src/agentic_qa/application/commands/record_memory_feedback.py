"""Record what a run discovered about the knowledge it used.

The write and the reliability update are one transaction. Split apart they can
disagree in both directions: an outcome recorded but never counted makes memory look
better than the evidence, and a count applied without its record makes a reliability
number nobody can audit or rebuild from (ADR 0010).

Ordering inside the transaction matters too. The occurrence row is written *first*,
and only an insert that actually happened is allowed to move the counters — that is
what makes a retried activity idempotent rather than a second vote.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from agentic_qa.application.commands.sync_knowledge_graph import enqueue_for_sync
from agentic_qa.application.errors import NotFoundError
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.domain.knowledge.experience import KnowledgeExperienceCandidate
from agentic_qa.domain.knowledge.feedback import FeedbackKind, MemoryFeedback, apply_feedback

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RecordMemoryFeedbackCommand:
    candidate_id: str
    run_id: str
    kind: FeedbackKind
    episode_id: str | None = None
    observed: bool = True
    """False when a model concluded this rather than a deterministic check. The row is
    still written — a model repeatedly doubting a fact is worth seeing — but it must
    not move the numbers a later run trusts."""

    detail: str | None = None


@dataclass(frozen=True)
class RecordMemoryFeedbackResult:
    candidate: KnowledgeExperienceCandidate
    recorded: bool
    """False when this occurrence was already known, so nothing was counted twice."""


async def register_feedback(
    uow: UnitOfWork,
    candidate: KnowledgeExperienceCandidate,
    *,
    run_id: str,
    kind: FeedbackKind,
    now: datetime,
    episode_id: str | None = None,
    observed: bool = True,
    detail: str | None = None,
) -> tuple[KnowledgeExperienceCandidate, bool]:
    """Record one outcome and re-derive the candidate, inside an already-open
    transaction.

    Shared by the command below and by consolidation, so both reach the same verdict
    about the same evidence and both get the same duplicate protection. Two copies of
    this would be two rules that can disagree about what a retry means.
    """
    feedback = MemoryFeedback(
        feedback_id=str(uuid4()),
        candidate_id=candidate.candidate_id,
        run_id=run_id,
        kind=kind,
        created_at=now,
        observed=observed,
        episode_id=episode_id,
        detail=detail,
    )

    if not await uow.memory_feedback.record(feedback):
        # Already counted. Changing nothing is the whole point: a lost acknowledgement
        # must not turn one run's outcome into two votes.
        return candidate, False

    updated = apply_feedback(candidate, feedback, now=now)
    await uow.knowledge.save(updated)
    # In the same transaction as the change, so the projection can never be told about
    # something the durable side then rolled back.
    await enqueue_for_sync(uow, updated.candidate_id)
    return updated, True


async def record_memory_feedback(
    uow: UnitOfWork, command: RecordMemoryFeedbackCommand, *, now: datetime
) -> RecordMemoryFeedbackResult:
    async with uow:
        candidate = await uow.knowledge.get(command.candidate_id)
        if candidate is None:
            raise NotFoundError("knowledge candidate", command.candidate_id)

        updated, recorded = await register_feedback(
            uow,
            candidate,
            run_id=command.run_id,
            kind=command.kind,
            now=now,
            episode_id=command.episode_id,
            observed=command.observed,
            detail=command.detail,
        )
        if not recorded:
            return RecordMemoryFeedbackResult(candidate=updated, recorded=False)
        await uow.commit()

    if updated.status is not candidate.status:
        logger.info(
            "knowledge %s moved %s -> %s after %s feedback from run %s",
            candidate.candidate_id,
            candidate.status,
            updated.status,
            command.kind,
            command.run_id,
        )
    return RecordMemoryFeedbackResult(candidate=updated, recorded=True)
