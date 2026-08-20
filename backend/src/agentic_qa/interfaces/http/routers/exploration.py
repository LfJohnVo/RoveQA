"""What an exploring run mapped, and what changed since the last one.

Read-only, and the delta is computed on read from two durable maps rather than stored.
A third record could disagree with both, and the first time somebody re-ran the
comparison and got a different answer than the stored one, neither would be trusted.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path

from agentic_qa.application.queries.exploration_report import (
    ExplorationOutcome,
    exploration_outcome,
)
from agentic_qa.bootstrap.container import Container
from agentic_qa.domain.exploration.state import PageState
from agentic_qa.interfaces.http.dependencies import get_container
from agentic_qa.interfaces.http.schemas import (
    ChangedStateResponse,
    ExplorationDeltaResponse,
    ExplorationResponse,
    ExploredStateResponse,
)

router = APIRouter(prefix="/api/v1/runs/{run_id}/exploration", tags=["exploration"])

ContainerDep = Annotated[Container, Depends(get_container)]
RunPath = Annotated[str, Path(min_length=1, max_length=200)]


@router.get("", response_model=ExplorationResponse)
async def read_exploration(container: ContainerDep, run_id: RunPath) -> ExplorationResponse:
    """404 when the run did not explore: a planned run has no map, and answering with
    an empty one would say the application offers nothing."""
    async with container.unit_of_work() as uow:
        outcome = await exploration_outcome(uow, run_id)
    return _response(outcome)


def _response(outcome: ExplorationOutcome) -> ExplorationResponse:
    report = outcome.report
    return ExplorationResponse(
        run_id=outcome.run_id,
        project_id=outcome.project_id,
        stop_reason=report.stop_reason.value,
        complete=report.complete,
        actions_taken=report.actions_taken,
        states_discovered=report.states_discovered,
        max_depth_reached=report.max_depth_reached,
        frontier_remaining=report.frontier_remaining,
        declined=report.declined,
        states=[_state(state) for state in outcome.state_map.states],
        delta=(
            ExplorationDeltaResponse(
                baseline_run_id=outcome.baseline_run_id or "",
                new=[_state(state) for state in outcome.delta.new],
                gone=[_state(state) for state in outcome.delta.gone],
                changed=[
                    ChangedStateResponse(
                        route=change.route,
                        gained=list(change.gained),
                        lost=list(change.lost),
                    )
                    for change in outcome.delta.changed
                ],
                unreachable_conclusions=outcome.delta.unreachable_conclusions,
            )
            if outcome.delta is not None
            else None
        ),
    )


def _state(state: PageState) -> ExploredStateResponse:
    return ExploredStateResponse(
        signature=state.signature,
        route=state.route,
        url=state.url,
        title=state.title,
        affordances=list(state.affordance_keys),
    )
