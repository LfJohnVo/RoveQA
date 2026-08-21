"""Criterion result repository port.

Results are written once per run and read by reports. `record` is idempotent per
`(run_id, criterion_id)`: an activity that retried after a lost acknowledgement must not
leave two contradictory answers for the same criterion.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from agentic_qa.domain.qa.observations import ObservedFailure
from agentic_qa.domain.qa.verification import CriterionResult


@dataclass(frozen=True)
class RunCriterionResult:
    """A result together with the run it belongs to.

    `CriterionResult` deliberately does not carry a run id — it is one criterion's
    answer, and a run is the context it was answered in. Triage needs both, so the
    pairing is made explicit here rather than by widening the domain type.
    """

    run_id: str
    result: CriterionResult


class CriterionResultRepository(Protocol):
    async def record(self, run_id: str, results: Sequence[CriterionResult]) -> None:
        """Store results for a run, replacing any previous answer for the same criteria."""
        ...

    async def list_for_run(self, run_id: str) -> list[CriterionResult]: ...

    async def list_recent_failures(
        self, project_id: str, *, limit: int
    ) -> list[RunCriterionResult]:
        """Deterministic failures across a project's recent runs, newest run first.

        Only what triage can group: outcomes that were actually observed to fail.
        Model-derived judgements are excluded here rather than filtered later, because
        a query that returns them invites a caller that forgets to.

        Within a run the original order is preserved: cascade detection reads the first
        setup failure as the one everything after it may have inherited, and a reordered
        list would name the wrong cause.
        """
        ...


class ObservedFailureRepository(Protocol):
    """Where console errors and failed requests go to be readable.

    Separate from `CriterionResultRepository` because the grain is different and the
    meaning is different: a criterion result answers a question somebody asked, an
    observed failure is something nobody asked about and the browser saw anyway. Mixing
    them would need a nullable `criterion_id`, and a nullable key is how two kinds of row
    end up in one query that means neither.
    """

    async def record(self, run_id: str, failures: Sequence[ObservedFailure]) -> None:
        """Append this episode's observations to the run.

        Append rather than replace: an episode is a slice of a run, and a later one must
        not erase what an earlier one saw. Callers pass a whole episode's worth at once,
        so a retry of the same episode is the one case that can duplicate — which is
        cheap here, and cheaper than losing the first episode's findings.
        """
        ...

    async def list_for_run(self, run_id: str) -> list[ObservedFailure]: ...
