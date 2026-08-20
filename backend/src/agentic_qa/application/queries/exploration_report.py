"""What one exploration found, and what changed since the last one.

The comparison is made here rather than stored, because it is derived from two maps that
are themselves durable. Storing the delta would create a third record that can disagree
with both — and the first time somebody re-ran the comparison and got a different answer
than the stored one, neither would be trusted again.

The baseline is the project's *previous* exploration, not its last good one. A baseline
chosen by outcome would hide a regression that has been failing for two nights behind
the last night it passed.
"""

from dataclasses import dataclass

from agentic_qa.application.errors import NotFoundError
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.domain.exploration.comparison import MapDelta, StateMap, compare
from agentic_qa.domain.exploration.frontier import ExplorationReport


@dataclass(frozen=True)
class ExplorationOutcome:
    run_id: str
    project_id: str
    state_map: StateMap
    report: ExplorationReport
    baseline_run_id: str | None = None
    """Which run this was compared against. `None` for a project's first exploration,
    where every state is new and that is not a finding."""

    delta: MapDelta | None = None


async def exploration_outcome(uow: UnitOfWork, run_id: str) -> ExplorationOutcome:
    """Load one run's map and diff it against the previous exploration.

    Raises `NotFoundError` when the run did not explore. A planned run has no map, and
    answering with an empty one would say "this application offers nothing".
    """
    run = await uow.runs.get(run_id)
    if run is None:
        raise NotFoundError("run", run_id)

    state_map = await uow.state_maps.get(run_id)
    report = await uow.state_maps.report_for(run_id)
    if state_map is None or report is None:
        raise NotFoundError("exploration", run_id)

    baseline_run_id = await uow.state_maps.previous_run(run.project_id, before_run_id=run_id)
    baseline = await uow.state_maps.get(baseline_run_id) if baseline_run_id else None

    return ExplorationOutcome(
        run_id=run_id,
        project_id=run.project_id,
        state_map=state_map,
        report=report,
        baseline_run_id=baseline_run_id,
        # No baseline means no delta, rather than a delta where everything is new: the
        # first exploration of an application discovering the whole application is not
        # news, and reporting it as forty findings would teach a reader to skip them.
        delta=compare(baseline, state_map) if baseline is not None else None,
    )
