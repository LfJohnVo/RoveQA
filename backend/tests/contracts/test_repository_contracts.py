"""Repository contract suite.

Every implementation of the ports must satisfy these behaviours identically. The
`repositories` fixture is parametrized, so adding an adapter adds coverage without
touching this file.
"""

import pytest

from agentic_qa.application.errors import AlreadyExistsError
from agentic_qa.domain.projects.project import Project
from agentic_qa.domain.qa.user_story import AcceptanceCriterion, UserStory
from agentic_qa.domain.runs.run import Run, RunStatus, Verdict
from tests.conftest import Repositories


def make_story(story_id: str, project_id: str) -> UserStory:
    return UserStory(
        story_id=story_id,
        project_id=project_id,
        actor="registered user",
        goal="reset the password",
        acceptance_criteria=(
            AcceptanceCriterion(criterion_id="ac-1", description="reset email is sent"),
        ),
    )


async def seed_project(repositories: Repositories, project_id: str = "p-1") -> Project:
    project = Project(project_id=project_id, name="Checkout")
    await repositories.projects.add(project)
    return project


class TestProjectRepository:
    async def test_round_trip(self, repositories: Repositories) -> None:
        await seed_project(repositories)
        stored = await repositories.projects.get("p-1")
        assert stored is not None
        assert stored.project_id == "p-1"
        assert stored.name == "Checkout"

    async def test_unknown_id_returns_none(self, repositories: Repositories) -> None:
        assert await repositories.projects.get("missing") is None

    async def test_duplicate_id_is_rejected(self, repositories: Repositories) -> None:
        await seed_project(repositories)
        with pytest.raises(AlreadyExistsError):
            await repositories.projects.add(Project(project_id="p-1", name="Other"))

    async def test_returned_entity_is_detached_from_the_store(
        self, repositories: Repositories
    ) -> None:
        await seed_project(repositories)
        first = await repositories.projects.get("p-1")
        assert first is not None
        first.rename("Mutated locally")

        second = await repositories.projects.get("p-1")
        assert second is not None
        assert second.name == "Checkout"


class TestStoryRepository:
    async def test_round_trip_preserves_criteria(self, repositories: Repositories) -> None:
        await seed_project(repositories)
        await repositories.stories.add(make_story("s-1", "p-1"))

        stored = await repositories.stories.get("s-1")
        assert stored is not None
        assert stored.actor == "registered user"
        assert [c.criterion_id for c in stored.acceptance_criteria] == ["ac-1"]

    async def test_duplicate_id_is_rejected(self, repositories: Repositories) -> None:
        await seed_project(repositories)
        await repositories.stories.add(make_story("s-1", "p-1"))
        with pytest.raises(AlreadyExistsError):
            await repositories.stories.add(make_story("s-1", "p-1"))

    async def test_listing_is_scoped_bounded_and_ordered(self, repositories: Repositories) -> None:
        await seed_project(repositories, "p-1")
        await seed_project(repositories, "p-2")
        for story_id in ("s-3", "s-1", "s-2"):
            await repositories.stories.add(make_story(story_id, "p-1"))
        await repositories.stories.add(make_story("s-9", "p-2"))

        listed = await repositories.stories.list_for_project("p-1", limit=2)
        assert [s.story_id for s in listed] == ["s-1", "s-2"]

        other = await repositories.stories.list_for_project("p-2", limit=10)
        assert [s.story_id for s in other] == ["s-9"]


class TestRunRepository:
    async def test_round_trip_preserves_status_and_verdict(
        self, repositories: Repositories
    ) -> None:
        await seed_project(repositories)
        run = Run(run_id="r-1", project_id="p-1")
        run.transition_to(RunStatus.QUEUED)
        run.transition_to(RunStatus.RUNNING)
        run.transition_to(RunStatus.COMPLETED, Verdict.PASSED)
        await repositories.runs.add(run)

        stored = await repositories.runs.get("r-1")
        assert stored is not None
        assert stored.status is RunStatus.COMPLETED
        assert stored.verdict is Verdict.PASSED

    async def test_draft_run_has_no_verdict(self, repositories: Repositories) -> None:
        await seed_project(repositories)
        await repositories.runs.add(Run(run_id="r-2", project_id="p-1"))

        stored = await repositories.runs.get("r-2")
        assert stored is not None
        assert stored.status is RunStatus.CREATED
        assert stored.verdict is None

    async def test_duplicate_id_is_rejected(self, repositories: Repositories) -> None:
        await seed_project(repositories)
        await repositories.runs.add(Run(run_id="r-1", project_id="p-1"))
        with pytest.raises(AlreadyExistsError):
            await repositories.runs.add(Run(run_id="r-1", project_id="p-1"))

    async def test_listing_a_project_returns_its_own_runs_newest_first(
        self, repositories: Repositories
    ) -> None:
        """Newest first because that is the order a person looks.

        The run you want is almost always the one that just finished, and a list that
        opens on the oldest makes the newest the hardest thing to reach.

        What this proves is the *total* order, not the timestamp: `now()` is fixed for a
        transaction, so three runs added here share one `created_at` and `run_id DESC`
        decides. That tiebreak is the half worth pinning anyway — in real use each run
        arrives in its own transaction and `created_at` separates them, while two runs
        created in the same millisecond are exactly the case that would otherwise come
        back in whatever order the query plan chose.
        """
        await seed_project(repositories)
        await seed_project(repositories, project_id="p-2")
        for index in range(3):
            await repositories.runs.add(Run(run_id=f"r-{index}", project_id="p-1"))
        await repositories.runs.add(Run(run_id="other", project_id="p-2"))

        listed = await repositories.runs.list_for_project("p-1", limit=50)

        assert [run.run_id for run in listed] == ["r-2", "r-1", "r-0"]

    async def test_the_listing_respects_its_limit(self, repositories: Repositories) -> None:
        await seed_project(repositories)
        for index in range(5):
            await repositories.runs.add(Run(run_id=f"r-{index}", project_id="p-1"))

        listed = await repositories.runs.list_for_project("p-1", limit=2)

        assert len(listed) == 2

    async def test_a_project_with_no_runs_lists_nothing(self, repositories: Repositories) -> None:
        await seed_project(repositories)
        assert await repositories.runs.list_for_project("p-1", limit=50) == []
