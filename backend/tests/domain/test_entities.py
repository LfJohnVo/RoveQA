"""Entity invariants for Project and UserStory."""

import pytest

from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.domain.projects.project import Project
from agentic_qa.domain.qa.user_story import AcceptanceCriterion, UserStory
from agentic_qa.domain.runs.run import Run


def criterion(criterion_id: str = "ac-1") -> AcceptanceCriterion:
    return AcceptanceCriterion(criterion_id=criterion_id, description="a visible outcome")


class TestProject:
    def test_trims_values(self) -> None:
        project = Project(project_id="  p-1  ", name="  Checkout  ")
        assert project.project_id == "p-1"
        assert project.name == "Checkout"

    @pytest.mark.parametrize("blank", ["", "   ", "\n"])
    def test_rejects_blank_name(self, blank: str) -> None:
        with pytest.raises(InvalidEntityError):
            Project(project_id="p-1", name=blank)

    def test_rejects_blank_id(self) -> None:
        with pytest.raises(InvalidEntityError):
            Project(project_id=" ", name="Checkout")

    def test_rejects_oversized_name(self) -> None:
        with pytest.raises(InvalidEntityError):
            Project(project_id="p-1", name="x" * 241)

    def test_rename_revalidates(self) -> None:
        project = Project(project_id="p-1", name="Checkout")
        with pytest.raises(InvalidEntityError):
            project.rename("  ")
        assert project.name == "Checkout"


class TestUserStory:
    def test_requires_at_least_one_criterion(self) -> None:
        with pytest.raises(InvalidEntityError):
            UserStory(
                story_id="s-1",
                project_id="p-1",
                actor="user",
                goal="reset password",
                acceptance_criteria=(),
            )

    def test_rejects_duplicate_criterion_ids(self) -> None:
        with pytest.raises(InvalidEntityError):
            UserStory(
                story_id="s-1",
                project_id="p-1",
                actor="user",
                goal="reset password",
                acceptance_criteria=(criterion("ac-1"), criterion("ac-1")),
            )

    def test_accepts_distinct_criteria_and_normalizes_lines(self) -> None:
        story = UserStory(
            story_id="s-1",
            project_id="p-1",
            actor="  user  ",
            goal="reset password",
            acceptance_criteria=(criterion("ac-1"), criterion("ac-2")),
            preconditions=("  account exists  ",),
        )
        assert story.actor == "user"
        assert story.preconditions == ("account exists",)
        assert [c.criterion_id for c in story.acceptance_criteria] == ["ac-1", "ac-2"]

    def test_rejects_blank_precondition(self) -> None:
        with pytest.raises(InvalidEntityError):
            UserStory(
                story_id="s-1",
                project_id="p-1",
                actor="user",
                goal="reset password",
                acceptance_criteria=(criterion(),),
                preconditions=("",),
            )

    def test_criterion_rejects_blank_description(self) -> None:
        with pytest.raises(InvalidEntityError):
            AcceptanceCriterion(criterion_id="ac-1", description="  ")


class TestRunIdentity:
    def test_rejects_blank_identifiers(self) -> None:
        with pytest.raises(InvalidEntityError):
            Run(run_id="", project_id="p-1")
        with pytest.raises(InvalidEntityError):
            Run(run_id="r-1", project_id="  ")
