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
        EpisodeOutcome,
        EpisodeParams,
        RunParams,
        TransitionParams,
    )

# Beyond this many episodes the workflow starts a fresh history with the same run.
EPISODES_BEFORE_CONTINUE_AS_NEW = 200

_STATUS_ACTIVITY_RETRY = RetryPolicy(maximum_attempts=5)


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
                EpisodeParams(run_id=params.run_id, episode_index=episode),
                result_type=EpisodeOutcome,
                start_to_close_timeout=timedelta(hours=2),
                heartbeat_timeout=timedelta(minutes=2),
            )
            episode += 1

            if not outcome.more_work:
                break

            if episode >= EPISODES_BEFORE_CONTINUE_AS_NEW:
                workflow.continue_as_new(
                    RunParams(
                        run_id=params.run_id,
                        project_id=params.project_id,
                        start_episode=episode,
                    )
                )

        # No plan was executed and nothing was verified, so the honest verdict is
        # inconclusive rather than a pass. Phase 07 derives it from real results.
        await self._transition(params.run_id, "completed", verdict="inconclusive")
        return "inconclusive"

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
