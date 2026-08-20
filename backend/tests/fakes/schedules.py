"""In-memory schedule gateway.

Mirrors the two behaviours the endpoints depend on: an id is unique, and every lookup
is by id alone — so a test that forgets to scope by project fails here the same way it
would fail against Temporal, where all schedules share one namespace.
"""

from dataclasses import replace

from agentic_qa.application.errors import AlreadyExistsError
from agentic_qa.application.ports.schedules import RunSchedule


class InMemoryScheduleGateway:
    def __init__(self, schedules: list[RunSchedule] | None = None) -> None:
        self._schedules: dict[str, RunSchedule] = {
            schedule.schedule_id: schedule for schedule in (schedules or [])
        }

    async def create(self, schedule: RunSchedule) -> RunSchedule:
        if schedule.schedule_id in self._schedules:
            raise AlreadyExistsError("schedule", schedule.schedule_id)
        self._schedules[schedule.schedule_id] = schedule
        return schedule

    async def get(self, schedule_id: str) -> RunSchedule | None:
        return self._schedules.get(schedule_id)

    async def list_for_project(self, project_id: str) -> list[RunSchedule]:
        return sorted(
            (item for item in self._schedules.values() if item.project_id == project_id),
            key=lambda item: item.schedule_id,
        )

    async def set_paused(self, schedule_id: str, *, paused: bool) -> bool:
        schedule = self._schedules.get(schedule_id)
        if schedule is None:
            return False
        self._schedules[schedule_id] = replace(schedule, paused=paused)
        return True

    async def delete(self, schedule_id: str) -> bool:
        return self._schedules.pop(schedule_id, None) is not None
