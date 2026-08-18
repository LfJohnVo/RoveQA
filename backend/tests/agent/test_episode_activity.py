"""The Temporal activity driving a real episode.

This is where ADR 0009's division shows up end to end: the graph decides when a
moment is safe, and the activity writes the durable RecoveryPoint with the checkpoint
id that only exists once the graph has run.
"""

import asyncio
import sys
from collections.abc import AsyncIterator, Callable, Coroutine
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

import psycopg
import pytest
from temporalio.testing import ActivityEnvironment

from agentic_qa.application.ports.browser import BrowserGateway
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.bootstrap.container import Container
from agentic_qa.domain.browser.actions import ActionTarget, BrowserAction, BrowserActionType
from agentic_qa.domain.projects.project import Project
from agentic_qa.domain.projects.run_policy import RunPolicy
from agentic_qa.domain.runs.recovery import RecoveryTrigger
from agentic_qa.domain.runs.run import Run, RunStatus
from agentic_qa.infrastructure.agent.langgraph.checkpointer import open_checkpointer
from agentic_qa.infrastructure.agent.langgraph.episode_runner import LangGraphEpisodeRunner
from agentic_qa.infrastructure.persistence.postgres.engine import (
    create_engine,
    create_session_factory,
)
from agentic_qa.infrastructure.persistence.postgres.models import Base
from agentic_qa.infrastructure.persistence.postgres.unit_of_work import PostgresUnitOfWork
from agentic_qa.infrastructure.workflows.temporal.activities import RunActivities
from agentic_qa.infrastructure.workflows.temporal.contracts import EpisodeParams
from tests.conftest import postgres_test_dsn
from tests.fakes.agent import RecordingBrowserGateway, ScriptedModelGateway

ALLOWED_ORIGIN = "http://target.test"


def run_with_compatible_loop(main: Callable[[], Coroutine[Any, Any, Any]]) -> Any:
    loop_factory = asyncio.SelectorEventLoop if sys.platform == "win32" else None
    with asyncio.Runner(loop_factory=loop_factory) as runner:
        return runner.run(main())


def navigate(step: int) -> BrowserAction:
    return BrowserAction(
        type=BrowserActionType.NAVIGATE,
        intent=f"open page {step}",
        target=ActionTarget(url=f"{ALLOWED_ORIGIN}/page/{step}"),
    )


def policy_for(project_id: str, policy_id: str) -> RunPolicy:
    return RunPolicy(
        policy_id=policy_id,
        project_id=project_id,
        allowed_origins=(ALLOWED_ORIGIN,),
        max_duration_seconds=600,
        max_actions=100,
        max_model_calls=10,
    )


@asynccontextmanager
async def prepared_container(
    browser: BrowserGateway, script: list[BrowserAction]
) -> AsyncIterator[tuple[Container, str]]:
    """A container wired the way the worker wires itself, with fakes for model/browser."""
    engine = create_engine(postgres_test_dsn())
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = create_session_factory(engine)

    def unit_of_work() -> UnitOfWork:
        return PostgresUnitOfWork(session_factory)

    @asynccontextmanager
    async def browser_factory() -> AsyncIterator[BrowserGateway]:
        yield browser

    def checkpointer_factory() -> Any:
        return open_checkpointer(postgres_test_dsn())

    run_id = f"r-{uuid4()}"
    project_id = f"p-{uuid4()}"
    policy_id = f"pol-{uuid4()}"
    async with unit_of_work() as uow:
        await uow.projects.add(
            Project(project_id=project_id, name="Episodes", default_run_policy_id=policy_id)
        )
        await uow.policies.add(policy_for(project_id, policy_id))
        run = Run(run_id=run_id, project_id=project_id, run_policy_id=policy_id)
        run.transition_to(RunStatus.QUEUED)
        await uow.runs.add(run)
        await uow.commit()

    container = Container(
        unit_of_work=unit_of_work,
        engine=engine,
        episodes=LangGraphEpisodeRunner(
            model=ScriptedModelGateway(script=script),
            browser_factory=browser_factory,
            checkpointer_factory=checkpointer_factory,
        ),
    )
    try:
        yield container, run_id
    finally:
        await engine.dispose()


def test_the_activity_runs_the_graph_and_records_a_recovery_point() -> None:
    browser = RecordingBrowserGateway(url=f"{ALLOWED_ORIGIN}/page/1")

    async def main() -> tuple[list[str], Any]:
        async with prepared_container(browser, [navigate(1), navigate(2)]) as (
            container,
            run_id,
        ):
            activities = RunActivities(container)
            # The real activity heartbeats, so it needs a real activity context.
            await ActivityEnvironment().run(
                activities.run_episode, EpisodeParams(run_id=run_id, episode_index=0)
            )

            async with container.unit_of_work() as uow:
                point = await uow.recovery_points.latest_for_run(run_id)
            return browser.executed, point

    try:
        executed, point = run_with_compatible_loop(main)
    except (OSError, psycopg.OperationalError) as error:
        pytest.skip(f"PostgreSQL not reachable: {error}")

    assert executed == ["open page 1", "open page 2"]
    # The graph said the moment was safe; the activity wrote it down with the real id.
    assert point is not None
    assert point.trigger is RecoveryTrigger.EPISODE_CLOSED
    assert point.graph_checkpoint_id


def test_without_a_configured_runtime_the_activity_says_so_instead_of_pretending() -> None:
    """No model gateway exists until Phase 06; the worker must not fake an episode."""

    async def main() -> Any:
        async with prepared_container(RecordingBrowserGateway(), []) as (container, run_id):
            bare = Container(unit_of_work=container.unit_of_work, engine=container.engine)
            outcome = await ActivityEnvironment().run(
                RunActivities(bare).run_episode,
                EpisodeParams(run_id=run_id, episode_index=0),
            )
            async with bare.unit_of_work() as uow:
                point = await uow.recovery_points.latest_for_run(run_id)
            return outcome, point

    try:
        outcome, point = run_with_compatible_loop(main)
    except (OSError, psycopg.OperationalError) as error:
        pytest.skip(f"PostgreSQL not reachable: {error}")

    assert outcome.more_work is False
    assert point is None  # nothing ran, so nothing is claimed as safe


def test_the_activity_enforces_the_runs_policy_on_the_browser() -> None:
    """The runner wraps the gateway, so an off-origin action cannot reach the browser."""
    browser = RecordingBrowserGateway(url=f"{ALLOWED_ORIGIN}/page/1")
    off_origin = BrowserAction(
        type=BrowserActionType.NAVIGATE,
        intent="open somewhere else",
        target=ActionTarget(url="https://evil.test/steal"),
    )

    async def main() -> list[str]:
        async with prepared_container(browser, [off_origin]) as (container, run_id):
            with pytest.raises(Exception):  # noqa: B017 - denial surfaces as an error
                await ActivityEnvironment().run(
                    RunActivities(container).run_episode,
                    EpisodeParams(run_id=run_id, episode_index=0),
                )
            return browser.executed

    try:
        executed = run_with_compatible_loop(main)
    except (OSError, psycopg.OperationalError) as error:
        pytest.skip(f"PostgreSQL not reachable: {error}")

    assert executed == []  # the denied action never reached the browser
