"""Temporal adapter for the WorkflowGateway port."""

import logging

from temporalio.client import Client
from temporalio.exceptions import WorkflowAlreadyStartedError
from temporalio.service import RPCError, RPCStatusCode

from agentic_qa.infrastructure.workflows.temporal.contracts import (
    TASK_QUEUE,
    RunParams,
    workflow_id_for,
)

logger = logging.getLogger(__name__)


class TemporalWorkflowGateway:
    def __init__(self, client: Client, task_queue: str = TASK_QUEUE) -> None:
        self._client = client
        self._task_queue = task_queue

    async def start_run(self, run_id: str, project_id: str) -> None:
        try:
            await self._client.start_workflow(
                "AgentRunWorkflow",
                RunParams(run_id=run_id, project_id=project_id),
                id=workflow_id_for(run_id),
                task_queue=self._task_queue,
            )
        except WorkflowAlreadyStartedError:
            # The workflow id is derived from the run id, so a retried start after a
            # lost acknowledgement finds the same workflow. That is the desired
            # outcome, not an error.
            logger.info("workflow already running for run %s", run_id)

    async def request_pause(self, run_id: str) -> None:
        await self._signal(run_id, "pause")

    async def request_resume(self, run_id: str) -> None:
        await self._signal(run_id, "resume")

    async def request_cancel(self, run_id: str) -> None:
        await self._signal(run_id, "cancel")

    async def _signal(self, run_id: str, name: str) -> None:
        handle = self._client.get_workflow_handle(workflow_id_for(run_id))
        try:
            await handle.signal(name)
        except RPCError as error:
            if error.status is RPCStatusCode.NOT_FOUND:
                # Already finished (or never started): signalling a terminal run is a
                # no-op, which is what makes cancel naturally idempotent.
                logger.info("no live workflow for run %s; ignoring %s", run_id, name)
                return
            raise
