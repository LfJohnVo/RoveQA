"""Use-case behaviour against fake ports."""

import pytest

from agentic_qa.application.commands.create_project import (
    CreateProjectCommand,
    create_project,
)
from agentic_qa.application.commands.create_run_draft import (
    CreateRunDraftCommand,
    create_run_draft,
)
from agentic_qa.application.commands.create_story import CreateStoryCommand, create_story
from agentic_qa.application.errors import NotFoundError
from agentic_qa.application.queries.get_project import get_project
from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.domain.qa.user_story import AcceptanceCriterion
from agentic_qa.domain.runs.run import RunStatus
from tests.conftest import Repositories, in_memory_repositories

CRITERIA = (AcceptanceCriterion(criterion_id="ac-1", description="reset email is sent"),)


@pytest.fixture
def repos() -> Repositories:
    return in_memory_repositories()


class TestCreateProject:
    async def test_persists_and_returns_the_project(self, repos: Repositories) -> None:
        project = await create_project(repos.projects, CreateProjectCommand(name="Checkout"))

        assert project.name == "Checkout"
        assert await repos.projects.get(project.project_id) is not None

    async def test_assigns_a_distinct_identity_per_call(self, repos: Repositories) -> None:
        first = await create_project(repos.projects, CreateProjectCommand(name="Checkout"))
        second = await create_project(repos.projects, CreateProjectCommand(name="Checkout"))

        assert first.project_id != second.project_id

    async def test_rejects_invalid_name_before_persisting(self, repos: Repositories) -> None:
        with pytest.raises(InvalidEntityError):
            await create_project(repos.projects, CreateProjectCommand(name="   "))


class TestGetProject:
    async def test_returns_the_project(self, repos: Repositories) -> None:
        created = await create_project(repos.projects, CreateProjectCommand(name="Checkout"))

        assert (await get_project(repos.projects, created.project_id)).name == "Checkout"

    async def test_raises_not_found_for_unknown_id(self, repos: Repositories) -> None:
        with pytest.raises(NotFoundError):
            await get_project(repos.projects, "ghost")


class TestCreateStory:
    async def test_persists_story_under_its_project(self, repos: Repositories) -> None:
        project = await create_project(repos.projects, CreateProjectCommand(name="Checkout"))

        story = await create_story(
            repos.projects,
            repos.stories,
            CreateStoryCommand(
                project_id=project.project_id,
                actor="registered user",
                goal="reset the password",
                acceptance_criteria=CRITERIA,
            ),
        )

        stored = await repos.stories.get(story.story_id)
        assert stored is not None
        assert stored.project_id == project.project_id
        assert [c.criterion_id for c in stored.acceptance_criteria] == ["ac-1"]

    async def test_rejects_unknown_project(self, repos: Repositories) -> None:
        with pytest.raises(NotFoundError):
            await create_story(
                repos.projects,
                repos.stories,
                CreateStoryCommand(
                    project_id="ghost",
                    actor="user",
                    goal="goal",
                    acceptance_criteria=CRITERIA,
                ),
            )

    async def test_rejects_story_without_criteria(self, repos: Repositories) -> None:
        project = await create_project(repos.projects, CreateProjectCommand(name="Checkout"))

        with pytest.raises(InvalidEntityError):
            await create_story(
                repos.projects,
                repos.stories,
                CreateStoryCommand(
                    project_id=project.project_id,
                    actor="user",
                    goal="goal",
                    acceptance_criteria=(),
                ),
            )


class TestCreateRunDraft:
    async def test_draft_is_created_but_not_started(self, repos: Repositories) -> None:
        project = await create_project(repos.projects, CreateProjectCommand(name="Checkout"))

        run = await create_run_draft(
            repos.projects, repos.runs, CreateRunDraftCommand(project_id=project.project_id)
        )

        stored = await repos.runs.get(run.run_id)
        assert stored is not None
        assert stored.status is RunStatus.CREATED
        assert stored.verdict is None

    async def test_rejects_unknown_project(self, repos: Repositories) -> None:
        with pytest.raises(NotFoundError):
            await create_run_draft(
                repos.projects, repos.runs, CreateRunDraftCommand(project_id="ghost")
            )
