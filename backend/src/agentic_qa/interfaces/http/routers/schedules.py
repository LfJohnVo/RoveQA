"""Recurring runs.

Thin by design: every operation is one call into the `ScheduleGateway`, because there
is no business rule about scheduling that the port and the domain type do not already
carry. Validating the cron here as well would be a second interpretation of a string
Temporal is the one that acts on.

No `Idempotency-Key`. The schedule id is the caller's and is the identity: creating the
same schedule twice is a 409, not a duplicate nightly regression, and a retried create
after a lost response finds its own schedule waiting.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi import status as http_status

from agentic_qa.application.errors import NotFoundError
from agentic_qa.application.ports.schedules import RunSchedule, ScheduleGateway
from agentic_qa.bootstrap.container import Container
from agentic_qa.interfaces.http.dependencies import get_container
from agentic_qa.interfaces.http.schemas import (
    CreateScheduleRequest,
    ScheduleListResponse,
    ScheduleResponse,
)

router = APIRouter(prefix="/api/v1/projects/{project_id}/schedules", tags=["schedules"])

ContainerDep = Annotated[Container, Depends(get_container)]
ProjectPath = Annotated[str, Path(min_length=1, max_length=200)]
SchedulePath = Annotated[str, Path(min_length=1, max_length=200)]


@router.post("", response_model=ScheduleResponse, status_code=http_status.HTTP_201_CREATED)
async def create_schedule(
    container: ContainerDep, project_id: ProjectPath, request: CreateScheduleRequest
) -> ScheduleResponse:
    schedules = _require_schedules(container)
    async with container.unit_of_work() as uow:
        if await uow.projects.get(project_id) is None:
            raise NotFoundError("project", project_id)

    # `InvalidEntityError` from the domain type and `AlreadyExistsError` from the
    # gateway both travel to the registered handlers, which render the one error
    # envelope the CLI already knows how to read. Catching them here would produce a
    # second error shape for the same conditions.
    created = await schedules.create(
        RunSchedule(
            schedule_id=request.schedule_id,
            project_id=project_id,
            cron=request.cron,
            plan_id=request.plan_id,
            plan_version=request.plan_version,
            environment_id=request.environment_id,
            run_policy_id=request.run_policy_id,
            paused=request.paused,
            note=request.note,
        )
    )
    return ScheduleResponse.from_domain(created)


@router.get("", response_model=ScheduleListResponse)
async def list_schedules(container: ContainerDep, project_id: ProjectPath) -> ScheduleListResponse:
    schedules = _require_schedules(container)
    found = await schedules.list_for_project(project_id)
    return ScheduleListResponse(
        project_id=project_id, schedules=[ScheduleResponse.from_domain(item) for item in found]
    )


@router.post("/{schedule_id}/pause", response_model=ScheduleResponse)
async def pause(
    container: ContainerDep, project_id: ProjectPath, schedule_id: SchedulePath
) -> ScheduleResponse:
    """Stop firing without forgetting the schedule.

    What a team does during a deploy freeze. Deleting instead would lose the cron
    expression and whoever wrote it, and "we'll recreate it after" is how a nightly
    regression stops running for a quarter.
    """
    return await _set_paused(container, project_id, schedule_id, paused=True)


@router.post("/{schedule_id}/resume", response_model=ScheduleResponse)
async def resume(
    container: ContainerDep, project_id: ProjectPath, schedule_id: SchedulePath
) -> ScheduleResponse:
    return await _set_paused(container, project_id, schedule_id, paused=False)


@router.delete("/{schedule_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    container: ContainerDep, project_id: ProjectPath, schedule_id: SchedulePath
) -> None:
    schedules = _require_schedules(container)
    await _owned(schedules, project_id, schedule_id)
    await schedules.delete(schedule_id)


async def _set_paused(
    container: Container, project_id: str, schedule_id: str, *, paused: bool
) -> ScheduleResponse:
    schedules = _require_schedules(container)
    await _owned(schedules, project_id, schedule_id)
    await schedules.set_paused(schedule_id, paused=paused)
    updated = await schedules.get(schedule_id)
    if updated is None:
        # Deleted between the ownership check and the update. Rare, and reported rather
        # than papered over with the stale copy we were holding.
        raise NotFoundError("schedule", schedule_id)
    return ScheduleResponse.from_domain(updated)


async def _owned(schedules: ScheduleGateway, project_id: str, schedule_id: str) -> RunSchedule:
    """Resolve a schedule *within this project*.

    Ids live in one namespace in Temporal, so without this check a caller could pause
    or delete another project's nightly regression by guessing its name.
    """
    schedule = await schedules.get(schedule_id)
    if schedule is None or schedule.project_id != project_id:
        raise NotFoundError("schedule", schedule_id)
    return schedule


def _require_schedules(container: Container) -> ScheduleGateway:
    if container.schedules is None:
        # Honest rather than a fake success: a 201 for a schedule nobody stored would
        # be believed until the night it did not run.
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="scheduling is unavailable: this process is not connected to Temporal",
        )
    return container.schedules
