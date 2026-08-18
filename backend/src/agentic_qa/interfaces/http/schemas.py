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


class CreateRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(min_length=1, max_length=200)


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

    @classmethod
    def from_domain(cls, run: Run) -> "RunResponse":
        return cls(
            run_id=run.run_id,
            project_id=run.project_id,
            status=run.status,
            verdict=run.verdict,
        )
