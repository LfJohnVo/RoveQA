"""A known story, run for real, twice.

This is the phase's headline gate: the same story passes reproducibly against a working
target and fails reproducibly against one that does not confirm what the story promised
— with the failure naming the criterion, not just reporting that something went wrong.

Everything real participates: PostgreSQL, the LangGraph checkpointer, Chromium, the
policy guard and the deterministic verifier. Only the planner is a double, because a
model's variance is exactly what must not decide whether this test is green.
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

import psycopg
import pytest
from temporalio.testing import ActivityEnvironment

from agentic_qa.application.commands.compile_plan import CompilePlanCommand, compile_plan
from agentic_qa.application.ports.browser import BrowserGateway
from agentic_qa.application.queries.run_report import (
    RunReport,
    build_run_report,
    render_markdown,
    to_document,
)
from agentic_qa.bootstrap.container import Container
from agentic_qa.domain.browser.actions import (
    ActionTarget,
    BrowserAction,
    BrowserActionType,
    IdempotencyStrategy,
)
from agentic_qa.domain.projects.project import Project
from agentic_qa.domain.projects.run_policy import RunPolicy
from agentic_qa.domain.qa.user_story import AcceptanceCriterion, UserStory
from agentic_qa.domain.qa.verification import CriterionOutcome, FailureKind
from agentic_qa.domain.runs.run import Run, RunStatus, Verdict
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


def write(intent: str, action: BrowserActionType, **kwargs: Any) -> BrowserAction:
    """A state-changing action with the safety fields the domain requires."""
    return BrowserAction(
        type=action,
        intent=intent,
        side_effect=True,
        idempotency_strategy=IdempotencyStrategy.VERIFY_BEFORE_RETRY,
        verification_strategy="the resulting page reflects this step",
        **kwargs,
    )


def script_for(base_url: str, reference: str) -> list[BrowserAction]:
    """What a planner would decide, fixed so the test measures the pipeline, not a model."""
    return [
        BrowserAction(
            type=BrowserActionType.NAVIGATE,
            intent="open the records page",
            target=ActionTarget(url=f"{base_url}/records"),
        ),
        write(
            "enter the reference",
            BrowserActionType.FILL,
            target=ActionTarget(label="Reference"),
            value=reference,
        ),
        write(
            "enter the name",
            BrowserActionType.FILL,
            target=ActionTarget(label="Name"),
            value="End to end",
        ),
        write(
            "submit the record",
            BrowserActionType.CLICK,
            target=ActionTarget(role="button", name="Create record"),
        ),
    ]


@asynccontextmanager
async def prepared(base_url: str, *, hint: str | None) -> AsyncIterator[tuple[Container, str]]:
    """Seed a project, story, plan and run, and wire the real runtime around them."""
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
        goal="create a record and see it confirmed",
        acceptance_criteria=(
            AcceptanceCriterion(
                criterion_id="ac-created",
                description="the page confirms the record was created",
                # The hint is what makes this criterion checkable without a model.
                verification_hint=hint,
            ),
        ),
    )

    async with unit_of_work() as uow:
        await uow.projects.add(
            Project(project_id=project_id, name="E2E", default_run_policy_id=policy_id)
        )
        await uow.policies.add(
            RunPolicy(
                policy_id=policy_id,
                project_id=project_id,
                allowed_origins=(base_url,),
                max_duration_seconds=120,
                max_actions=20,
                max_model_calls=10,
                # Filling a form and submitting it is not a read-only run.
                destructive_actions=True,
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
        episodes=LangGraphEpisodeRunner(
            model=ScriptedModelGateway(script=script_for(base_url, f"REF-{uuid4().hex[:6]}")),
            browser_factory=browser_factory,
            checkpointer_factory=lambda: open_checkpointer(postgres_test_dsn()),
        ),
    )
    try:
        yield container, run_id
    finally:
        await engine.dispose()


async def run_story(*, hint: str | None) -> tuple[str | None, RunReport]:
    """Execute the story once against a live target app."""
    async with (
        running_target_app() as (base_url, _state),
        prepared(base_url, hint=hint) as (container, run_id),
    ):
        # The real activity heartbeats, so it needs a real activity context.
        outcome = await ActivityEnvironment().run(
            RunActivities(container).run_episode,
            EpisodeParams(run_id=run_id, episode_index=0),
        )
        async with container.unit_of_work() as uow:
            report = await build_run_report(
                uow.runs, uow.plans, uow.criterion_results, run_id=run_id
            )
        return outcome.verdict, report


def execute(hint: str | None) -> tuple[str | None, RunReport]:
    try:
        return asyncio.run(run_story(hint=hint))
    except (OSError, psycopg.OperationalError) as error:
        pytest.skip(f"PostgreSQL not reachable: {error}")


def test_a_known_story_passes_reproducibly() -> None:
    """Run it twice: a QA verdict that only holds sometimes is not a verdict."""
    first_verdict, _ = execute("Created")
    second_verdict, report = execute("Created")

    assert first_verdict == second_verdict == Verdict.PASSED.value
    result = report.results[0]
    assert result.outcome is CriterionOutcome.MET
    assert result.model_derived is False, "a passing verdict must not rest on a model"


def test_the_story_fails_and_names_the_criterion_when_the_page_does_not_confirm_it() -> None:
    """The failure must say *which* promise was broken, and point at its plan step."""
    verdict, report = execute("Order dispatched")

    assert verdict == Verdict.FAILED.value
    result = report.results[0]
    assert result.criterion_id == "ac-created"
    assert result.outcome is CriterionOutcome.NOT_MET
    assert result.failure_kind is FailureKind.PRODUCT
    assert result.step_id == "assert-ac-created"

    document = to_document(report)
    criterion = document["criteria"][0]
    assert criterion["deterministic_observation"], "a reproducible failure must be recorded as one"
    assert criterion["root_cause_hypothesis"] is None, "nothing here came from a model"
    assert "Order dispatched" in render_markdown(report)


def test_an_unverifiable_criterion_ends_inconclusive_instead_of_blaming_the_product() -> None:
    """A criterion with nothing deterministic to check is a plan problem, not a defect.

    The agent did its job and the page is fine; the story simply never said how anyone
    would know. Reporting that as a product failure is how a QA system loses the right
    to be believed, so the run ends inconclusive and the report names no defect.
    """
    verdict, report = execute(None)

    assert verdict == Verdict.INCONCLUSIVE.value
    result = report.results[0]
    assert result.outcome is CriterionOutcome.UNVERIFIED
    assert result.model_derived is True
    assert report.defects == (), "an unverifiable criterion was reported as a defect"

    document = to_document(report)
    criterion = document["criteria"][0]
    assert criterion["deterministic_observation"] is None
    assert criterion["root_cause_hypothesis"], "a model claim must be recorded as one"
