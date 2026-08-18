"""End-to-end wiring: use case -> port -> PostgreSQL adapter -> database.

The unit tests cover use-case logic against fakes; this proves the real chain
persists what those tests assert.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from agentic_qa.application.commands.create_project import (
    CreateProjectCommand,
    create_project,
)
from agentic_qa.application.commands.create_run_draft import (
    CreateRunDraftCommand,
    create_run_draft,
)
from agentic_qa.application.commands.create_story import CreateStoryCommand, create_story
from agentic_qa.application.queries.get_project import get_project
from agentic_qa.domain.qa.user_story import AcceptanceCriterion
from agentic_qa.domain.runs.run import RunStatus
from agentic_qa.infrastructure.persistence.postgres.repositories import (
    PostgresProjectRepository,
    PostgresRunRepository,
    PostgresStoryRepository,
)


async def test_project_story_and_run_draft_reach_the_database(
    postgres_session: AsyncSession,
) -> None:
    projects = PostgresProjectRepository(postgres_session)
    stories = PostgresStoryRepository(postgres_session)
    runs = PostgresRunRepository(postgres_session)

    project = await create_project(projects, CreateProjectCommand(name="Checkout"))
    story = await create_story(
        projects,
        stories,
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
    run = await create_run_draft(
        projects, runs, CreateRunDraftCommand(project_id=project.project_id)
    )
    await postgres_session.flush()

    assert (await get_project(projects, project.project_id)).name == "Checkout"

    stored_story = await stories.get(story.story_id)
    assert stored_story is not None
    # Criterion order survives the round trip through the position column.
    assert [c.criterion_id for c in stored_story.acceptance_criteria] == ["ac-1", "ac-2"]
    assert stored_story.preconditions == ("account exists",)

    stored_run = await runs.get(run.run_id)
    assert stored_run is not None
    assert stored_run.status is RunStatus.CREATED

    rows = await postgres_session.execute(
        text(
            "SELECT criterion_id FROM acceptance_criteria WHERE story_id = :sid ORDER BY position"
        ),
        {"sid": story.story_id},
    )
    assert [row[0] for row in rows] == ["ac-1", "ac-2"]
