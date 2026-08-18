"""Project endpoints."""

from fastapi import APIRouter, status

from agentic_qa.application.commands.create_project import (
    CreateProjectCommand,
    create_project,
)
from agentic_qa.application.queries.get_project import get_project
from agentic_qa.interfaces.http.dependencies import UnitOfWorkDep
from agentic_qa.interfaces.http.schemas import CreateProjectRequest, ProjectResponse

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def post_project(payload: CreateProjectRequest, uow: UnitOfWorkDep) -> ProjectResponse:
    project = await create_project(uow, CreateProjectCommand(name=payload.name))
    return ProjectResponse.from_domain(project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def read_project(project_id: str, uow: UnitOfWorkDep) -> ProjectResponse:
    return ProjectResponse.from_domain(await get_project(uow.projects, project_id))
