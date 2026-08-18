"""Resolve the RunPolicy that governs a run.

Normative order (docs/12, docs/13): the policy named by the request, else the
environment default, else the project default. If none resolves the request fails
typed — a run never starts without a policy, because the origin allowlist is the
primary control against reaching services nobody asked it to reach.
"""

from agentic_qa.application.errors import ApplicationError, NotFoundError
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.domain.projects.run_policy import RunPolicy


class PolicyNotResolvedError(ApplicationError):
    """No run policy could be resolved, so the run must not start."""

    def __init__(self, project_id: str, environment_id: str | None) -> None:
        super().__init__(
            "no run policy resolved for project "
            f"{project_id} (environment={environment_id or 'none'}); "
            "set a policy on the request, the environment or the project"
        )
        self.project_id = project_id
        self.environment_id = environment_id


async def resolve_run_policy(
    uow: UnitOfWork,
    *,
    project_id: str,
    environment_id: str | None = None,
    requested_policy_id: str | None = None,
) -> RunPolicy:
    for candidate in await _candidates(
        uow, project_id=project_id, environment_id=environment_id, requested=requested_policy_id
    ):
        policy = await uow.policies.get(candidate)
        if policy is None:
            # A dangling reference is a configuration error, not a reason to fall
            # through to a weaker policy.
            raise NotFoundError("run_policy", candidate)
        if policy.project_id != project_id:
            # A policy belonging to another project must never govern this run.
            raise PolicyNotResolvedError(project_id, environment_id)
        resolved: RunPolicy = policy
        return resolved

    raise PolicyNotResolvedError(project_id, environment_id)


async def _candidates(
    uow: UnitOfWork,
    *,
    project_id: str,
    environment_id: str | None,
    requested: str | None,
) -> list[str]:
    if requested is not None:
        return [requested]

    if environment_id is not None:
        environment = await uow.environments.get(environment_id)
        if environment is None:
            raise NotFoundError("environment", environment_id)
        if environment.project_id != project_id:
            raise PolicyNotResolvedError(project_id, environment_id)
        if environment.default_run_policy_id is not None:
            return [environment.default_run_policy_id]

    project = await uow.projects.get(project_id)
    if project is None:
        raise NotFoundError("project", project_id)
    return [project.default_run_policy_id] if project.default_run_policy_id else []
