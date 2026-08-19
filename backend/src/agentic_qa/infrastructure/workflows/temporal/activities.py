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
from agentic_qa.domain.qa.test_plan import TestPlan
from agentic_qa.domain.qa.verification import derive_verdict
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
            # The plan version was pinned onto the run at creation, so this reads the
            # plan the run is judged by — not whichever version is current now.
            plan = (
                await uow.plans.get(run.plan_id, run.plan_version)
                if run.plan_id is not None and run.plan_version is not None
                else None
            )

            story = (
                await uow.stories.get(plan.source_story_id)
                if plan is not None and plan.source_story_id is not None
                else None
            )

        hints = (
            {
                criterion.criterion_id: criterion.verification_hint
                for criterion in story.acceptance_criteria
                if criterion.verification_hint
            }
            if story is not None
            else {}
        )

        result = await runner.run_episode(
            EpisodeRequest(
                run_id=params.run_id,
                goal=plan.objective if plan is not None else params.goal,
                episode_index=params.episode_index,
                policy=policy,
                assertions=plan.assertions if plan is not None else (),
                verification_hints=hints,
            )
        )
        activity.heartbeat(params.episode_index)

        await self._index_evidence(params.run_id, result)
        if result.safe_point and result.graph_checkpoint_id:
            await self._record_recovery_point(params, result)

        verdict = await self._record_results(params, plan, result)
        return EpisodeOutcome(more_work=result.more_work, verdict=verdict)

    async def _record_results(
        self, params: EpisodeParams, plan: TestPlan | None, result: EpisodeResult
    ) -> str | None:
        """Persist criterion results and derive the run's verdict from them.

        The verdict is derived here, from durable results, rather than in the workflow:
        the workflow must stay free of I/O, and a verdict computed from data it never
        saw could not be re-derived when someone questions the report.
        """
        if plan is None:
            return None

        async with self._container.unit_of_work() as uow:
            await uow.criterion_results.record(params.run_id, result.criterion_results)
            await uow.commit()

        return derive_verdict(
            result.criterion_results,
            expected=[step.criterion_id for step in plan.assertions if step.criterion_id],
        ).value

    async def _index_evidence(self, run_id: str, result: EpisodeResult) -> None:
        """Record the artifacts the episode captured.

        The bytes were already written by the repository while the browser was open;
        this is the durable index a failure bundle reads to answer "what does this run
        have, and does it all belong to one evidence set" (docs/11).
        """
        if not result.evidence:
            return
        async with self._container.unit_of_work() as uow:
            for ref in result.evidence:
                await uow.artifacts.record(ref)
            await uow.commit()
        logger.info("indexed %d artifact(s) for run %s", len(result.evidence), run_id)

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
                    browser=BrowserRecoveryData(
                        # Where the page actually ended up. Recovery rebuilds a
                        # browser and navigates here before verifying anything.
                        url=result.observed_url or "",
                        last_verified_action=None,
                    ),
                    created_at=datetime.now(UTC),
                )
            )
            await uow.commit()
