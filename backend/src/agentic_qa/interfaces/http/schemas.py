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

    @classmethod
    def from_domain(cls, run: Run) -> "RunResponse":
        return cls(
            run_id=run.run_id,
            project_id=run.project_id,
            status=run.status,
            verdict=run.verdict,
            run_policy_id=run.run_policy_id,
            environment_id=run.environment_id,
        )
