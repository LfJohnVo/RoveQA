"""Recurring runs.

A schedule is durable state, and it has exactly one owner: Temporal. Copying it into
PostgreSQL as well would create two records that can disagree, and the one that fires
is the one in Temporal — so the copy would be the authoritative-looking wrong answer.
This is the same reasoning as ADR 0009 for run lifecycle, applied one level up.

What that buys is the Phase 12 gate for free rather than by effort: restarting the API,
the worker, or the whole compose stack cannot lose a schedule, because none of them
were holding it.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.domain.validation import require_identifier, require_text

MAX_NOTE_CHARS = 500


@dataclass(frozen=True)
class RunSchedule:
    """A recurring run, described the way the caller asked for it.

    Carries the plan version explicitly. A schedule pinned to a version keeps running
    the same regression until someone changes it; a schedule with `plan_version=None`
    resolves the latest at each firing, which is what a team wants for "run the current
    suite nightly". Both are legitimate, and the difference must be a choice rather
    than a default nobody noticed.
    """

    schedule_id: str
    project_id: str
    cron: str
    plan_id: str | None = None
    plan_version: str | None = None
    environment_id: str | None = None
    run_policy_id: str | None = None
    paused: bool = False
    note: str = ""
    next_run_at: datetime | None = None
    """Reported by the gateway, never set by a caller: it is Temporal's answer, and a
    value we computed ourselves could disagree with when the run actually fires."""

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "schedule_id", require_identifier(self.schedule_id, field="schedule_id")
        )
        object.__setattr__(
            self, "project_id", require_identifier(self.project_id, field="project_id")
        )
        object.__setattr__(self, "cron", require_text(self.cron, field="cron", max_length=200))
        if len(self.cron.split()) not in (5, 6):
            # Rejected here rather than at the first firing: a schedule that silently
            # never fires is indistinguishable from one that works until someone checks
            # weeks later why no regression ran.
            raise InvalidEntityError(f"cron must have 5 or 6 fields: {self.cron}")
        if len(self.note) > MAX_NOTE_CHARS:
            raise InvalidEntityError("note is too long")


class ScheduleGateway(Protocol):
    async def create(self, schedule: RunSchedule) -> RunSchedule:
        """Register a recurring run. Raises `AlreadyExistsError` on a taken id.

        The id is the caller's, not generated: creating the same schedule twice has to
        be recognisable as the same request, and an id we minted would make every retry
        a new nightly regression.
        """
        ...

    async def get(self, schedule_id: str) -> RunSchedule | None: ...

    async def list_for_project(self, project_id: str) -> list[RunSchedule]: ...

    async def set_paused(self, schedule_id: str, *, paused: bool) -> bool:
        """Pause or resume. False when there is no such schedule.

        Pausing rather than deleting is what a team does during a deploy freeze; a
        delete would lose the cron expression and whoever wrote it.
        """
        ...

    async def delete(self, schedule_id: str) -> bool: ...
