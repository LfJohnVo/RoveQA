"""Durable state maps.

An exploration's value is comparative. One map says what an application offers; two
maps say what changed, and only the second is worth waking somebody for. So a map is
stored per run rather than merged into one accumulating picture: a single table could
say what exists and never what appeared.

The report is stored beside the map and never folded into it. A map of twelve states
that ran out of actions and a map of twelve states that ran out of places to go look
identical, and only the second can support the claim that a state missing next time was
removed.
"""

from typing import Protocol

from agentic_qa.domain.exploration.comparison import StateMap
from agentic_qa.domain.exploration.frontier import ExplorationReport


class StateMapRepository(Protocol):
    async def record(
        self, run_id: str, project_id: str, state_map: StateMap, report: ExplorationReport
    ) -> None:
        """Store one exploration's map and what it spent.

        Idempotent per `(run_id, signature)`: an activity that retried after a lost
        acknowledgement must not double the states it found, and the second attempt
        found the same application.
        """
        ...

    async def get(self, run_id: str) -> StateMap | None:
        """The map one run produced, or None when that run did not explore."""
        ...

    async def report_for(self, run_id: str) -> ExplorationReport | None: ...

    async def previous_run(self, project_id: str, *, before_run_id: str) -> str | None:
        """The run whose map this one should be compared against.

        The most recent earlier exploration of the same project. Deliberately not "the
        last known good": a baseline chosen by outcome would hide a regression that has
        been failing for two nights behind the last night it passed.
        """
        ...
