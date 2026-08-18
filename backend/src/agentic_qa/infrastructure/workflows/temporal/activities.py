"""Activities: the only place workflow code is allowed to touch the outside world.

Status is persisted from here, never as workflow-level state, so the durable row is
authoritative and the Temporal history stays bounded (ADR 0009).
"""

import logging
from datetime import UTC, datetime
from uuid import uuid4

from temporalio import activity

from agentic_qa.application.commands.transition_run import (
    TransitionRunCommand,
    transition_run,
)
from agentic_qa.application.errors import NotFoundError
from agentic_qa.application.ports.episodes import EpisodeRequest, EpisodeResult
from agentic_qa.application.services.policy_resolution import resolve_run_policy
from agentic_qa.bootstrap.container import Container
from agentic_qa.domain.runs.recovery import (
    BrowserRecoveryData,
    RecoveryPoint,
    RecoveryTrigger,
)
from agentic_qa.domain.runs.run import RunStatus, Verdict
from agentic_qa.infrastructure.workflows.temporal.contracts import (
    EpisodeOutcome,
    EpisodeParams,
    TransitionParams,
)

logger = logging.getLogger(__name__)

_TRIGGERS = {
    "navigation_stable": RecoveryTrigger.NAVIGATION_STABLE,
    "episode_closed": RecoveryTrigger.EPISODE_CLOSED,
}


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
                publisher=self._container.events,
            )

    @activity.defn(name="run_episode")
    async def run_episode(self, params: EpisodeParams) -> EpisodeOutcome:
        """Execute one episode of the agent loop.

        The activity stays thin: it resolves the run's policy, asks the episode runner
        to execute (which resumes from the checkpoint when there is one), and records
        the safe point durably. Deciding *when* a moment is safe belongs to the graph;
        writing it down belongs here, where the real checkpoint id exists.
        """
        activity.heartbeat(params.episode_index)

        runner = self._container.episodes
        if runner is None:
            # Honest rather than fake: nothing is configured to run an agent yet.
            logger.info("no agent runtime configured; run %s executes no episode", params.run_id)
            return EpisodeOutcome(more_work=False)

        async with self._container.unit_of_work() as uow:
            run = await uow.runs.get(params.run_id)
            if run is None:
                raise NotFoundError("run", params.run_id)
            policy = await resolve_run_policy(
                uow,
                project_id=run.project_id,
                environment_id=run.environment_id,
                requested_policy_id=run.run_policy_id,
            )

        result = await runner.run_episode(
            EpisodeRequest(
                run_id=params.run_id,
                goal=params.goal,
                episode_index=params.episode_index,
                policy=policy,
            )
        )
        activity.heartbeat(params.episode_index)

        if result.safe_point and result.graph_checkpoint_id:
            await self._record_recovery_point(params, result)

        return EpisodeOutcome(more_work=result.more_work)

    async def _record_recovery_point(self, params: EpisodeParams, result: EpisodeResult) -> None:
        async with self._container.unit_of_work() as uow:
            await uow.recovery_points.add(
                RecoveryPoint(
                    recovery_point_id=str(uuid4()),
                    run_id=params.run_id,
                    episode_index=params.episode_index,
                    trigger=_TRIGGERS.get(
                        result.safe_point or "", RecoveryTrigger.NAVIGATION_STABLE
                    ),
                    graph_checkpoint_id=result.graph_checkpoint_id or "",
                    browser=BrowserRecoveryData(url="", last_verified_action=None),
                    created_at=datetime.now(UTC),
                )
            )
            await uow.commit()
