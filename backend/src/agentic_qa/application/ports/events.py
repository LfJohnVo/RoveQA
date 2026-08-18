"""Durable run event log.

This is the source of truth for what happened during a run. Redis Streams (added on
top of it) only make delivery fast: a client that reconnects rebuilds its baseline
from here, and a Redis flush cannot lose a confirmed event (docs/09, ADR 0003).

The envelope mirrors `contracts/run-event.schema.json` and docs/12.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

# Event types are part of the public contract (docs/12).
RUN_CREATED = "run.created"
RUN_STATUS_CHANGED = "run.status.changed"

MAX_EVENT_PAGE_SIZE = 500
DEFAULT_EVENT_PAGE_SIZE = 100


@dataclass(frozen=True)
class NewRunEvent:
    """An event to append. The log assigns its sequence."""

    run_id: str
    type: str
    payload: dict[str, Any] = field(default_factory=dict)
    request_id: str | None = None
    """Correlates the event with the API request that caused it, when there was one."""


@dataclass(frozen=True)
class RunEvent:
    event_id: str
    run_id: str
    sequence: int
    type: str
    occurred_at: datetime
    payload: dict[str, Any]
    request_id: str | None = None


class RunEventLog(Protocol):
    async def append(self, event: NewRunEvent) -> RunEvent:
        """Append durably, assigning the next per-run sequence.

        Called inside the same transaction as the change it describes, so a run can
        never change state without leaving its event behind (or the other way round).
        """
        ...

    async def list_for_run(self, run_id: str, *, after: int, limit: int) -> list[RunEvent]:
        """Events with sequence > after, ascending, capped at limit.

        `after` is the cursor a reconnecting client already has; the cap keeps reads
        bounded (docs/11).
        """
        ...
