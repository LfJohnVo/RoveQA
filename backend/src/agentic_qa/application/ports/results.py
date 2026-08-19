"""Criterion result repository port.

Results are written once per run and read by reports. `record` is idempotent per
`(run_id, criterion_id)`: an activity that retried after a lost acknowledgement must not
leave two contradictory answers for the same criterion.
"""

from collections.abc import Sequence
from typing import Protocol

from agentic_qa.domain.qa.verification import CriterionResult


class CriterionResultRepository(Protocol):
    async def record(self, run_id: str, results: Sequence[CriterionResult]) -> None:
        """Store results for a run, replacing any previous answer for the same criteria."""
        ...

    async def list_for_run(self, run_id: str) -> list[CriterionResult]: ...
