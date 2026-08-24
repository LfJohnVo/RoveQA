"""Repositories for environments and run policies."""

from typing import Protocol

from agentic_qa.domain.projects.environment import Environment
from agentic_qa.domain.projects.run_policy import RunPolicy


class EnvironmentRepository(Protocol):
    async def add(self, environment: Environment) -> None:
        """Persist a new environment. Raises AlreadyExistsError when the id is taken."""
        ...

    async def get(self, environment_id: str) -> Environment | None: ...

    async def list_for_project(self, project_id: str) -> list[Environment]:
        """One project's environments, ordered by id so two reads agree.

        Unbounded, unlike the other listings, and the asymmetry is deliberate: a project
        has a handful of environments — staging, production — because each one is a
        deployment somebody maintains. A page size here would be a limit on a number
        that cannot grow on its own.
        """
        ...


class RunPolicyRepository(Protocol):
    async def add(self, policy: RunPolicy) -> None:
        """Persist a new policy. Raises AlreadyExistsError when the id is taken.

        There is no update: policies are immutable so a finished run's rules cannot be
        rewritten underneath it.
        """
        ...

    async def get(self, policy_id: str) -> RunPolicy | None: ...
