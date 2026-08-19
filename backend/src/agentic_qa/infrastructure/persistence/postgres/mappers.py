"""Explicit ORM <-> domain mapping.

ORM model != domain entity (docs/03). Mapping stays here so a schema change cannot
leak into the domain.
"""

from agentic_qa.domain.browser.evidence import EvidenceRef
from agentic_qa.domain.projects.environment import Environment
from agentic_qa.domain.projects.project import Project
from agentic_qa.domain.projects.run_policy import RunPolicy
from agentic_qa.domain.qa.test_plan import (
    MemoryPolicy,
    MetadataValue,
    PlanBudget,
    PlanMode,
    PlanPriority,
    PlanStep,
    PlanStepType,
    TestPlan,
)
from agentic_qa.domain.qa.user_story import AcceptanceCriterion, UserStory
from agentic_qa.domain.qa.verification import CriterionOutcome, CriterionResult, FailureKind
from agentic_qa.domain.runs.run import Run
from agentic_qa.infrastructure.persistence.postgres.models import (
    AcceptanceCriterionModel,
    ArtifactModel,
    CriterionResultModel,
    EnvironmentModel,
    ProjectModel,
    RunModel,
    RunPolicyModel,
    TestPlanModel,
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
        plan_id=model.plan_id,
        plan_version=model.plan_version,
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
        plan_id=run.plan_id,
        plan_version=run.plan_version,
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


def plan_to_domain(model: TestPlanModel) -> TestPlan:
    return TestPlan(
        plan_id=model.plan_id,
        plan_version=model.plan_version,
        project_id=model.project_id,
        name=model.name,
        mode=PlanMode(model.mode),
        plan_steps=tuple(_plan_step_to_domain(step) for step in model.plan_steps),
        source_story_id=model.source_story_id,
        environment_id=model.environment_id,
        run_policy_id=model.run_policy_id,
        budget=_budget_to_domain(model.budget),
        description=model.description,
        priority=PlanPriority(model.priority) if model.priority else None,
        memory_policy=MemoryPolicy(model.memory_policy),
        metadata=tuple((key, _metadata_value(value)) for key, value in model.plan_metadata.items()),
    )


def plan_to_model(plan: TestPlan) -> TestPlanModel:
    return TestPlanModel(
        plan_id=plan.plan_id,
        plan_version=plan.plan_version,
        project_id=plan.project_id,
        source_story_id=plan.source_story_id,
        environment_id=plan.environment_id,
        run_policy_id=plan.run_policy_id,
        name=plan.name,
        description=plan.description,
        mode=plan.mode.value,
        priority=plan.priority.value if plan.priority else None,
        memory_policy=plan.memory_policy.value,
        budget=_budget_to_column(plan.budget),
        plan_steps=[_plan_step_to_column(step) for step in plan.plan_steps],
        plan_metadata=dict(plan.metadata),
    )


def _plan_step_to_domain(raw: dict[str, object]) -> PlanStep:
    criterion = raw.get("criterion_id")
    return PlanStep(
        step_id=str(raw["step_id"]),
        type=PlanStepType(str(raw["type"])),
        description=str(raw["description"]),
        criterion_id=str(criterion) if criterion is not None else None,
        critical=bool(raw.get("critical", False)),
    )


def _plan_step_to_column(step: PlanStep) -> dict[str, object]:
    return {
        "step_id": step.step_id,
        "type": step.type.value,
        "description": step.description,
        "criterion_id": step.criterion_id,
        "critical": step.critical,
    }


def _budget_to_domain(raw: dict[str, object] | None) -> PlanBudget | None:
    if not raw:
        return None
    return PlanBudget(
        max_actions=_optional_int(raw.get("max_actions")),
        max_duration_seconds=_optional_int(raw.get("max_duration_seconds")),
        max_model_calls=_optional_int(raw.get("max_model_calls")),
    )


def _budget_to_column(budget: PlanBudget | None) -> dict[str, int] | None:
    if budget is None:
        return None
    fields = {
        "max_actions": budget.max_actions,
        "max_duration_seconds": budget.max_duration_seconds,
        "max_model_calls": budget.max_model_calls,
    }
    return {name: value for name, value in fields.items() if value is not None}


def _optional_int(value: object) -> int | None:
    return int(value) if isinstance(value, int) else None


def _metadata_value(value: object) -> MetadataValue:
    """JSONB gives back exactly the scalar types the contract allows."""
    if value is None or isinstance(value, str | bool | int | float):
        return value
    # Defensive: a value written by an older/foreign writer is kept readable rather
    # than crashing the read, but it stops being a silent type change.
    return str(value)


def criterion_result_to_domain(model: CriterionResultModel) -> CriterionResult:
    return CriterionResult(
        criterion_id=model.criterion_id,
        outcome=CriterionOutcome(model.outcome),
        observation=model.observation,
        failure_kind=FailureKind(model.failure_kind) if model.failure_kind else None,
        model_derived=model.model_derived,
        evidence_refs=tuple(model.evidence_refs),
        step_id=model.step_id,
        model_invocation_id=model.model_invocation_id,
        model_name=model.model_name,
        prompt_version=model.prompt_version,
    )


def criterion_result_to_model(run_id: str, result: CriterionResult) -> CriterionResultModel:
    return CriterionResultModel(
        run_id=run_id,
        criterion_id=result.criterion_id,
        step_id=result.step_id,
        outcome=result.outcome.value,
        failure_kind=result.failure_kind.value if result.failure_kind else None,
        observation=result.observation,
        model_derived=result.model_derived,
        evidence_refs=list(result.evidence_refs),
        model_invocation_id=result.model_invocation_id,
        model_name=result.model_name,
        prompt_version=result.prompt_version,
    )


def artifact_to_domain(model: ArtifactModel) -> EvidenceRef:
    return EvidenceRef(
        artifact_id=model.artifact_id,
        run_id=model.run_id,
        evidence_set_id=model.evidence_set_id,
        kind=model.kind,
        relative_path=model.relative_path,
        sha256=model.sha256,
        size_bytes=model.size_bytes,
        captured_at=model.captured_at,
        step_id=model.step_id,
    )


def artifact_to_model(ref: EvidenceRef) -> ArtifactModel:
    return ArtifactModel(
        artifact_id=ref.artifact_id,
        run_id=ref.run_id,
        evidence_set_id=ref.evidence_set_id,
        kind=ref.kind,
        relative_path=ref.relative_path,
        sha256=ref.sha256,
        size_bytes=ref.size_bytes,
        step_id=ref.step_id,
        captured_at=ref.captured_at,
    )
