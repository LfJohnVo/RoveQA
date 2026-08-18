"""Recovery point repository port."""

from typing import Protocol

from agentic_qa.domain.runs.recovery import RecoveryPoint


class RecoveryPointRepository(Protocol):
    async def add(self, point: RecoveryPoint) -> None: ...

    async def latest_for_run(self, run_id: str) -> RecoveryPoint | None:
        """The newest safe point, which is where a resume validates against."""
        ...

    async def list_for_run(self, run_id: str, *, limit: int) -> list[RecoveryPoint]:
        """Newest first, bounded — a long run must not be read unboundedly."""
        ...
