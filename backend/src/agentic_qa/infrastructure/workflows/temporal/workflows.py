"""AgentRunWorkflow: the durable owner of a run's lifecycle (ADR 0009).

Shape fixed by the ADR and not to be renegotiated in later phases:
- one activity per episode, so pause/cancel apply between episodes and the history
  stays bounded;
- pause/resume/cancel arrive as signals; the workflow stops at a safe point rather
  than killing work mid-flight;
- every side effect and every write lives in an activity — the workflow itself does
  no I/O, which is what keeps it deterministic and replayable;
- continue-as-new past an episode threshold, so an exploratory run cannot grow its
  event history without bound.
"""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from agentic_qa.infrastructure.workflows.temporal.contracts import (
        AnalyzeFailuresParams,
        ConsolidateParams,
        EpisodeOutcome,
        EpisodeParams,
        RunParams,
        ScheduledRunParams,
        StartScheduledRunParams,
        SyncGraphParams,
        TransitionParams,
    )

# Beyond this many episodes the workflow starts a fresh history with the same run.
EPISODES_BEFORE_CONTINUE_AS_NEW = 200

_STATUS_ACTIVITY_RETRY = RetryPolicy(maximum_attempts=5)

_CONSOLIDATION_RETRY = RetryPolicy(maximum_attempts=2)
"""Barely retried. The activity already swallows its own failures, so an attempt that
reaches Temporal at all is an infrastructure problem, and the verdict this workflow
exists to produce is durable before it runs."""


@workflow.defn(name="AgentRunWorkflow")
class AgentRunWorkflow:
    def __init__(self) -> None:
        self._paused = False
        self._cancel_requested = False

    @workflow.signal
    def pause(self) -> None:
        self._paused = True

    @workflow.signal
    def resume(self) -> None:
        self._paused = False

    @workflow.signal
    def cancel(self) -> None:
        """Explicit cancellation. Idempotent, and never inferred from a disconnect."""
        self._cancel_requested = True

    @workflow.query
    def is_paused(self) -> bool:
        return self._paused

    @workflow.run
    async def run(self, params: RunParams) -> str:
        if params.start_episode == 0:
            await self._transition(params.run_id, "running")

        episode = params.start_episode
        verdict: str | None = None
        while True:
            if self._cancel_requested:
                return await self._finish_cancelled(params.run_id)

            if self._paused:
                await self._transition(params.run_id, "pausing")
                await self._transition(params.run_id, "paused")
                await workflow.wait_condition(lambda: not self._paused or self._cancel_requested)
                if self._cancel_requested:
                    return await self._finish_cancelled(params.run_id)
                await self._transition(params.run_id, "running")

            # result_type is required for activities called by name: without it the
            # converter returns raw JSON and the annotation below would be a lie.
            outcome: EpisodeOutcome = await workflow.execute_activity(
                "run_episode",
                EpisodeParams(
                    run_id=params.run_id,
                    episode_index=episode,
                    explore=params.explore,
                ),
                result_type=EpisodeOutcome,
                start_to_close_timeout=timedelta(hours=2),
                heartbeat_timeout=timedelta(minutes=2),
            )
            episode += 1
            # Last episode wins: a later episode saw more of the run than an earlier one.
            verdict = outcome.verdict or verdict

            if not outcome.more_work:
                break

            if episode >= EPISODES_BEFORE_CONTINUE_AS_NEW:
                workflow.continue_as_new(
                    RunParams(
                        run_id=params.run_id,
                        project_id=params.project_id,
                        start_episode=episode,
                        explore=params.explore,
                    )
                )

        # A run with no plan verified nothing, so the honest verdict is inconclusive —
        # never a pass. With a plan, the verdict comes from the criterion results the
        # activity persisted and derived.
        final = verdict or "inconclusive"
        await self._transition(params.run_id, "completed", verdict=final)

        # After the verdict is durable, never before: learning is a consequence of a
        # finished run, and a run must not report differently because of what it did
        # or did not manage to remember.
        await workflow.execute_activity(
            "consolidate_experience",
            ConsolidateParams(run_id=params.run_id),
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=_CONSOLIDATION_RETRY,
        )

        # Then the projection: it is derived from what consolidation just committed,
        # and a graph that is down must not be able to delay a verdict that is already
        # durable.
        await workflow.execute_activity(
            "sync_knowledge_graph",
            SyncGraphParams(),
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=_CONSOLIDATION_RETRY,
        )

        # Last, and the slowest by an order of magnitude. Grouping the failures needs no
        # model, but explaining the largest clusters may spend minutes per cluster in a
        # model streamed layer by layer — so it runs after everything a reader needs is
        # already durable, and heartbeats while it works.
        await workflow.execute_activity(
            "analyze_failures",
            AnalyzeFailuresParams(run_id=params.run_id),
            start_to_close_timeout=timedelta(hours=1),
            heartbeat_timeout=timedelta(minutes=2),
            retry_policy=_CONSOLIDATION_RETRY,
        )
        return final

    async def _finish_cancelled(self, run_id: str) -> str:
        await self._transition(run_id, "cancelling")
        await self._transition(run_id, "cancelled", verdict="cancelled")
        return "cancelled"

    async def _transition(self, run_id: str, status: str, verdict: str | None = None) -> None:
        await workflow.execute_activity(
            "transition_run_status",
            TransitionParams(run_id=run_id, target_status=status, verdict=verdict),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=_STATUS_ACTIVITY_RETRY,
        )


_SCHEDULED_START_RETRY = RetryPolicy(maximum_attempts=3)


@workflow.defn(name="ScheduledRunWorkflow")
class ScheduledRunWorkflow:
    """What a schedule actually starts.

    A schedule cannot start `AgentRunWorkflow` directly: that workflow expects a run
    that already exists durably, and ADR 0010 puts the row and its idempotency record
    before the workflow, never after. So a firing creates the run first — in an
    activity, because that is a database write — and the run's own workflow is started
    from there exactly as an API-triggered run is.

    Thin on purpose. Everything durable about the run belongs to `AgentRunWorkflow`;
    this exists only to turn "it is 2am" into a run id.

    Known limitation: this completes as soon as the run is created, so the schedule's
    overlap policy sees a firing that lasted a second rather than a run that lasted an
    hour. A regression slower than its own interval will therefore stack. Fixing it
    means making the run a child of this workflow, which is a bigger change than the
    problem currently justifies.
    """

    @workflow.run
    async def run(self, params: ScheduledRunParams) -> str:
        # The firing's own workflow id: derived by Temporal from the schedule and the
        # scheduled time, so it is stable across retries of this firing and different
        # for the next one. Exactly the identity run creation needs, and deterministic,
        # which `uuid4()` here would not be.
        key = workflow.info().workflow_id
        # Annotated because activities called by name return the converter's Any;
        # the same reason `run_episode` above declares its result type.
        run_id: str = await workflow.execute_activity(
            "start_scheduled_run",
            StartScheduledRunParams(idempotency_key=key, schedule=params),
            result_type=str,
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=_SCHEDULED_START_RETRY,
        )
        return run_id
