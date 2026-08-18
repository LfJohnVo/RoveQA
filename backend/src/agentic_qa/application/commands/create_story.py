"""Create a user story for an existing project."""

from dataclasses import dataclass, field
from uuid import uuid4

from agentic_qa.application.errors import NotFoundError
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.domain.qa.user_story import AcceptanceCriterion, UserStory


@dataclass(frozen=True)
class CreateStoryCommand:
    project_id: str
    actor: str
    goal: str
    # Criterion ids are authored, not generated: plans and findings reference them.
    acceptance_criteria: tuple[AcceptanceCriterion, ...]
    preconditions: tuple[str, ...] = field(default=())
    forbidden_outcomes: tuple[str, ...] = field(default=())


async def create_story(uow: UnitOfWork, command: CreateStoryCommand) -> UserStory:
    if await uow.projects.get(command.project_id) is None:
        raise NotFoundError("project", command.project_id)

    story = UserStory(
        story_id=str(uuid4()),
        project_id=command.project_id,
        actor=command.actor,
        goal=command.goal,
        acceptance_criteria=command.acceptance_criteria,
        preconditions=command.preconditions,
        forbidden_outcomes=command.forbidden_outcomes,
    )
    await uow.stories.add(story)
    await uow.commit()
    return story
