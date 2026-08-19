"""Transport DTOs.

Separate from domain entities on purpose (docs/03): a schema change here must never
be able to reshape the domain, and response models are validated at runtime so a
malformed 2xx fails loudly instead of becoming a fake success.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from agentic_qa.application.ports.events import RunEvent
from agentic_qa.domain.projects.project import Project
from agentic_qa.domain.projects.run_policy import RunPolicy
from agentic_qa.domain.qa.user_story import UserStory
from agentic_qa.domain.runs.run import Run, RunStatus, Verdict


class CreateProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=240)


class ProjectResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    name: str

    @classmethod
    def from_domain(cls, project: Project) -> "ProjectResponse":
        return cls(project_id=project.project_id, name=project.name)


class CreateRunPolicyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allowed_origins: list[str] = Field(min_length=1)
    """RFC 6454 origins; there is no safe empty allowlist, so at least one is required."""

    max_duration_seconds: int = Field(ge=1, le=172_800)
    max_actions: int = Field(ge=1, le=10_000)
    max_model_calls: int = Field(ge=0, le=10_000)
    destructive_actions: bool = False
    allow_file_uploads: bool = False
    upload_path_allowlist: list[str] = Field(default_factory=list)
    allow_downloads: bool = False
    max_depth: int | None = Field(default=None, ge=0)
    synthetic_data_allowed: bool = True
    set_as_project_default: bool = False


class RunPolicyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_id: str
    project_id: str
    allowed_origins: list[str]
    max_duration_seconds: int
    max_actions: int
    max_model_calls: int
    destructive_actions: bool
    allow_file_uploads: bool
    upload_path_allowlist: list[str]
    allow_downloads: bool
    max_depth: int | None
    synthetic_data_allowed: bool

    @classmethod
    def from_domain(cls, policy: RunPolicy) -> "RunPolicyResponse":
        return cls(
            policy_id=policy.policy_id,
            project_id=policy.project_id,
            allowed_origins=list(policy.allowed_origins),
            max_duration_seconds=policy.max_duration_seconds,
            max_actions=policy.max_actions,
            max_model_calls=policy.max_model_calls,
            destructive_actions=policy.destructive_actions,
            allow_file_uploads=policy.allow_file_uploads,
            upload_path_allowlist=list(policy.upload_path_allowlist),
            allow_downloads=policy.allow_downloads,
            max_depth=policy.max_depth,
            synthetic_data_allowed=policy.synthetic_data_allowed,
        )


class CreateRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(min_length=1, max_length=200)
    environment_id: str | None = Field(default=None, min_length=1, max_length=200)
    run_policy_id: str | None = Field(default=None, min_length=1, max_length=200)
    plan_id: str | None = Field(default=None, min_length=1, max_length=200)
    plan_version: str | None = Field(default=None, min_length=1, max_length=100)
    """Without a version the latest is resolved once, at creation, and pinned onto
    the run: what a run is judged by must not change while it runs."""


class RunEventResponse(BaseModel):
    """Matches the envelope in docs/12 and contracts/run-event.schema.json."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    run_id: str
    sequence: int
    type: str
    occurred_at: datetime
    payload: dict[str, Any]
    request_id: str | None

    @classmethod
    def from_domain(cls, event: RunEvent) -> "RunEventResponse":
        return cls(
            event_id=event.event_id,
            run_id=event.run_id,
            sequence=event.sequence,
            type=event.type,
            occurred_at=event.occurred_at,
            payload=event.payload,
            request_id=event.request_id,
        )


class RunEventPageResponse(BaseModel):
    """`next_after` is the cursor to resume from; empty events means fully caught up."""

    model_config = ConfigDict(extra="forbid")

    events: list[RunEventResponse]
    next_after: int


class RunAcceptedResponse(BaseModel):
    """A lifecycle command was accepted; the durable status changes when it applies."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    accepted: str


class RunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    project_id: str
    status: RunStatus
    verdict: Verdict | None
    run_policy_id: str | None
    environment_id: str | None
    plan_id: str | None = None
    plan_version: str | None = None

    @classmethod
    def from_domain(cls, run: Run) -> "RunResponse":
        return cls(
            run_id=run.run_id,
            project_id=run.project_id,
            status=run.status,
            verdict=run.verdict,
            run_policy_id=run.run_policy_id,
            environment_id=run.environment_id,
            plan_id=run.plan_id,
            plan_version=run.plan_version,
        )


class AcceptanceCriterionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    criterion_id: str = Field(min_length=1, max_length=200)
    """Authored, not generated: plans, results and findings all reference it."""

    description: str = Field(min_length=1, max_length=4000)
    verification_hint: str | None = Field(default=None, min_length=1, max_length=1000)
    """A literal the page must contain. Its presence is what makes a criterion
    verifiable deterministically instead of by a model's opinion."""


class CreateStoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor: str = Field(min_length=1, max_length=500)
    goal: str = Field(min_length=1, max_length=1000)
    acceptance_criteria: list[AcceptanceCriterionPayload] = Field(min_length=1, max_length=100)
    preconditions: list[str] = Field(default_factory=list, max_length=50)
    forbidden_outcomes: list[str] = Field(default_factory=list, max_length=50)


class StoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    story_id: str
    project_id: str
    actor: str
    goal: str
    acceptance_criteria: list[AcceptanceCriterionPayload]

    @classmethod
    def from_domain(cls, story: UserStory) -> "StoryResponse":
        return cls(
            story_id=story.story_id,
            project_id=story.project_id,
            actor=story.actor,
            goal=story.goal,
            acceptance_criteria=[
                AcceptanceCriterionPayload(
                    criterion_id=criterion.criterion_id,
                    description=criterion.description,
                    verification_hint=criterion.verification_hint,
                )
                for criterion in story.acceptance_criteria
            ],
        )


class CompilePlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_policy_id: str | None = Field(default=None, min_length=1, max_length=200)
    environment_id: str | None = Field(default=None, min_length=1, max_length=200)
    plan_id: str | None = Field(default=None, min_length=1, max_length=200)
    """Supply an existing plan's id to publish a new version of it."""

    max_actions: int | None = Field(default=None, ge=1, le=10_000)
    max_duration_seconds: int | None = Field(default=None, ge=1, le=172_800)
    max_model_calls: int | None = Field(default=None, ge=0, le=10_000)


class ImportPlanRequest(BaseModel):
    """A portable plan document submitted directly, as the CLI does."""

    model_config = ConfigDict(extra="forbid")

    plan: dict[str, Any] = Field()
    plan_id: str | None = Field(default=None, min_length=1, max_length=200)
    """Absent means a new plan identity is minted. Identity is never derived from the
    content, or two unrelated plans with the same steps would merge into one."""

    plan_version: str | None = Field(default=None, min_length=1, max_length=100)
    """Absent means the content hash, which is what makes re-submitting the same
    document idempotent (docs/12)."""
