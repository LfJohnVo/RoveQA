"""Activities: the only place workflow code is allowed to touch the outside world.

Status is persisted from here, never as workflow-level state, so the durable row is
authoritative and the Temporal history stays bounded (ADR 0009).
"""

import logging

from temporalio import activity

from agentic_qa.application.commands.transition_run import (
    TransitionRunCommand,
    transition_run,
)
from agentic_qa.bootstrap.container import Container
from agentic_qa.domain.runs.run import RunStatus, Verdict
from agentic_qa.infrastructure.workflows.temporal.contracts import (
    EpisodeOutcome,
    EpisodeParams,
    TransitionParams,
)

logger = logging.getLogger(__name__)


class RunActivities:
    """Activities bound to a container, so the worker owns the database wiring."""

    def __init__(self, container: Container) -> None:
        self._container = container

    @activity.defn(name="transition_run_status")
    async def transition_run_status(self, params: TransitionParams) -> None:
        async with self._container.unit_of_work() as uow:
            await transition_run(
                uow,
                TransitionRunCommand(
                    run_id=params.run_id,
                    target_status=RunStatus(params.target_status),
                    verdict=Verdict(params.verdict) if params.verdict else None,
                ),
            )

    @activity.defn(name="run_episode")
    async def run_episode(self, params: EpisodeParams) -> EpisodeOutcome:
        """Execute one episode of the agent loop.

        Phase 02 has no agent runtime yet, so there is no work to do and the loop ends
        immediately. Phase 05 fills this body with the LangGraph execution and
        heartbeats; the workflow above does not change when it does.
        """
        activity.heartbeat(params.episode_index)
        logger.info("no agent runtime yet; run %s has no episode to execute", params.run_id)
        return EpisodeOutcome(more_work=False)
