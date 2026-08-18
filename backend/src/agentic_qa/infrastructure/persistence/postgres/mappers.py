"""Explicit ORM <-> domain mapping.

ORM model != domain entity (docs/03). Mapping stays here so a schema change cannot
leak into the domain.
"""

from agentic_qa.domain.projects.project import Project
from agentic_qa.domain.qa.user_story import AcceptanceCriterion, UserStory
from agentic_qa.domain.runs.run import Run
from agentic_qa.infrastructure.persistence.postgres.models import (
    AcceptanceCriterionModel,
    ProjectModel,
    RunModel,
    UserStoryModel,
)


def project_to_domain(model: ProjectModel) -> Project:
    return Project(project_id=model.project_id, name=model.name)


def project_to_model(project: Project) -> ProjectModel:
    return ProjectModel(project_id=project.project_id, name=project.name)


def story_to_domain(model: UserStoryModel) -> UserStory:
    return UserStory(
        story_id=model.story_id,
        project_id=model.project_id,
        actor=model.actor,
        goal=model.goal,
        acceptance_criteria=tuple(
            AcceptanceCriterion(
                criterion_id=criterion.criterion_id,
                description=criterion.description,
                verification_hint=criterion.verification_hint,
            )
            for criterion in sorted(model.criteria, key=lambda c: c.position)
        ),
        preconditions=tuple(model.preconditions),
        forbidden_outcomes=tuple(model.forbidden_outcomes),
    )


def story_to_model(story: UserStory) -> UserStoryModel:
    return UserStoryModel(
        story_id=story.story_id,
        project_id=story.project_id,
        actor=story.actor,
        goal=story.goal,
        preconditions=list(story.preconditions),
        forbidden_outcomes=list(story.forbidden_outcomes),
        criteria=[
            AcceptanceCriterionModel(
                criterion_id=criterion.criterion_id,
                description=criterion.description,
                verification_hint=criterion.verification_hint,
                position=position,
            )
            for position, criterion in enumerate(story.acceptance_criteria)
        ],
    )


def run_to_domain(model: RunModel) -> Run:
    run = Run(run_id=model.run_id, project_id=model.project_id)
    # Status/verdict are restored, not replayed: the state machine guards live
    # transitions, while persistence rehydrates an already valid state.
    run.status = model.status
    run.verdict = model.verdict
    return run


def run_to_model(run: Run) -> RunModel:
    return RunModel(
        run_id=run.run_id,
        project_id=run.project_id,
        status=run.status,
        verdict=run.verdict,
    )
