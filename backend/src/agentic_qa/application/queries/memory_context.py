"""Retrieve the memory a run should start from.

The pipeline docs/26 asks for, in order: hard scope filters, then candidate search,
then deterministic ranking, then a bounded context. The order is the safety property —
ranking never gets to promote something the filters would have excluded, because the
filters run in SQL before anything is scored.

Phase 09 slice 3 does the search against PostgreSQL only. The graph adds *more*
candidates to rank later; it never becomes the authority on which ones are allowed,
so adding it cannot widen what a run is permitted to see (ADR 0008).

Failure here is not a run failure. A run that cannot read memory is a cold run, and a
cold run is exactly what the system did before any of this existed.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.domain.knowledge.compatibility import MemoryScope
from agentic_qa.domain.knowledge.experience import CandidateStatus
from agentic_qa.domain.knowledge.memory_context import (
    DEFAULT_CONTEXT_ITEMS,
    MemoryContext,
    select,
)

logger = logging.getLogger(__name__)

CANDIDATE_POOL = 200
"""How many stored candidates are ranked before the context is cut to size.

Bounded because retrieval sits in front of every run: an unbounded read grows with
the project's history and would make the warm path slower than the cold one it is
supposed to beat. The pool is read reliability-first, so raising it adds progressively
weaker candidates rather than better ones.
"""


@dataclass(frozen=True)
class MemoryContextRequest:
    scope: MemoryScope
    limit: int = DEFAULT_CONTEXT_ITEMS
    query_id: str | None = None


async def retrieve_memory_context(
    uow: UnitOfWork, request: MemoryContextRequest, *, now: datetime
) -> MemoryContext:
    scope = request.scope
    query_id = request.query_id or str(uuid4())

    async with uow:
        # Hard filters, in the query: project, environment, and a status a planner is
        # allowed to act on. Nothing else can be loaded, so nothing else can leak.
        candidates = await uow.knowledge.list_for_scope(
            project_id=scope.project_id,
            environment_id=scope.environment_id,
            statuses=[CandidateStatus.PROMOTED, CandidateStatus.TRUSTED],
            limit=CANDIDATE_POOL,
        )

    context = select(candidates, scope=scope, query_id=query_id, now=now, limit=request.limit)
    logger.info(
        "memory context %s: %d of %d candidate(s) for %s/%s",
        query_id,
        len(context.items),
        len(candidates),
        scope.project_id,
        scope.environment_id,
    )
    return context
