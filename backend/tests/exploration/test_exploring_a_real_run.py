"""An exploring run, end to end: Temporal activity, real Chromium, real PostgreSQL.

Everything else in this package tests a piece. This tests the chain the phase is
actually for: a run asks to explore, the activity drives a real browser over a real
application with no model configured to plan anything, the map lands durably, and a
second run of the same application produces a delta somebody could act on.

The second run is the point. One map says what an application offers; two say what
changed, and only the second is worth waking anyone for.
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

from agentic_qa.application.ports.browser import BrowserGateway
from agentic_qa.application.queries.exploration_report import exploration_outcome
from agentic_qa.bootstrap.container import Container
from agentic_qa.domain.projects.project import Project
from agentic_qa.domain.projects.run_policy import RunPolicy
from agentic_qa.domain.runs.run import Run, RunStatus
from agentic_qa.infrastructure.agent.langgraph.checkpointer import open_checkpointer
from agentic_qa.infrastructure.agent.langgraph.episode_runner import LangGraphEpisodeRunner
from agentic_qa.infrastructure.browser.playwright.gateway import start_browser_session
from agentic_qa.infrastructure.persistence.postgres.engine import (
    create_engine,
    create_session_factory,
)
from agentic_qa.infrastructure.persistence.postgres.models import Base
from agentic_qa.infrastructure.persistence.postgres.unit_of_work import PostgresUnitOfWork
from agentic_qa.infrastructure.workflows.temporal.activities import RunActivities
from agentic_qa.infrastructure.workflows.temporal.contracts import EpisodeParams
from tests.conftest import postgres_test_dsn
from tests.fakes.agent import ScriptedModelGateway
from tests.target_app.server import running_target_app


@asynccontextmanager
async def exploring_project(base_url: str) -> AsyncIterator[tuple[Container, str]]:
    """A project whose runs may read the target app and nothing else."""
    engine = create_engine(postgres_test_dsn())
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = create_session_factory(engine)

    def unit_of_work() -> PostgresUnitOfWork:
        return PostgresUnitOfWork(session_factory)

    project_id = f"p-{uuid4()}"
    policy_id = f"pol-{uuid4()}"
    async with unit_of_work() as uow:
        await uow.projects.add(
            Project(project_id=project_id, name="Explored", default_run_policy_id=policy_id)
        )
        await uow.policies.add(
            RunPolicy(
                policy_id=policy_id,
                project_id=project_id,
                allowed_origins=(base_url,),
                max_duration_seconds=120,
                max_actions=12,
                # Zero, and never consulted: exploring calls no model at all.
                max_model_calls=0,
            )
        )
        await uow.commit()

    @asynccontextmanager
    async def browser_factory() -> AsyncIterator[BrowserGateway]:
        session = await start_browser_session(headless=True)
        try:
            # The explorer maps from wherever the page already is; the run's entry
            # point is the browser's starting page, not something the frontier picks.
            await session.gateway.page.goto(base_url)
            yield session.gateway
        finally:
            await session.aclose()

    container = Container(
        unit_of_work=unit_of_work,
        engine=engine,
        episodes=LangGraphEpisodeRunner(
            # Scripted and empty: if anything asked it to plan, the episode would end
            # immediately and the assertions below would fail rather than pass quietly.
            model=ScriptedModelGateway(script=[]),
            browser_factory=browser_factory,
            checkpointer_factory=lambda: open_checkpointer(postgres_test_dsn()),
        ),
    )
    try:
        yield container, project_id
    finally:
        await engine.dispose()


async def queue_run(container: Container, project_id: str) -> str:
    run_id = f"r-{uuid4()}"
    async with container.unit_of_work() as uow:
        project = await uow.projects.get(project_id)
        assert project is not None
        run = Run(
            run_id=run_id,
            project_id=project_id,
            run_policy_id=project.default_run_policy_id,
        )
        run.transition_to(RunStatus.QUEUED)
        await uow.runs.add(run)
        await uow.commit()
    return run_id


async def explore_twice(_artifact_root: Path) -> Any:
    async with (
        running_target_app() as (base_url, _state),
        exploring_project(base_url) as (container, project_id),
    ):
        activities = RunActivities(container)
        first = await queue_run(container, project_id)
        second = await queue_run(container, project_id)

        for run_id in (first, second):
            await ActivityEnvironment().run(
                activities.run_episode,
                EpisodeParams(run_id=run_id, episode_index=0, explore=True),
            )

        async with container.unit_of_work() as uow:
            first_outcome = await exploration_outcome(uow, first)
            second_outcome = await exploration_outcome(uow, second)
        return first_outcome, second_outcome


def execute(artifact_root: Path) -> Any:
    try:
        return asyncio.run(explore_twice(artifact_root))
    except (OSError, psycopg.OperationalError) as error:
        pytest.skip(f"PostgreSQL not reachable: {error}")


def test_an_exploring_run_leaves_a_durable_map(tmp_path: Path) -> None:
    first, _second = execute(tmp_path)

    assert first.report.states_discovered > 1
    assert first.state_map.states
    # Every state it recorded is inside the application it was allowed to visit.
    assert all(state.url.startswith("http://") for state in first.state_map.states)


def test_the_report_says_what_it_spent_and_why_it_stopped(tmp_path: Path) -> None:
    first, _second = execute(tmp_path)

    assert first.report.actions_taken > 0
    assert first.report.stop_reason.value in {
        "frontier_exhausted",
        "max_actions",
        "max_states",
        "deadline",
    }
    # Buttons on a read-only run: counted, never attempted.
    assert first.report.declined >= 0


def test_the_first_exploration_of_an_application_is_not_a_pile_of_findings(
    tmp_path: Path,
) -> None:
    first, _second = execute(tmp_path)

    assert first.baseline_run_id is None
    assert first.delta is None


def test_the_second_run_compares_against_the_first(tmp_path: Path) -> None:
    """The same application, unchanged between runs, must produce no findings.

    This is the gate. If the signature depended on anything volatile — a timestamp, a
    row count, render order — a nightly regression would report the whole application
    as changed every single night.
    """
    first, second = execute(tmp_path)

    assert second.baseline_run_id == first.run_id
    assert second.delta is not None
    assert not second.delta.has_findings, (
        f"new={[s.route for s in second.delta.new]} "
        f"gone={[s.route for s in second.delta.gone]} "
        f"changed={[c.summary for c in second.delta.changed]}"
    )
