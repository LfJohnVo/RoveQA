"""Worker entrypoint: hosts the workflow and its activities.

The worker is replaceable. Nothing about a run lives only in its memory — status and
progress are durable in PostgreSQL and Temporal, so killing it loses no run.

The agent runtime is wired here and only here. The API process never loads Playwright
or calls a model; it answers questions about runs. If no model endpoint is configured,
the worker still starts and the activity reports that no runtime is available, rather
than running a scripted pretence.
"""

import asyncio
import logging
from dataclasses import replace

from temporalio.client import Client
from temporalio.worker import Worker

from agentic_qa.bootstrap.container import build_container, with_agent_runtime
from agentic_qa.bootstrap.settings import Settings
from agentic_qa.infrastructure.workflows.temporal.activities import RunActivities
from agentic_qa.infrastructure.workflows.temporal.contracts import TASK_QUEUE
from agentic_qa.infrastructure.workflows.temporal.gateway import TemporalWorkflowGateway
from agentic_qa.infrastructure.workflows.temporal.schedules import TemporalScheduleGateway
from agentic_qa.infrastructure.workflows.temporal.workflows import (
    AgentRunWorkflow,
    ScheduledRunWorkflow,
)

logger = logging.getLogger(__name__)


def build_worker(client: Client, activities: RunActivities, task_queue: str = TASK_QUEUE) -> Worker:
    return Worker(
        client,
        task_queue=task_queue,
        workflows=[AgentRunWorkflow, ScheduledRunWorkflow],
        activities=[
            activities.transition_run_status,
            activities.run_episode,
            activities.consolidate_experience,
            activities.sync_knowledge_graph,
            activities.analyze_failures,
            activities.start_scheduled_run,
        ],
    )


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = Settings.from_env()
    client = await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)
    # The worker needs the workflow gateway too, not just the API: a schedule firing
    # creates a run *and starts its workflow*, both from an activity running here.
    # Built from the client the worker already has rather than a second connection.
    container = with_agent_runtime(
        replace(
            build_container(settings),
            workflows=TemporalWorkflowGateway(client, settings.temporal_task_queue),
            schedules=TemporalScheduleGateway(client, settings.temporal_task_queue),
        ),
        settings,
    )
    worker = build_worker(client, RunActivities(container), settings.temporal_task_queue)
    logger.info("worker listening on %s", settings.temporal_task_queue)
    try:
        await worker.run()
    finally:
        await container.aclose()


if __name__ == "__main__":
    asyncio.run(main())
