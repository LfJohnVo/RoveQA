"""Consolidate a finished run into durable knowledge.

Runs once per run, enforced by an idempotency record committed in the same
transaction as the knowledge itself (ADR 0010). A retried activity that consolidated
twice would record two supports from one run, and support is meant to count
*independent* runs that agreed — inflating it is exactly how one flaky observation
talks itself into being trusted.

Learning is never allowed to fail the run it learned from. The run is already over
and its verdict is already durable; a knowledge write that cannot happen is a missing
optimisation for later runs, not a QA result anyone should lose. Callers get the
outcome and decide, and the activity above logs it.
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from agentic_qa.application.commands.record_memory_feedback import register_feedback
from agentic_qa.application.commands.sync_knowledge_graph import enqueue_for_sync
from agentic_qa.application.errors import AlreadyExistsError, NotFoundError
from agentic_qa.application.ports.idempotency import (
    EXPERIENCE_CONSOLIDATION_SCOPE,
    IdempotencyRecord,
    request_fingerprint,
)
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.application.services.experience_consolidation import (
    DEFAULT_ENVIRONMENT,
    ConsolidationInput,
    consolidate,
)
from agentic_qa.domain.knowledge.experience import KnowledgeExperienceCandidate
from agentic_qa.domain.knowledge.feedback import FeedbackKind
from agentic_qa.domain.knowledge.reconciliation import contradicted_by
from agentic_qa.domain.qa.verification import CriterionResult

logger = logging.getLogger(__name__)

CONTRADICTION_SCAN_LIMIT = 500
"""How much stored knowledge one finished run compares itself against.

Bounded because consolidation runs after every run: an unbounded scan grows with the
project's history. Ordered reliability-first, so what is checked is what a later run
would most likely have acted on."""


@dataclass(frozen=True)
class ConsolidateExperienceCommand:
    run_id: str
    app_version: str | None = None
    page_fingerprint: str | None = None


@dataclass(frozen=True)
class ConsolidateExperienceResult:
    candidates: tuple[KnowledgeExperienceCandidate, ...]
    skipped: tuple[str, ...]
    replayed: bool
    """True when this run had already been consolidated and nothing was written."""

    contradicted: tuple[KnowledgeExperienceCandidate, ...] = ()
    """Stored knowledge this run disproved. Invalidated, never deleted: why something
    stopped being true is worth as much as the fact was."""


async def consolidate_experience(
    uow: UnitOfWork, command: ConsolidateExperienceCommand, *, now: datetime
) -> ConsolidateExperienceResult:
    async with uow:
        if await uow.idempotency.get(EXPERIENCE_CONSOLIDATION_SCOPE, command.run_id) is not None:
            return ConsolidateExperienceResult(candidates=(), skipped=(), replayed=True)

        run = await uow.runs.get(command.run_id)
        if run is None:
            raise NotFoundError("run", command.run_id)

        environment_id = run.environment_id or DEFAULT_ENVIRONMENT
        results = await uow.criterion_results.list_for_run(run.run_id)
        evidence = await uow.artifacts.list_for_run(run.run_id)
        recovery = await uow.recovery_points.latest_for_run(run.run_id)

        outcome = consolidate(
            ConsolidationInput(
                run=run,
                results=results,
                # Where the run actually ended up, taken from the last safe point
                # rather than from anything the model reported about itself.
                observed_url=recovery.browser.url if recovery is not None else None,
                evidence_set_id=evidence[0].evidence_set_id if evidence else None,
                page_fingerprint=command.page_fingerprint,
                app_version=command.app_version,
            ),
            now=now,
        )

        merged = [await uow.knowledge.merge(candidate) for candidate in outcome.candidates]
        for candidate in merged:
            await enqueue_for_sync(uow, candidate.candidate_id)
        contradicted = await _invalidate_what_this_run_disproved(
            uow,
            run_id=run.run_id,
            project_id=run.project_id,
            environment_id=environment_id,
            results=results,
            now=now,
        )

        try:
            await uow.idempotency.add(
                IdempotencyRecord(
                    scope=EXPERIENCE_CONSOLIDATION_SCOPE,
                    key=run.run_id,
                    request_fingerprint=request_fingerprint(
                        EXPERIENCE_CONSOLIDATION_SCOPE, {"run_id": run.run_id}
                    ),
                    resource_id=run.run_id,
                )
            )
        except AlreadyExistsError:
            # Two workers consolidated the same run at once. The loser rolls back, so
            # the winner's support stands alone — which is the correct count.
            return ConsolidateExperienceResult(candidates=(), skipped=(), replayed=True)

        await uow.commit()

    return ConsolidateExperienceResult(
        candidates=tuple(merged),
        skipped=outcome.skipped,
        replayed=False,
        contradicted=tuple(contradicted),
    )


async def _invalidate_what_this_run_disproved(
    uow: UnitOfWork,
    *,
    run_id: str,
    project_id: str,
    environment_id: str,
    results: Sequence[CriterionResult],
    now: datetime,
) -> list[KnowledgeExperienceCandidate]:
    """Withdraw memory this run's deterministic results disprove.

    The other half of learning. Without it memory only ever grows, and a fact that
    stopped being true keeps being offered to every run that follows — which is worse
    than having no memory, because the agent acts on it.

    Only contradictions are recorded here; agreement was already counted by merging
    the candidates this run produced. Doing both would let one run vote twice.
    """
    stored = await uow.knowledge.list_for_scope(
        # Every status, not just the actionable ones: a candidate that has not been
        # promoted yet can still be disproved, and letting it accumulate support it
        # no longer deserves is how it reaches a planner later.
        project_id=project_id,
        environment_id=environment_id,
        limit=CONTRADICTION_SCAN_LIMIT,
    )
    withdrawn: list[KnowledgeExperienceCandidate] = []
    for candidate in contradicted_by(stored, results=results):
        updated, recorded = await register_feedback(
            uow,
            candidate,
            run_id=run_id,
            kind=FeedbackKind.CONTRADICTION,
            now=now,
            detail="a deterministic check in this run disproved it",
        )
        if recorded:
            withdrawn.append(updated)
    return withdrawn
