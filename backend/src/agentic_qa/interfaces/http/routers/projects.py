"""Project endpoints."""

from typing import Annotated

from fastapi import APIRouter, Query, status

from agentic_qa.application.commands.create_environment import (
    CreateEnvironmentCommand,
    create_environment,
)
from agentic_qa.application.commands.create_project import (
    CreateProjectCommand,
    create_project,
)
from agentic_qa.application.commands.create_run_policy import (
    CreateRunPolicyCommand,
    create_run_policy,
)
from agentic_qa.application.queries.get_project import get_project
from agentic_qa.interfaces.http.authorisation import AuthorisedDep
from agentic_qa.interfaces.http.dependencies import UnitOfWorkDep
from agentic_qa.interfaces.http.schemas import (
    CreateEnvironmentRequest,
    CreateProjectRequest,
    CreateRunPolicyRequest,
    EnvironmentResponse,
    ProjectResponse,
    RunPolicyResponse,
)

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

DEFAULT_PROJECT_PAGE_SIZE = 50
MAX_PROJECT_PAGE_SIZE = 200


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def post_project(payload: CreateProjectRequest, uow: UnitOfWorkDep) -> ProjectResponse:
    project = await create_project(uow, CreateProjectCommand(name=payload.name))
    return ProjectResponse.from_domain(project)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    uow: UnitOfWorkDep,
    token: AuthorisedDep,
    limit: Annotated[int, Query(ge=1, le=MAX_PROJECT_PAGE_SIZE)] = DEFAULT_PROJECT_PAGE_SIZE,
) -> list[ProjectResponse]:
    """This token's projects. Bounded by construction, and filtered by who is asking.

    The path names no project, so the generic scope check has nothing to compare against
    — a listing across projects is exactly the shape that check cannot decide (ADR 0020).
    Filtering here is what stops a token for one team's application from enumerating
    every other application this deployment tests.
    """
    projects = await uow.projects.list(limit=limit)
    return [
        ProjectResponse.from_domain(project)
        for project in projects
        if token.covers(project.project_id)
    ]


@router.get("/{project_id}", response_model=ProjectResponse)
async def read_project(project_id: str, uow: UnitOfWorkDep) -> ProjectResponse:
    return ProjectResponse.from_domain(await get_project(uow.projects, project_id))


@router.post(
    "/{project_id}/environments",
    response_model=EnvironmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_environment(
    project_id: str, payload: CreateEnvironmentRequest, uow: UnitOfWorkDep
) -> EnvironmentResponse:
    """Create a deployment of this project's application.

    An environment is what a session hangs off, and until now one could only be made
    from a test. That made the whole session feature unreachable through the API: you
    could register a session for an environment that no endpoint could create.
    """
    environment = await create_environment(
        uow,
        CreateEnvironmentCommand(
            project_id=project_id,
            name=payload.name,
            default_run_policy_id=payload.default_run_policy_id,
        ),
    )
    return EnvironmentResponse.from_domain(environment)


@router.get("/{project_id}/environments", response_model=list[EnvironmentResponse])
async def list_environments(project_id: str, uow: UnitOfWorkDep) -> list[EnvironmentResponse]:
    """Unbounded on purpose: a project has staging and production, not thousands."""
    environments = await uow.environments.list_for_project(project_id)
    return [EnvironmentResponse.from_domain(environment) for environment in environments]


@router.post(
    "/{project_id}/run-policies",
    response_model=RunPolicyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_run_policy(
    project_id: str, payload: CreateRunPolicyRequest, uow: UnitOfWorkDep
) -> RunPolicyResponse:
    """Create an immutable run policy; changing rules means creating a new one."""
    policy = await create_run_policy(
        uow,
        CreateRunPolicyCommand(
            project_id=project_id,
            allowed_origins=tuple(payload.allowed_origins),
            max_duration_seconds=payload.max_duration_seconds,
            max_actions=payload.max_actions,
            max_model_calls=payload.max_model_calls,
            destructive_actions=payload.destructive_actions,
            consent=payload.consent,
            allow_file_uploads=payload.allow_file_uploads,
            upload_path_allowlist=tuple(payload.upload_path_allowlist),
            allow_downloads=payload.allow_downloads,
            max_depth=payload.max_depth,
            synthetic_data_allowed=payload.synthetic_data_allowed,
            set_as_project_default=payload.set_as_project_default,
        ),
    )
    return RunPolicyResponse.from_domain(policy)
