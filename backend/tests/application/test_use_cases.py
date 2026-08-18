"""Use-case behaviour against fake ports.

Commands take a unit of work and own their commit (ADR 0010); the fake rolls back
for real, so a missing commit fails here too.
"""

import pytest

from agentic_qa.application.commands.create_project import (
    CreateProjectCommand,
    create_project,
)
from agentic_qa.application.commands.create_story import CreateStoryCommand, create_story
from agentic_qa.application.commands.start_run import StartRunCommand, start_run
from agentic_qa.application.errors import IdempotencyConflictError, NotFoundError
from agentic_qa.application.ports.idempotency import RUN_CREATION_SCOPE
from agentic_qa.application.queries.get_project import get_project
from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.domain.projects.project import Project
from agentic_qa.domain.qa.user_story import AcceptanceCriterion
from agentic_qa.domain.runs.run import RunStatus
from tests.fakes.repositories import InMemoryStore
from tests.fakes.unit_of_work import InMemoryUnitOfWork
from tests.fakes.workflows import FailingWorkflowGateway, RecordingWorkflowGateway

CRITERIA = (AcceptanceCriterion(criterion_id="ac-1", description="reset email is sent"),)


@pytest.fixture
def store() -> InMemoryStore:
    return InMemoryStore()


@pytest.fixture
def uow(store: InMemoryStore) -> InMemoryUnitOfWork:
    return InMemoryUnitOfWork(store)


@pytest.fixture
def workflows() -> RecordingWorkflowGateway:
    return RecordingWorkflowGateway()


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


class TestStartRun:
    async def test_run_is_queued_and_handed_to_the_workflow_engine(
        self, uow: InMemoryUnitOfWork, workflows: RecordingWorkflowGateway
    ) -> None:
        project = await seed_project(uow)

        async with uow:
            result = await start_run(
                uow,
                workflows,
                StartRunCommand(project_id=project.project_id, idempotency_key="k-1"),
            )

        assert result.replayed is False
        assert workflows.started == [(result.run.run_id, project.project_id)]
        async with uow:
            stored = await uow.runs.get(result.run.run_id)
            assert stored is not None
            assert stored.status is RunStatus.QUEUED
            assert stored.verdict is None

    async def test_rejects_unknown_project(
        self, uow: InMemoryUnitOfWork, workflows: RecordingWorkflowGateway
    ) -> None:
        async with uow:
            with pytest.raises(NotFoundError):
                await start_run(
                    uow, workflows, StartRunCommand(project_id="ghost", idempotency_key="k-1")
                )

        assert workflows.started == []

    async def test_repeating_the_same_request_replays_the_same_run(
        self,
        uow: InMemoryUnitOfWork,
        store: InMemoryStore,
        workflows: RecordingWorkflowGateway,
    ) -> None:
        """The lost-response case: the client never saw the ACK and retries."""
        project = await seed_project(uow)
        command = StartRunCommand(project_id=project.project_id, idempotency_key="k-lost")

        async with uow:
            first = await start_run(uow, workflows, command)
        async with uow:
            second = await start_run(uow, workflows, command)

        assert second.replayed is True
        assert second.run.run_id == first.run.run_id
        assert len(store.runs) == 1  # the retry created nothing new
        assert len(workflows.started) == 1  # and started no second workflow

    async def test_reusing_a_key_for_a_different_request_fails_typed(
        self, uow: InMemoryUnitOfWork, workflows: RecordingWorkflowGateway
    ) -> None:
        await seed_project(uow, "p-1")
        await seed_project(uow, "p-2")

        async with uow:
            await start_run(
                uow, workflows, StartRunCommand(project_id="p-1", idempotency_key="k-shared")
            )

        async with uow:
            with pytest.raises(IdempotencyConflictError):
                await start_run(
                    uow, workflows, StartRunCommand(project_id="p-2", idempotency_key="k-shared")
                )

    async def test_record_and_run_are_committed_together(
        self, uow: InMemoryUnitOfWork, workflows: RecordingWorkflowGateway
    ) -> None:
        project = await seed_project(uow)

        async with uow:
            command = StartRunCommand(project_id=project.project_id, idempotency_key="k-atomic")
            result = await start_run(uow, workflows, command)

        async with uow:
            record = await uow.idempotency.get(RUN_CREATION_SCOPE, "k-atomic")
            assert record is not None
            assert record.resource_id == result.run.run_id
            assert await uow.runs.get(record.resource_id) is not None

    async def test_a_failed_start_leaves_a_recoverable_queued_run(
        self, uow: InMemoryUnitOfWork, store: InMemoryStore
    ) -> None:
        """ADR 0010 ordering: the run is durable before the workflow is started.

        Losing the engine must not lose the run, and must not leave a workflow with no
        row behind it.
        """
        project = await seed_project(uow)

        with pytest.raises(RuntimeError):
            async with uow:
                await start_run(
                    uow,
                    FailingWorkflowGateway(),
                    StartRunCommand(project_id=project.project_id, idempotency_key="k-nostart"),
                )

        assert len(store.runs) == 1
        queued = next(iter(store.runs.values()))
        assert queued.status is RunStatus.QUEUED
