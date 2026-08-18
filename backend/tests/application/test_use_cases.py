"""Use-case behaviour against fake ports.

Commands take a unit of work and own their commit (ADR 0010); the fake rolls back
for real, so a missing commit fails here too.
"""

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
from agentic_qa.application.errors import IdempotencyConflictError, NotFoundError
from agentic_qa.application.ports.idempotency import RUN_CREATION_SCOPE
from agentic_qa.application.queries.get_project import get_project
from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.domain.projects.project import Project
from agentic_qa.domain.qa.user_story import AcceptanceCriterion
from agentic_qa.domain.runs.run import RunStatus
from tests.fakes.repositories import InMemoryStore
from tests.fakes.unit_of_work import InMemoryUnitOfWork

CRITERIA = (AcceptanceCriterion(criterion_id="ac-1", description="reset email is sent"),)


@pytest.fixture
def store() -> InMemoryStore:
    return InMemoryStore()


@pytest.fixture
def uow(store: InMemoryStore) -> InMemoryUnitOfWork:
    return InMemoryUnitOfWork(store)


async def seed_project(uow: InMemoryUnitOfWork, project_id: str = "p-1") -> Project:
    project = Project(project_id=project_id, name="Checkout")
    async with uow:
        await uow.projects.add(project)
        await uow.commit()
    return project


class TestCreateProject:
    async def test_persists_and_returns_the_project(self, uow: InMemoryUnitOfWork) -> None:
        async with uow:
            project = await create_project(uow, CreateProjectCommand(name="Checkout"))

        async with uow:
            assert await uow.projects.get(project.project_id) is not None

    async def test_assigns_a_distinct_identity_per_call(self, uow: InMemoryUnitOfWork) -> None:
        async with uow:
            first = await create_project(uow, CreateProjectCommand(name="Checkout"))
        async with uow:
            second = await create_project(uow, CreateProjectCommand(name="Checkout"))

        assert first.project_id != second.project_id

    async def test_rejects_invalid_name_before_persisting(self, uow: InMemoryUnitOfWork) -> None:
        with pytest.raises(InvalidEntityError):
            async with uow:
                await create_project(uow, CreateProjectCommand(name="   "))


class TestGetProject:
    async def test_returns_the_project(self, uow: InMemoryUnitOfWork) -> None:
        created = await seed_project(uow)

        async with uow:
            assert (await get_project(uow.projects, created.project_id)).name == "Checkout"

    async def test_raises_not_found_for_unknown_id(self, uow: InMemoryUnitOfWork) -> None:
        async with uow:
            with pytest.raises(NotFoundError):
                await get_project(uow.projects, "ghost")


class TestCreateStory:
    async def test_persists_story_under_its_project(self, uow: InMemoryUnitOfWork) -> None:
        project = await seed_project(uow)

        async with uow:
            story = await create_story(
                uow,
                CreateStoryCommand(
                    project_id=project.project_id,
                    actor="registered user",
                    goal="reset the password",
                    acceptance_criteria=CRITERIA,
                ),
            )

        async with uow:
            stored = await uow.stories.get(story.story_id)
            assert stored is not None
            assert stored.project_id == project.project_id
            assert [c.criterion_id for c in stored.acceptance_criteria] == ["ac-1"]

    async def test_rejects_unknown_project(self, uow: InMemoryUnitOfWork) -> None:
        async with uow:
            with pytest.raises(NotFoundError):
                await create_story(
                    uow,
                    CreateStoryCommand(
                        project_id="ghost",
                        actor="user",
                        goal="goal",
                        acceptance_criteria=CRITERIA,
                    ),
                )

    async def test_rejects_story_without_criteria(self, uow: InMemoryUnitOfWork) -> None:
        project = await seed_project(uow)

        async with uow:
            with pytest.raises(InvalidEntityError):
                await create_story(
                    uow,
                    CreateStoryCommand(
                        project_id=project.project_id,
                        actor="user",
                        goal="goal",
                        acceptance_criteria=(),
                    ),
                )


class TestCreateRunDraft:
    async def test_draft_is_created_but_not_started(self, uow: InMemoryUnitOfWork) -> None:
        project = await seed_project(uow)

        async with uow:
            result = await create_run_draft(
                uow, CreateRunDraftCommand(project_id=project.project_id, idempotency_key="k-1")
            )

        assert result.replayed is False
        async with uow:
            stored = await uow.runs.get(result.run.run_id)
            assert stored is not None
            assert stored.status is RunStatus.CREATED
            assert stored.verdict is None

    async def test_rejects_unknown_project(self, uow: InMemoryUnitOfWork) -> None:
        async with uow:
            with pytest.raises(NotFoundError):
                await create_run_draft(
                    uow, CreateRunDraftCommand(project_id="ghost", idempotency_key="k-1")
                )

    async def test_repeating_the_same_request_replays_the_same_run(
        self, uow: InMemoryUnitOfWork, store: InMemoryStore
    ) -> None:
        """The lost-response case: the client never saw the ACK and retries."""
        project = await seed_project(uow)
        command = CreateRunDraftCommand(project_id=project.project_id, idempotency_key="k-lost")

        async with uow:
            first = await create_run_draft(uow, command)
        async with uow:
            second = await create_run_draft(uow, command)

        assert second.replayed is True
        assert second.run.run_id == first.run.run_id
        assert len(store.runs) == 1  # the retry created nothing new

    async def test_reusing_a_key_for_a_different_request_fails_typed(
        self, uow: InMemoryUnitOfWork
    ) -> None:
        await seed_project(uow, "p-1")
        await seed_project(uow, "p-2")

        async with uow:
            await create_run_draft(
                uow, CreateRunDraftCommand(project_id="p-1", idempotency_key="k-shared")
            )

        async with uow:
            with pytest.raises(IdempotencyConflictError):
                await create_run_draft(
                    uow, CreateRunDraftCommand(project_id="p-2", idempotency_key="k-shared")
                )

    async def test_record_and_run_are_committed_together(self, uow: InMemoryUnitOfWork) -> None:
        project = await seed_project(uow)

        async with uow:
            command = CreateRunDraftCommand(
                project_id=project.project_id, idempotency_key="k-atomic"
            )
            result = await create_run_draft(uow, command)

        async with uow:
            record = await uow.idempotency.get(RUN_CREATION_SCOPE, "k-atomic")
            assert record is not None
            assert record.resource_id == result.run.run_id
            assert await uow.runs.get(record.resource_id) is not None
