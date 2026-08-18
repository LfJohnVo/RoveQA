"""Explicit ORM <-> domain mapping.

ORM model != domain entity (docs/03). Mapping stays here so a schema change cannot
leak into the domain.
"""

from agentic_qa.domain.projects.environment import Environment
from agentic_qa.domain.projects.project import Project
from agentic_qa.domain.projects.run_policy import RunPolicy
from agentic_qa.domain.qa.user_story import AcceptanceCriterion, UserStory
from agentic_qa.domain.runs.run import Run
from agentic_qa.infrastructure.persistence.postgres.models import (
    AcceptanceCriterionModel,
    EnvironmentModel,
    ProjectModel,
    RunModel,
    RunPolicyModel,
    UserStoryModel,
)


def project_to_domain(model: ProjectModel) -> Project:
    return Project(
        project_id=model.project_id,
        name=model.name,
        default_run_policy_id=model.default_run_policy_id,
    )


def project_to_model(project: Project) -> ProjectModel:
    return ProjectModel(
        project_id=project.project_id,
        name=project.name,
        default_run_policy_id=project.default_run_policy_id,
    )


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
    run = Run(
        run_id=model.run_id,
        project_id=model.project_id,
        run_policy_id=model.run_policy_id,
        environment_id=model.environment_id,
    )
    # Status/verdict are restored, not replayed: the state machine guards live
    # transitions, while persistence rehydrates an already valid state.
    run.status = model.status
    run.verdict = model.verdict
    return run


def run_to_model(run: Run) -> RunModel:
    return RunModel(
        run_id=run.run_id,
        project_id=run.project_id,
        run_policy_id=run.run_policy_id,
        environment_id=run.environment_id,
        status=run.status,
        verdict=run.verdict,
    )


def policy_to_domain(model: RunPolicyModel) -> RunPolicy:
    return RunPolicy(
        policy_id=model.policy_id,
        project_id=model.project_id,
        allowed_origins=tuple(model.allowed_origins),
        max_duration_seconds=model.max_duration_seconds,
        max_actions=model.max_actions,
        max_model_calls=model.max_model_calls,
        destructive_actions=model.destructive_actions,
        allow_file_uploads=model.allow_file_uploads,
        upload_path_allowlist=tuple(model.upload_path_allowlist),
        allow_downloads=model.allow_downloads,
        max_depth=model.max_depth,
        synthetic_data_allowed=model.synthetic_data_allowed,
    )


def policy_to_model(policy: RunPolicy) -> RunPolicyModel:
    return RunPolicyModel(
        policy_id=policy.policy_id,
        project_id=policy.project_id,
        allowed_origins=list(policy.allowed_origins),
        upload_path_allowlist=list(policy.upload_path_allowlist),
        destructive_actions=policy.destructive_actions,
        allow_file_uploads=policy.allow_file_uploads,
        allow_downloads=policy.allow_downloads,
        synthetic_data_allowed=policy.synthetic_data_allowed,
        max_duration_seconds=policy.max_duration_seconds,
        max_actions=policy.max_actions,
        max_model_calls=policy.max_model_calls,
        max_depth=policy.max_depth,
    )


def environment_to_domain(model: EnvironmentModel) -> Environment:
    return Environment(
        environment_id=model.environment_id,
        project_id=model.project_id,
        name=model.name,
        default_run_policy_id=model.default_run_policy_id,
    )


def environment_to_model(environment: Environment) -> EnvironmentModel:
    return EnvironmentModel(
        environment_id=environment.environment_id,
        project_id=environment.project_id,
        name=environment.name,
        default_run_policy_id=environment.default_run_policy_id,
    )
