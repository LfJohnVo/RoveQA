"""Project endpoints."""

from fastapi import APIRouter, status

from agentic_qa.application.commands.create_project import (
    CreateProjectCommand,
    create_project,
)
from agentic_qa.application.commands.create_run_policy import (
    CreateRunPolicyCommand,
    create_run_policy,
)
from agentic_qa.application.queries.get_project import get_project
from agentic_qa.interfaces.http.dependencies import UnitOfWorkDep
from agentic_qa.interfaces.http.schemas import (
    CreateProjectRequest,
    CreateRunPolicyRequest,
    ProjectResponse,
    RunPolicyResponse,
)

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def post_project(payload: CreateProjectRequest, uow: UnitOfWorkDep) -> ProjectResponse:
    project = await create_project(uow, CreateProjectCommand(name=payload.name))
    return ProjectResponse.from_domain(project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def read_project(project_id: str, uow: UnitOfWorkDep) -> ProjectResponse:
    return ProjectResponse.from_domain(await get_project(uow.projects, project_id))


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
            allow_file_uploads=payload.allow_file_uploads,
            upload_path_allowlist=tuple(payload.upload_path_allowlist),
            allow_downloads=payload.allow_downloads,
            max_depth=payload.max_depth,
            synthetic_data_allowed=payload.synthetic_data_allowed,
            set_as_project_default=payload.set_as_project_default,
        ),
    )
    return RunPolicyResponse.from_domain(policy)
