"""Evidence, from the live page to the failure bundle.

Phase 07 could say *which* criterion was not met but could not show anything: nothing
captured artifacts, so `evidence_refs` was always empty and a bundle from a real run
held only a manifest. This closes that chain and tests it end to end — a real
episode, a real screenshot written through the repository, indexed durably, and
reachable from the failure context under one evidence set.
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

import psycopg
import pytest
from temporalio.testing import ActivityEnvironment

from agentic_qa.application.commands.compile_plan import CompilePlanCommand, compile_plan
from agentic_qa.application.ports.browser import BrowserGateway
from agentic_qa.application.queries.failure_context import load_failure_context, to_manifest
from agentic_qa.bootstrap.container import Container
from agentic_qa.domain.browser.actions import ActionTarget, BrowserAction, BrowserActionType
from agentic_qa.domain.projects.project import Project
from agentic_qa.domain.projects.run_policy import RunPolicy
from agentic_qa.domain.qa.user_story import AcceptanceCriterion, UserStory
from agentic_qa.domain.runs.run import Run, RunStatus, Verdict
from agentic_qa.infrastructure.agent.langgraph.checkpointer import open_checkpointer
from agentic_qa.infrastructure.agent.langgraph.episode_runner import LangGraphEpisodeRunner
from agentic_qa.infrastructure.artifacts.filesystem.repository import (
    FilesystemArtifactRepository,
)
from agentic_qa.infrastructure.browser.playwright.gateway import start_browser_session
from agentic_qa.infrastructure.persistence.postgres.engine import (
    create_engine,
    create_session_factory,
)
from agentic_qa.infrastructure.persistence.postgres.models import Base
from agentic_qa.infrastructure.persistence.postgres.unit_of_work import PostgresUnitOfWork
from agentic_qa.infrastructure.workflows.temporal.activities import RunActivities
from agentic_qa.infrastructure.workflows.temporal.contracts import (
    EpisodeParams,
    TransitionParams,
)
from tests.conftest import postgres_test_dsn
from tests.fakes.agent import ScriptedModelGateway
from tests.target_app.server import running_target_app


@asynccontextmanager
async def prepared(base_url: str, artifact_root: Path) -> AsyncIterator[tuple[Container, str]]:
    """A run wired the way the worker wires itself, with a real artifact repository."""
    engine = create_engine(postgres_test_dsn())
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = create_session_factory(engine)

    def unit_of_work() -> PostgresUnitOfWork:
        return PostgresUnitOfWork(session_factory)

    project_id = f"p-{uuid4()}"
    policy_id = f"pol-{uuid4()}"
    story = UserStory(
        story_id=f"story-{uuid4()}",
        project_id=project_id,
        actor="a QA engineer",
        goal="open the records page",
        acceptance_criteria=(
            AcceptanceCriterion(
                criterion_id="ac-listing",
                description="the records page offers a way to create a record",
                # Deliberately absent from the page, so the run fails and there is a
                # failure worth bundling.
                verification_hint="Order dispatched",
            ),
        ),
    )

    async with unit_of_work() as uow:
        await uow.projects.add(
            Project(project_id=project_id, name="Evidence", default_run_policy_id=policy_id)
        )
        await uow.policies.add(
            RunPolicy(
                policy_id=policy_id,
                project_id=project_id,
                allowed_origins=(base_url,),
                max_duration_seconds=120,
                max_actions=10,
                max_model_calls=10,
            )
        )
        await uow.stories.add(story)
        await uow.commit()

    async with unit_of_work() as uow:
        plan = await compile_plan(
            uow, CompilePlanCommand(story_id=story.story_id, run_policy_id=policy_id)
        )

    run_id = f"r-{uuid4()}"
    async with unit_of_work() as uow:
        run = Run(
            run_id=run_id,
            project_id=project_id,
            run_policy_id=policy_id,
            plan_id=plan.plan_id,
            plan_version=plan.plan_version,
        )
        run.transition_to(RunStatus.QUEUED)
        await uow.runs.add(run)
        await uow.commit()

    @asynccontextmanager
    async def browser_factory() -> AsyncIterator[BrowserGateway]:
        session = await start_browser_session(headless=True)
        try:
            yield session.gateway
        finally:
            await session.aclose()

    container = Container(
        unit_of_work=unit_of_work,
        engine=engine,
        artifacts=FilesystemArtifactRepository(artifact_root),
        episodes=LangGraphEpisodeRunner(
            model=ScriptedModelGateway(
                script=[
                    BrowserAction(
                        type=BrowserActionType.NAVIGATE,
                        intent="open the records page",
                        target=ActionTarget(url=f"{base_url}/records"),
                    )
                ]
            ),
            browser_factory=browser_factory,
            checkpointer_factory=lambda: open_checkpointer(postgres_test_dsn()),
            artifacts=FilesystemArtifactRepository(artifact_root),
        ),
    )
    try:
        yield container, run_id
    finally:
        await engine.dispose()


async def run_episode(artifact_root: Path) -> Any:
    async with (
        running_target_app() as (base_url, _state),
        prepared(base_url, artifact_root) as (container, run_id),
    ):
        activities = RunActivities(container)
        outcome = await ActivityEnvironment().run(
            activities.run_episode,
            EpisodeParams(run_id=run_id, episode_index=0),
        )
        # The workflow, not the episode activity, writes the verdict onto the run.
        # This test drives the activity directly, so it performs that step itself
        # rather than leaving the run without the verdict a bundle requires.
        await ActivityEnvironment().run(
            activities.transition_run_status,
            TransitionParams(run_id=run_id, target_status="running"),
        )
        await ActivityEnvironment().run(
            activities.transition_run_status,
            TransitionParams(run_id=run_id, target_status="completed", verdict=outcome.verdict),
        )

        # Everything is read inside this block, while the container still owns a
        # live engine. Reaching back in afterwards would query a disposed pool.
        async with container.unit_of_work() as uow:
            context = await load_failure_context(
                uow.runs, uow.criterion_results, uow.artifacts, run_id=run_id
            )
            recovery_point = await uow.recovery_points.latest_for_run(run_id)
        return outcome, context, recovery_point, run_id


def execute(artifact_root: Path) -> Any:
    try:
        return asyncio.run(run_episode(artifact_root))
    except (OSError, psycopg.OperationalError) as error:
        pytest.skip(f"PostgreSQL not reachable: {error}")


def test_a_failing_run_leaves_evidence_a_bundle_can_show(tmp_path: Path) -> None:
    """The chain Phase 07 could not complete: capture, index, and reach it again."""
    outcome, context, _point, run_id = execute(tmp_path)

    assert outcome.verdict == Verdict.FAILED.value

    # Captured while the browser was open, and written where the repository puts it.
    assert len(context.artifacts) == 1
    artifact = context.artifacts[0]
    assert artifact.kind == "screenshot"
    assert artifact.size_bytes > 0
    assert (tmp_path / artifact.relative_path).exists()

    # Indexed durably against this run and one evidence set.
    assert artifact.run_id == run_id
    assert context.evidence_set_id == artifact.evidence_set_id
    assert artifact.evidence_set_id == f"{run_id}-e0"


def test_the_failed_criterion_points_at_the_evidence(tmp_path: Path) -> None:
    """`evidence_refs` existed and nobody filled it; a failure named nothing showable."""
    _outcome, context, _point, _run_id = execute(tmp_path)

    result = context.results[0]
    assert result.criterion_id == "ac-listing"
    assert result.evidence_refs == (context.artifacts[0].artifact_id,)


def test_the_manifest_carries_the_artifact_with_its_provenance(tmp_path: Path) -> None:
    _outcome, context, _point, _run_id = execute(tmp_path)

    manifest = to_manifest(context)
    entry = manifest["artifacts"][0]  # type: ignore[index]

    # Everything the bundle's coherence check compares against travels with the row.
    assert entry["run_id"] == manifest["run_id"]
    assert entry["evidence_set_id"] == manifest["evidence_set_id"]
    assert len(entry["sha256"]) == 64


def test_the_recovery_point_records_where_the_page_ended_up(tmp_path: Path) -> None:
    """It used to be written empty, so recovery would rebuild a browser and go nowhere."""
    _outcome, _context, point, _run_id = execute(tmp_path)

    assert point is not None
    assert point.browser.url.endswith("/records")
