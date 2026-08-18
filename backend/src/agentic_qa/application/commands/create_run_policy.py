"""Create a run policy, optionally making it the project default.

Policies are immutable: there is no update command, so a run that recorded its policy
can always be audited against the exact rules it ran under. Changing the rules means
creating a new policy and pointing the default at it.
"""

from dataclasses import dataclass, field
from uuid import uuid4

from agentic_qa.application.errors import NotFoundError
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.domain.projects.run_policy import RunPolicy


@dataclass(frozen=True)
class CreateRunPolicyCommand:
    project_id: str
    allowed_origins: tuple[str, ...]
    max_duration_seconds: int
    max_actions: int
    max_model_calls: int
    destructive_actions: bool = False
    allow_file_uploads: bool = False
    upload_path_allowlist: tuple[str, ...] = field(default=())
    allow_downloads: bool = False
    max_depth: int | None = None
    synthetic_data_allowed: bool = True
    set_as_project_default: bool = False


async def create_run_policy(uow: UnitOfWork, command: CreateRunPolicyCommand) -> RunPolicy:
    project = await uow.projects.get(command.project_id)
    if project is None:
        raise NotFoundError("project", command.project_id)

    policy = RunPolicy(
        policy_id=str(uuid4()),
        project_id=command.project_id,
        allowed_origins=command.allowed_origins,
        max_duration_seconds=command.max_duration_seconds,
        max_actions=command.max_actions,
        max_model_calls=command.max_model_calls,
        destructive_actions=command.destructive_actions,
        allow_file_uploads=command.allow_file_uploads,
        upload_path_allowlist=command.upload_path_allowlist,
        allow_downloads=command.allow_downloads,
        max_depth=command.max_depth,
        synthetic_data_allowed=command.synthetic_data_allowed,
    )
    await uow.policies.add(policy)

    if command.set_as_project_default:
        project.default_run_policy_id = policy.policy_id
        await uow.projects.save(project)

    await uow.commit()
    return policy
