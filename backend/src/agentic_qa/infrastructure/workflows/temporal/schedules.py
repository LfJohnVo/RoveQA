"""Temporal adapter for the ScheduleGateway port.

Temporal is the only store for schedules. There is no shadow copy in PostgreSQL,
because the copy could disagree with the thing that actually fires and would then be
the authoritative-looking wrong answer. That single ownership is also what makes the
Phase 12 gate hold without any effort on our side: the schedule outlives the API, the
worker and the whole compose stack, because none of them were holding it.

Cron expressions are passed through rather than parsed here. Temporal owns the
semantics of the string it will act on, and a second interpretation on our side would
eventually disagree with the first about a Sunday somewhere.
"""

import logging
from datetime import timedelta

from temporalio.api.common.v1 import Payload
from temporalio.client import (
    Client,
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleAlreadyRunningError,
    ScheduleOverlapPolicy,
    SchedulePolicy,
    ScheduleSpec,
    ScheduleState,
    ScheduleUpdate,
    ScheduleUpdateInput,
)
from temporalio.service import RPCError, RPCStatusCode

from agentic_qa.application.errors import AlreadyExistsError
from agentic_qa.application.ports.schedules import RunSchedule
from agentic_qa.infrastructure.workflows.temporal.contracts import (
    TASK_QUEUE,
    ScheduledRunParams,
    schedule_id_for,
    workflow_id_for,
)

logger = logging.getLogger(__name__)

UNKNOWN_CRON = "* * * * *"
"""Fallback for a schedule this system did not create and whose spec carries no cron.

The domain type requires one, and a schedule managed elsewhere is still worth listing;
what is not worth doing is reconstructing a plausible expression from a calendar spec
and presenting the guess as the schedule."""

FIRING_EXECUTION_TIMEOUT = timedelta(minutes=5)
"""How long one firing may take to *create* its run — not how long the run may take.

The run has its own timeouts and its own workflow; this bounds only the step that turns
"it is 2am" into a run id, so a wedged firing cannot sit in Temporal forever.
"""


class TemporalScheduleGateway:
    def __init__(self, client: Client, task_queue: str = TASK_QUEUE) -> None:
        self._client = client
        self._task_queue = task_queue

    async def create(self, schedule: RunSchedule) -> RunSchedule:
        action = ScheduleActionStartWorkflow(
            "ScheduledRunWorkflow",
            ScheduledRunParams(
                schedule_id=schedule.schedule_id,
                project_id=schedule.project_id,
                cron=schedule.cron,
                plan_id=schedule.plan_id,
                plan_version=schedule.plan_version,
                environment_id=schedule.environment_id,
                run_policy_id=schedule.run_policy_id,
            ),
            id=workflow_id_for(f"scheduled-{schedule.schedule_id}"),
            task_queue=self._task_queue,
            execution_timeout=FIRING_EXECUTION_TIMEOUT,
        )
        try:
            handle = await self._client.create_schedule(
                schedule_id_for(schedule.schedule_id),
                Schedule(
                    action=action,
                    spec=ScheduleSpec(cron_expressions=[schedule.cron]),
                    state=ScheduleState(paused=schedule.paused, note=schedule.note),
                    # SKIP: if the previous firing has not finished creating its run,
                    # a second one would race for the same idempotency scope. Queueing
                    # them would also mean a stalled firing quietly builds a backlog of
                    # regressions that all start at once when it clears.
                    policy=SchedulePolicy(overlap=ScheduleOverlapPolicy.SKIP),
                ),
            )
        except ScheduleAlreadyRunningError as error:
            raise AlreadyExistsError("schedule", schedule.schedule_id) from error

        described = await handle.describe()
        return await self._to_domain(schedule.schedule_id, described.schedule)

    async def get(self, schedule_id: str) -> RunSchedule | None:
        handle = self._client.get_schedule_handle(schedule_id_for(schedule_id))
        try:
            described = await handle.describe()
        except RPCError as error:
            if error.status is RPCStatusCode.NOT_FOUND:
                return None
            raise
        return await self._to_domain(schedule_id, described.schedule)

    async def list_for_project(self, project_id: str) -> list[RunSchedule]:
        """Listed from Temporal and filtered here.

        Temporal's list is eventually consistent — a schedule created a moment ago may
        not appear yet — which is why `create` returns the schedule it made rather than
        telling the caller to go and list.
        """
        found: list[RunSchedule] = []
        async for listing in await self._client.list_schedules():
            schedule_id = _strip_prefix(listing.id)
            described = await self.get(schedule_id)
            if described is not None and described.project_id == project_id:
                found.append(described)
        return sorted(found, key=lambda item: item.schedule_id)

    async def set_paused(self, schedule_id: str, *, paused: bool) -> bool:
        handle = self._client.get_schedule_handle(schedule_id_for(schedule_id))

        async def apply(update: ScheduleUpdateInput) -> ScheduleUpdate:
            update.description.schedule.state.paused = paused
            return ScheduleUpdate(schedule=update.description.schedule)

        try:
            await handle.update(apply)
        except RPCError as error:
            if error.status is RPCStatusCode.NOT_FOUND:
                return False
            raise
        return True

    async def delete(self, schedule_id: str) -> bool:
        handle = self._client.get_schedule_handle(schedule_id_for(schedule_id))
        try:
            await handle.delete()
        except RPCError as error:
            if error.status is RPCStatusCode.NOT_FOUND:
                # Deleting something that is not there is the outcome the caller wanted.
                return False
            raise
        return True

    async def _to_domain(self, schedule_id: str, schedule: Schedule) -> RunSchedule:
        """Rebuild the domain shape from what Temporal stored.

        The action's argument is the source of truth for *what* the schedule runs: it
        is the payload Temporal will hand to the workflow, so reading anything else
        would let the description drift from the behaviour.
        """
        params = await self._action_params(schedule)
        return RunSchedule(
            schedule_id=schedule_id,
            project_id=params.project_id,
            # From our payload, not from `spec`: Temporal rewrites a cron string into a
            # structured calendar, so the spec no longer contains the text that was
            # submitted. A schedule created outside this system has no payload cron and
            # falls back to whatever spec Temporal does report.
            cron=params.cron or _spec_cron(schedule),
            plan_id=params.plan_id,
            plan_version=params.plan_version,
            environment_id=params.environment_id,
            run_policy_id=params.run_policy_id,
            paused=schedule.state.paused,
            note=schedule.state.note or "",
            # `next_run_at` is left unset. Temporal reports next action times, but
            # showing a time we neither computed nor can re-derive invites a UI that
            # keeps displaying a "next run" after somebody paused the schedule.
        )

    async def _action_params(self, schedule: Schedule) -> ScheduledRunParams:
        """Decode the stored argument back into its dataclass.

        `describe()` hands back the raw payloads it received, not the objects that were
        encoded — so this goes through the client's own data converter rather than
        parsing the JSON by hand. Decoding with the same converter that encoded is what
        keeps a change to the payload format from silently producing a schedule
        description that no longer matches what will run.
        """
        action = schedule.action
        if not isinstance(action, ScheduleActionStartWorkflow):
            raise ValueError("schedule does not start a workflow")
        if not action.args:
            raise ValueError("schedule carries no run parameters")

        argument = action.args[0]
        if isinstance(argument, ScheduledRunParams):
            # Freshly built on this side and never round-tripped through the server.
            return argument
        if not isinstance(argument, Payload):
            raise ValueError(f"unexpected schedule argument: {type(argument).__name__}")

        decoded = await self._client.data_converter.decode(
            [argument], type_hints=[ScheduledRunParams]
        )
        params = decoded[0]
        if not isinstance(params, ScheduledRunParams):
            raise ValueError("schedule argument did not decode into run parameters")
        return params


def _spec_cron(schedule: Schedule) -> str:
    expressions = schedule.spec.cron_expressions
    return expressions[0] if expressions else UNKNOWN_CRON


def _strip_prefix(temporal_id: str) -> str:
    prefix = schedule_id_for("")
    return temporal_id[len(prefix) :] if temporal_id.startswith(prefix) else temporal_id
