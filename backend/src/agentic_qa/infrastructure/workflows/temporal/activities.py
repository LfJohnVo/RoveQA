"""Activities: the only place workflow code is allowed to touch the outside world.

Status is persisted from here, never as workflow-level state, so the durable row is
authoritative and the Temporal history stays bounded (ADR 0009).
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime
from uuid import uuid4

from temporalio import activity

from agentic_qa.application.commands.analyze_failures import (
    AnalyzeFailuresCommand,
    analyze_failures,
)
from agentic_qa.application.commands.consolidate_experience import (
    ConsolidateExperienceCommand,
    consolidate_experience,
)
from agentic_qa.application.commands.start_run import StartRunCommand, start_run
from agentic_qa.application.commands.sync_knowledge_graph import sync_pending
from agentic_qa.application.commands.transition_run import (
    TransitionRunCommand,
    transition_run,
)
from agentic_qa.application.errors import NotFoundError
from agentic_qa.application.ports.episodes import EpisodeRequest, EpisodeResult
from agentic_qa.application.queries.memory_context import (
    MemoryContextRequest,
    retrieve_memory_context,
)
from agentic_qa.application.services.experience_consolidation import DEFAULT_ENVIRONMENT
from agentic_qa.application.services.policy_resolution import resolve_run_policy
from agentic_qa.bootstrap.container import Container
from agentic_qa.domain.exploration.frontier import ExplorationBudget
from agentic_qa.domain.knowledge.compatibility import MemoryScope
from agentic_qa.domain.knowledge.memory_context import MemoryContext, MemoryItem
from agentic_qa.domain.projects.run_policy import RunPolicy
from agentic_qa.domain.qa.test_plan import TestPlan
from agentic_qa.domain.qa.verification import derive_verdict
from agentic_qa.domain.runs.recovery import (
    BrowserRecoveryData,
    RecoveryPoint,
    RecoveryTrigger,
)
from agentic_qa.domain.runs.run import Run, RunStatus, Verdict
from agentic_qa.infrastructure.knowledge.metrics import MemoryMetrics
from agentic_qa.infrastructure.workflows.temporal.contracts import (
    AnalyzeFailuresParams,
    ConsolidateParams,
    EpisodeOutcome,
    EpisodeParams,
    StartScheduledRunParams,
    SyncGraphParams,
    TransitionParams,
)

logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL_SECONDS = 30.0

DEFAULT_MAX_EXPLORED_STATES = 40

_TRIGGERS = {
    "navigation_stable": RecoveryTrigger.NAVIGATION_STABLE,
    "episode_closed": RecoveryTrigger.EPISODE_CLOSED,
}


class RunActivities:
    """Activities bound to a container, so the worker owns the database wiring."""

    def __init__(self, container: Container) -> None:
        self._container = container
        self.memory_metrics = MemoryMetrics()
        self.max_explored_states = DEFAULT_MAX_EXPLORED_STATES
        """How many distinct states one exploring episode may map.

        Public so an operator (and a test) can lower it without a redeploy. The other
        limits come from the RunPolicy, which is where limits belong; this one has no
        policy field yet because nothing has needed one."""

        """Per-worker counters. Public so an operator (and a test) can read what memory
        actually did, rather than inferring it from run outcomes that look identical
        whether memory helped or not."""

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

        memory = await self._recall(run, policy)

        # Exploring is asked for, never inferred. The budget comes from the run's own
        # policy: exploration is a way of spending a run's allowance, not a second
        # allowance beside it.
        exploration = (
            ExplorationBudget.under(policy, max_states=self.max_explored_states)
            if params.explore
            else None
        )

        result = await runner.run_episode(
            EpisodeRequest(
                run_id=params.run_id,
                goal=plan.objective if plan is not None else params.goal,
                episode_index=params.episode_index,
                policy=policy,
                assertions=plan.assertions if plan is not None else (),
                verification_hints=hints,
                memory=memory,
                exploration=exploration,
            )
        )
        activity.heartbeat(params.episode_index)

        await self._index_evidence(params.run_id, result)
        await self._record_state_map(params.run_id, run.project_id, result)
        if result.safe_point and result.graph_checkpoint_id:
            await self._record_recovery_point(params, result)

        verdict = await self._record_results(params, plan, result)
        return EpisodeOutcome(more_work=result.more_work, verdict=verdict)

    async def _record_state_map(self, run_id: str, project_id: str, result: EpisodeResult) -> None:
        """Store what an exploration mapped, or nothing for a planned episode.

        Not swallowed. Unlike memory or a screenshot, the map *is* the output of an
        exploring run — a run that crawled an application and stored nothing produced
        nothing, and reporting success for it would be reporting a run that did not
        happen. Recording is idempotent per run, so a Temporal retry is safe.
        """
        if result.state_map is None or result.exploration_report is None:
            return
        async with self._container.unit_of_work() as uow:
            await uow.state_maps.record(
                run_id, project_id, result.state_map, result.exploration_report
            )
            await uow.commit()
        logger.info(
            "run %s mapped %d state(s) and stopped: %s",
            run_id,
            result.exploration_report.states_discovered,
            result.exploration_report.stop_reason.value,
        )

    async def _recall(self, run: Run, policy: RunPolicy) -> tuple[MemoryItem, ...]:
        """What earlier runs learned about this application, or nothing.

        Failure is swallowed. A run that cannot read memory is a cold run, and a cold
        run is exactly what this system did before any of this existed — refusing to
        test an application because its memory is unavailable would trade a working
        QA run for an optimisation.
        """
        scope = MemoryScope(
            project_id=run.project_id,
            environment_id=run.environment_id or DEFAULT_ENVIRONMENT,
            # The policy is part of the situation: knowledge captured under a
            # read-only run says nothing about what happens when writes are allowed.
            policy_id=policy.policy_id,
            origin=policy.allowed_origins[0] if len(policy.allowed_origins) == 1 else None,
        )
        try:
            context: MemoryContext = await retrieve_memory_context(
                self._container.unit_of_work(),
                MemoryContextRequest(scope=scope),
                now=datetime.now(UTC),
            )
        except Exception:
            logger.exception("recalling memory for run %s failed; running cold", run.run_id)
            return ()

        self.memory_metrics.record_retrieval(
            project_id=run.project_id,
            items=len(context.items),
            revalidate=sum(1 for item in context.items if item.requires_revalidation),
            model_derived=sum(1 for item in context.items if item.model_derived),
        )
        return context.items

    @activity.defn(name="consolidate_experience")
    async def consolidate_experience(self, params: ConsolidateParams) -> int:
        """Turn a finished run into durable knowledge. Returns how many candidates hold.

        Failures are swallowed on purpose. The run is over and its verdict is already
        durable; losing what it could have taught later runs is a missed optimisation,
        while failing here would mark a completed run as failed because the *learning*
        broke. Consolidation is idempotent, so the next run over the same ground
        recovers the knowledge anyway.
        """
        try:
            result = await consolidate_experience(
                self._container.unit_of_work(),
                ConsolidateExperienceCommand(run_id=params.run_id),
                now=datetime.now(UTC),
            )
        except Exception:
            logger.exception("consolidating run %s into knowledge failed", params.run_id)
            return 0

        self.memory_metrics.record_consolidation(
            run_id=params.run_id,
            learned=len(result.candidates),
            contradicted=len(result.contradicted),
        )
        if result.skipped:
            # Loud on purpose: silence here would hide redaction quietly discarding
            # everything the system tries to learn.
            logger.info(
                "run %s: %d observation(s) not learnable: %s",
                params.run_id,
                len(result.skipped),
                "; ".join(result.skipped),
            )
        return len(result.candidates)

    @activity.defn(name="start_scheduled_run")
    async def start_scheduled_run(self, params: StartScheduledRunParams) -> str:
        """Create the run a schedule firing asks for, and return its id.

        Deliberately the *same* path an API-triggered run takes, idempotency record and
        all. A second way to create a run would be a second place for the ordering ADR
        0010 fixes to be got wrong, and the difference between a nightly run and a
        manual one should be who asked, not what was built.

        Unlike consolidation and failure analysis, failures here are **not** swallowed:
        there is no run yet, so nothing is corrupted by trying again, and a firing that
        silently produced nothing is a regression nobody ran and nobody noticed.
        """
        if self._container.workflows is None:
            raise RuntimeError("a scheduled run needs a workflow gateway to start the run")

        schedule = params.schedule
        async with self._container.unit_of_work() as uow:
            result = await start_run(
                uow,
                self._container.workflows,
                StartRunCommand(
                    project_id=schedule.project_id,
                    idempotency_key=params.idempotency_key,
                    environment_id=schedule.environment_id,
                    run_policy_id=schedule.run_policy_id,
                    plan_id=schedule.plan_id,
                    plan_version=schedule.plan_version,
                    request_id=f"schedule:{schedule.schedule_id}",
                ),
                publisher=self._container.events,
            )
        if result.replayed:
            # This firing already created its run; Temporal is retrying the activity
            # after a lost acknowledgement. Returning the same id is the whole point.
            logger.info(
                "schedule %s replayed firing %s", schedule.schedule_id, params.idempotency_key
            )
        return result.run.run_id

    @activity.defn(name="analyze_failures")
    async def analyze_failures(self, params: AnalyzeFailuresParams) -> int:
        """Group this project's recent failures and, if a deep model is configured, ask
        it about the largest ones. Returns how many hypotheses were recorded.

        Heartbeats throughout, because a deep model answers in minutes and an activity
        that goes quiet for that long is indistinguishable from a dead worker. Failures
        are swallowed for the same reason as consolidation: the verdict is already
        durable, and a second reading of results that are already written must not be
        able to turn a completed run into a failed one.
        """
        try:
            async with _heartbeating():
                result = await analyze_failures(
                    self._container.unit_of_work,
                    AnalyzeFailuresCommand(run_id=params.run_id),
                    analyst=self._container.deep_analyst,
                    now=datetime.now(UTC),
                )
        except Exception:
            logger.exception("analysing the failures of run %s failed", params.run_id)
            return 0

        if result.replayed:
            logger.info("failure analysis for run %s replayed; nothing re-asked", params.run_id)
        return result.hypotheses_recorded

    @activity.defn(name="sync_knowledge_graph")
    async def sync_knowledge_graph(self, params: SyncGraphParams) -> int:
        """Bring the graph projection up to date. Returns how many nodes it wrote.

        Runs after consolidation, and its failure is never the run's failure: the graph
        is a projection of rows PostgreSQL already holds, so a store that is down costs
        retrieval breadth until the backlog drains and nothing else (ADR 0008).

        Reported as a number rather than swallowed silently, because a projection that
        never catches up is worth noticing before somebody wonders why warm runs stopped
        being warm.
        """
        if self._container.graph is None:
            return 0
        try:
            report = await sync_pending(
                self._container.unit_of_work, self._container.graph, now=datetime.now(UTC)
            )
        except Exception:
            logger.exception("syncing the knowledge graph failed; the backlog keeps the work")
            return 0

        self.memory_metrics.record_sync(
            materialized=report.materialized, forgotten=report.forgotten, failed=report.failed
        )
        if report.unavailable:
            logger.warning("graph store unavailable; %d entries still pending", report.failed)
        return report.materialized

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


@asynccontextmanager
async def _heartbeating(
    interval_seconds: float = HEARTBEAT_INTERVAL_SECONDS,
) -> AsyncIterator[None]:
    """Keep an activity visibly alive across a call that takes minutes.

    Temporal cannot tell a slow model from a dead worker; without a heartbeat the only
    safe configuration would be a timeout long enough to hide a crash for an hour.
    """

    async def beat() -> None:
        while True:
            await asyncio.sleep(interval_seconds)
            activity.heartbeat()

    task = asyncio.create_task(beat())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
