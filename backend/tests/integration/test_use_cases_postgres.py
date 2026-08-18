"""End-to-end wiring: use case -> unit of work -> PostgreSQL adapter -> database.

The unit tests cover use-case logic against fakes; this proves the real chain
persists what those tests assert, including the durable idempotency record.
"""

from collections.abc import Callable

from agentic_qa.application.commands.create_project import (
    CreateProjectCommand,
    create_project,
)
from agentic_qa.application.commands.create_run_draft import (
    CreateRunDraftCommand,
    create_run_draft,
)
from agentic_qa.application.commands.create_story import CreateStoryCommand, create_story
from agentic_qa.application.ports.idempotency import RUN_CREATION_SCOPE
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.application.queries.get_project import get_project
from agentic_qa.domain.qa.user_story import AcceptanceCriterion
from agentic_qa.domain.runs.run import RunStatus

UnitOfWorkFactory = Callable[[], UnitOfWork]


async def test_project_story_and_run_draft_reach_the_database(
    postgres_unit_of_work_factory: UnitOfWorkFactory,
) -> None:
    async with postgres_unit_of_work_factory() as uow:
        project = await create_project(uow, CreateProjectCommand(name="Checkout"))

    async with postgres_unit_of_work_factory() as uow:
        story = await create_story(
            uow,
            CreateStoryCommand(
                project_id=project.project_id,
                actor="registered user",
                goal="reset the password",
                acceptance_criteria=(
                    AcceptanceCriterion(criterion_id="ac-1", description="reset email is sent"),
                    AcceptanceCriterion(criterion_id="ac-2", description="password is updated"),
                ),
                preconditions=("account exists",),
            ),
        )

    async with postgres_unit_of_work_factory() as uow:
        result = await create_run_draft(
            uow,
            CreateRunDraftCommand(project_id=project.project_id, idempotency_key="k-e2e"),
        )

    async with postgres_unit_of_work_factory() as uow:
        assert (await get_project(uow.projects, project.project_id)).name == "Checkout"

        stored_story = await uow.stories.get(story.story_id)
        assert stored_story is not None
        # Criterion order survives the round trip through the position column.
        assert [c.criterion_id for c in stored_story.acceptance_criteria] == ["ac-1", "ac-2"]
        assert stored_story.preconditions == ("account exists",)

        stored_run = await uow.runs.get(result.run.run_id)
        assert stored_run is not None
        assert stored_run.status is RunStatus.CREATED

        record = await uow.idempotency.get(RUN_CREATION_SCOPE, "k-e2e")
        assert record is not None
        assert record.resource_id == result.run.run_id
        assert record.created_at is not None


async def test_a_retried_request_reuses_the_committed_run(
    postgres_unit_of_work_factory: UnitOfWorkFactory,
) -> None:
    """Lost ACK against the real database: the retry must not create a second run."""
    async with postgres_unit_of_work_factory() as uow:
        project = await create_project(uow, CreateProjectCommand(name="Checkout"))

    command = CreateRunDraftCommand(project_id=project.project_id, idempotency_key="k-retry")

    async with postgres_unit_of_work_factory() as uow:
        first = await create_run_draft(uow, command)
    async with postgres_unit_of_work_factory() as uow:
        second = await create_run_draft(uow, command)

    assert second.replayed is True
    assert second.run.run_id == first.run.run_id
