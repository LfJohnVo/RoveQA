"""The headline gate of Phase 17: a story only reachable with a session reaches `passed`.

Everything real participates — PostgreSQL, the keyring, Chromium, the policy guard and
the deterministic verifier. The planner is a double, because a model's variance must not
decide whether this is green.

The fixture's `/dashboard` is the whole point of the shape: with a valid `target_session`
cookie it says "Signed in", and without one it says "Please sign in". So the same story,
the same plan, the same literal, run twice, separates a provisioned session from an
anonymous context by nothing but whether a session was lent to it.

The negative case is the one worth reading. Landing on a login page means the criterion's
literal is absent, and a deterministic check that reports absence reports
`FailureKind.PRODUCT` — an accusation. It must not: the application is working exactly as
designed, and the run is the thing that could not do its job (ADR 0019).
"""

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import psycopg
import pytest
from temporalio.testing import ActivityEnvironment

from agentic_qa.application.commands.compile_plan import CompilePlanCommand, compile_plan
from agentic_qa.application.ports.browser import BrowserGateway, BrowserSetup
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.bootstrap.container import Container
from agentic_qa.domain.browser.actions import ActionTarget, BrowserAction, BrowserActionType
from agentic_qa.domain.projects.environment import Environment
from agentic_qa.domain.projects.project import Project
from agentic_qa.domain.projects.run_policy import RunPolicy
from agentic_qa.domain.projects.session import EnvironmentSession
from agentic_qa.domain.qa.user_story import AcceptanceCriterion, UserStory
from agentic_qa.domain.qa.verification import CriterionOutcome, CriterionResult, FailureKind
from agentic_qa.domain.runs.run import Run, RunStatus, Verdict
from agentic_qa.infrastructure.agent.langgraph.checkpointer import open_checkpointer
from agentic_qa.infrastructure.agent.langgraph.episode_runner import LangGraphEpisodeRunner
from agentic_qa.infrastructure.browser.playwright.gateway import (
    parse_storage_state,
    start_browser_session,
)
from agentic_qa.infrastructure.keyring.file_keyring import FileSecretKeyring
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
from tests.target_app.app import SESSION_COOKIE
from tests.target_app.server import running_target_app

CRITERION = "ac-signed-in"
SIGNED_IN = "Signed in"


def storage_state_for(base_url: str) -> str:
    """A session as a browser exports one, carrying the fixture's own cookie.

    Built rather than captured by driving the login, and deliberately: what this gate is
    about is *lending* an established session, which is the path that puts no password
    anywhere near the agent. Logging in as a story is a different shape.
    """
    host = urlsplit(base_url).hostname or "127.0.0.1"
    return json.dumps(
        {
            "cookies": [
                {
                    "name": SESSION_COOKIE,
                    "value": "valid",
                    "domain": host,
                    "path": "/",
                    "expires": -1,
                    "httpOnly": True,
                    "secure": False,
                    "sameSite": "Lax",
                }
            ],
            "origins": [],
        }
    )


def script_for(base_url: str) -> list[BrowserAction]:
    """Navigate to the dashboard and stop. Whether it says "Signed in" is the question."""
    return [
        BrowserAction(
            type=BrowserActionType.NAVIGATE,
            intent="open the dashboard",
            target=ActionTarget(url=f"{base_url}/dashboard"),
        )
    ]


@asynccontextmanager
async def prepared(
    base_url: str, keyring_root: Path, *, lend_a_session: bool
) -> AsyncIterator[tuple[Container, str]]:
    engine = create_engine(postgres_test_dsn())
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = create_session_factory(engine)

    def unit_of_work() -> UnitOfWork:
        return PostgresUnitOfWork(session_factory)

    keyring = FileSecretKeyring(keyring_root)
    project_id = f"p-{uuid4()}"
    policy_id = f"pol-{uuid4()}"
    environment_id = f"env-{uuid4()}"

    async with unit_of_work() as uow:
        await uow.projects.add(Project(project_id=project_id, name="Behind a login"))
        await uow.policies.add(
            RunPolicy(
                policy_id=policy_id,
                project_id=project_id,
                allowed_origins=(base_url,),
                max_duration_seconds=120,
                max_actions=10,
                max_model_calls=10,
                destructive_actions=False,
            )
        )
        await uow.environments.add(
            Environment(environment_id=environment_id, project_id=project_id, name="with-a-session")
        )
        if lend_a_session:
            session = EnvironmentSession(
                session_id=f"sess-{uuid4()}",
                environment_id=environment_id,
                label="admin",
                established_at=datetime.now(UTC),
                established_by="the test",
            )
            sealed = await keyring.seal(
                session.session_id, storage_state_for(base_url).encode("utf-8")
            )
            await uow.sessions.add(session, sealed)
        await uow.commit()

    story = UserStory(
        story_id=f"s-{uuid4()}",
        project_id=project_id,
        actor="a signed-in operator",
        goal="see the dashboard",
        acceptance_criteria=(
            AcceptanceCriterion(
                criterion_id=CRITERION,
                description="the dashboard greets a signed-in operator",
                verification_hint=SIGNED_IN,
            ),
        ),
    )
    async with unit_of_work() as uow:
        await uow.stories.add(story)
        await uow.commit()
        plan = await compile_plan(
            uow, CompilePlanCommand(story_id=story.story_id, run_policy_id=policy_id)
        )

    run_id = f"r-{uuid4()}"
    async with unit_of_work() as uow:
        run = Run(
            run_id=run_id,
            project_id=project_id,
            run_policy_id=policy_id,
            environment_id=environment_id,
            plan_id=plan.plan_id,
            plan_version=plan.plan_version,
        )
        run.transition_to(RunStatus.QUEUED)
        await uow.runs.add(run)
        await uow.commit()

    @asynccontextmanager
    async def browser_factory(setup: BrowserSetup) -> AsyncIterator[BrowserGateway]:
        # The real provisioning path: whatever the activity resolved reaches Chromium
        # here, or does not. Nothing in this test hands the cookie over any other way.
        opened = await start_browser_session(
            headless=True,
            storage_state=(
                parse_storage_state(setup.storage_state_json)
                if setup.storage_state_json is not None
                else None
            ),
            secrets=setup.secrets,
        )
        try:
            yield opened.gateway
        finally:
            await opened.aclose()

    container = Container(
        unit_of_work=unit_of_work,
        engine=engine,
        keyring=keyring,
        episodes=LangGraphEpisodeRunner(
            model=ScriptedModelGateway(script=script_for(base_url)),
            browser_factory=browser_factory,
            checkpointer_factory=lambda: open_checkpointer(postgres_test_dsn()),
        ),
    )
    try:
        yield container, run_id
    finally:
        await engine.dispose()


async def run_it(
    keyring_root: Path, *, lend_a_session: bool
) -> tuple[str | None, list[CriterionResult]]:
    async with (
        running_target_app() as (base_url, _state),
        prepared(base_url, keyring_root, lend_a_session=lend_a_session) as (container, run_id),
    ):
        outcome = await ActivityEnvironment().run(
            RunActivities(container).run_episode,
            EpisodeParams(run_id=run_id, episode_index=0),
        )
        async with container.unit_of_work() as uow:
            results = list(await uow.criterion_results.list_for_run(run_id))
        return outcome.verdict, results


def execute(
    keyring_root: Path, *, lend_a_session: bool
) -> tuple[str | None, list[CriterionResult]]:
    try:
        return asyncio.run(run_it(keyring_root, lend_a_session=lend_a_session))
    except (OSError, psycopg.OperationalError) as error:
        pytest.skip(f"PostgreSQL not reachable: {error}")


def test_a_story_behind_a_login_passes_when_a_session_is_lent(tmp_path: Path) -> None:
    verdict, results = execute(tmp_path / "keyring", lend_a_session=True)

    story = [item for item in results if item.criterion_id == CRITERION]
    assert verdict == Verdict.PASSED.value, results
    assert [item.outcome for item in story] == [CriterionOutcome.MET]


def test_the_same_story_without_a_session_never_accuses_the_product(tmp_path: Path) -> None:
    """The same plan, the same literal, no session. It must not come back `failed`.

    The dashboard answers 200 and renders a login prompt, so the literal is genuinely
    absent — and a deterministic check reporting absence is exactly how a correct
    application gets accused. What the run should say is that *it* could not get there.
    """
    verdict, results = execute(tmp_path / "keyring", lend_a_session=False)

    story = [item for item in results if item.criterion_id == CRITERION]
    assert verdict != Verdict.FAILED.value, results
    assert [item.failure_kind for item in story] != [FailureKind.PRODUCT]
