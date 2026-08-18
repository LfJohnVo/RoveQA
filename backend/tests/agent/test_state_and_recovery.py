"""Agent state shape and the recovery points a resume validates against."""

from collections.abc import Callable
from datetime import UTC, datetime

from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.domain.agent.state import (
    MAX_RECENT_STEPS,
    AgentState,
    EpisodeSummary,
    StepOutcome,
    StepRecord,
)
from agentic_qa.domain.projects.project import Project
from agentic_qa.domain.runs.recovery import (
    BrowserRecoveryData,
    RecoveryPoint,
    RecoveryTrigger,
)
from agentic_qa.domain.runs.run import Run

UnitOfWorkFactory = Callable[[], UnitOfWork]


def step(index: int) -> StepRecord:
    return StepRecord(index=index, intent=f"step {index}", outcome=StepOutcome.SUCCEEDED)


def point(run_id: str, *, episode: int, checkpoint: str, identifier: str) -> RecoveryPoint:
    return RecoveryPoint(
        recovery_point_id=identifier,
        run_id=run_id,
        episode_index=episode,
        trigger=RecoveryTrigger.NAVIGATION_STABLE,
        graph_checkpoint_id=checkpoint,
        browser=BrowserRecoveryData(url="http://app.test/records", page_fingerprint="fp-1"),
        created_at=datetime.now(UTC),
    )


class TestAgentState:
    def test_recent_steps_stay_within_the_working_window(self) -> None:
        """Active context must not grow linearly with steps (Phase 05 gate)."""
        state = AgentState(run_id="r-1", goal="create a record")

        for index in range(MAX_RECENT_STEPS * 5):
            state.record_step(step(index))

        assert len(state.recent_steps) == MAX_RECENT_STEPS
        assert state.recent_steps[-1].index == MAX_RECENT_STEPS * 5 - 1
        assert state.step_index == MAX_RECENT_STEPS * 5 - 1

    def test_closing_an_episode_folds_its_steps_into_a_summary(self) -> None:
        state = AgentState(run_id="r-1", goal="create a record")
        for index in range(10):
            state.record_step(step(index))

        state.close_episode(
            EpisodeSummary(
                episode_index=0,
                goal="create a record",
                steps_taken=10,
                succeeded=True,
                summary="record created and verified",
            )
        )

        assert state.recent_steps == ()  # raw history is gone
        assert len(state.episode_summaries) == 1
        assert state.episode_index == 1

    def test_context_stays_flat_across_many_episodes(self) -> None:
        """A hundred steps leave a handful of summaries, not a hundred entries."""
        state = AgentState(run_id="r-1", goal="long run")

        for episode in range(10):
            for index in range(50):
                state.record_step(step(index))
            state.close_episode(
                EpisodeSummary(
                    episode_index=episode,
                    goal="long run",
                    steps_taken=50,
                    succeeded=True,
                    summary=f"episode {episode} done",
                )
            )

        # 500 steps executed; the planner would read 10 summaries and no raw steps.
        assert state.context_size == 10
        assert state.context_size < MAX_RECENT_STEPS + 10 + 1


class TestRecoveryPoints:
    async def test_points_round_trip_with_their_browser_data(
        self, unit_of_work_factory: UnitOfWorkFactory
    ) -> None:
        async with unit_of_work_factory() as uow:
            await uow.projects.add(Project(project_id="p-rec", name="Recovery"))
            await uow.runs.add(Run(run_id="r-rec", project_id="p-rec"))
            await uow.recovery_points.add(
                point("r-rec", episode=0, checkpoint="ckpt-1", identifier="rp-1")
            )
            await uow.commit()

        async with unit_of_work_factory() as uow:
            stored = await uow.recovery_points.latest_for_run("r-rec")

        assert stored is not None
        assert stored.graph_checkpoint_id == "ckpt-1"
        assert stored.browser.url == "http://app.test/records"
        assert stored.browser.page_fingerprint == "fp-1"
        assert stored.trigger is RecoveryTrigger.NAVIGATION_STABLE

    async def test_the_latest_point_is_the_one_a_resume_validates_against(
        self, unit_of_work_factory: UnitOfWorkFactory
    ) -> None:
        async with unit_of_work_factory() as uow:
            await uow.projects.add(Project(project_id="p-rec", name="Recovery"))
            await uow.runs.add(Run(run_id="r-rec", project_id="p-rec"))
            for index in range(3):
                await uow.recovery_points.add(
                    point(
                        "r-rec",
                        episode=index,
                        checkpoint=f"ckpt-{index}",
                        identifier=f"rp-{index}",
                    )
                )
            await uow.commit()

        async with unit_of_work_factory() as uow:
            latest = await uow.recovery_points.latest_for_run("r-rec")
            listed = await uow.recovery_points.list_for_run("r-rec", limit=2)

        assert latest is not None
        assert latest.graph_checkpoint_id == "ckpt-2"
        assert len(listed) == 2  # bounded read

    async def test_points_of_other_runs_are_not_returned(
        self, unit_of_work_factory: UnitOfWorkFactory
    ) -> None:
        async with unit_of_work_factory() as uow:
            await uow.projects.add(Project(project_id="p-rec", name="Recovery"))
            await uow.runs.add(Run(run_id="r-a", project_id="p-rec"))
            await uow.runs.add(Run(run_id="r-b", project_id="p-rec"))
            await uow.recovery_points.add(
                point("r-a", episode=0, checkpoint="ckpt-a", identifier="rp-a")
            )
            await uow.commit()

        async with unit_of_work_factory() as uow:
            assert await uow.recovery_points.latest_for_run("r-b") is None
