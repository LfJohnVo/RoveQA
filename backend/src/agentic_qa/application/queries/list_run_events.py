"""Read the durable event log of a run.

This is the catch-up path a client uses after a dropped connection: it replays from
the cursor it already has, so realtime delivery can be lossy without losing truth.
"""

from agentic_qa.application.errors import NotFoundError
from agentic_qa.application.ports.events import (
    DEFAULT_EVENT_PAGE_SIZE,
    MAX_EVENT_PAGE_SIZE,
    RunEvent,
)
from agentic_qa.application.ports.unit_of_work import UnitOfWork


async def list_run_events(
    uow: UnitOfWork,
    run_id: str,
    *,
    after: int = 0,
    limit: int = DEFAULT_EVENT_PAGE_SIZE,
) -> list[RunEvent]:
    if await uow.runs.get(run_id) is None:
        raise NotFoundError("run", run_id)
    # Clamp rather than trust the caller: an unbounded read is a denial-of-service
    # waiting to happen (docs/11 bounded reads).
    bounded = max(1, min(limit, MAX_EVENT_PAGE_SIZE))
    return await uow.events.list_for_run(run_id, after=max(0, after), limit=bounded)
