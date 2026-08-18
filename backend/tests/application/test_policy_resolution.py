"""RunPolicy resolution order (docs/12).

A run without a resolved policy has no origin allowlist, so every path that cannot
resolve one must fail rather than fall back to something permissive.
"""

import pytest

from agentic_qa.application.errors import NotFoundError
from agentic_qa.application.services.policy_resolution import (
    PolicyNotResolvedError,
    resolve_run_policy,
)
from agentic_qa.domain.projects.environment import Environment
from agentic_qa.domain.projects.project import Project
from agentic_qa.domain.projects.run_policy import RunPolicy
from tests.fakes.repositories import InMemoryStore
from tests.fakes.unit_of_work import InMemoryUnitOfWork


def make_policy(
    policy_id: str, project_id: str = "p-1", origin: str = "https://a.test"
) -> RunPolicy:
    return RunPolicy(
        policy_id=policy_id,
        project_id=project_id,
        allowed_origins=(origin,),
        max_duration_seconds=600,
        max_actions=100,
        max_model_calls=10,
    )


@pytest.fixture
def uow() -> InMemoryUnitOfWork:
    return InMemoryUnitOfWork(InMemoryStore())


async def seed(
    uow: InMemoryUnitOfWork,
    *,
    project_default: str | None = None,
    environment_default: str | None = None,
    policies: tuple[RunPolicy, ...] = (),
) -> None:
    async with uow:
        await uow.projects.add(
            Project(project_id="p-1", name="Checkout", default_run_policy_id=project_default)
        )
        await uow.environments.add(
            Environment(
                environment_id="e-1",
                project_id="p-1",
                name="staging",
                default_run_policy_id=environment_default,
            )
        )
        for policy in policies:
            await uow.policies.add(policy)
        await uow.commit()


async def test_the_requested_policy_wins(uow: InMemoryUnitOfWork) -> None:
    await seed(
        uow,
        project_default="pol-project",
        environment_default="pol-env",
        policies=(make_policy("pol-project"), make_policy("pol-env"), make_policy("pol-asked")),
    )

    async with uow:
        resolved = await resolve_run_policy(
            uow, project_id="p-1", environment_id="e-1", requested_policy_id="pol-asked"
        )

    assert resolved.policy_id == "pol-asked"


async def test_the_environment_default_comes_before_the_project_default(
    uow: InMemoryUnitOfWork,
) -> None:
    await seed(
        uow,
        project_default="pol-project",
        environment_default="pol-env",
        policies=(make_policy("pol-project"), make_policy("pol-env")),
    )

    async with uow:
        resolved = await resolve_run_policy(uow, project_id="p-1", environment_id="e-1")

    assert resolved.policy_id == "pol-env"


async def test_the_project_default_is_the_last_resort(uow: InMemoryUnitOfWork) -> None:
    await seed(uow, project_default="pol-project", policies=(make_policy("pol-project"),))

    async with uow:
        resolved = await resolve_run_policy(uow, project_id="p-1", environment_id="e-1")

    assert resolved.policy_id == "pol-project"


async def test_no_policy_anywhere_fails_instead_of_defaulting(uow: InMemoryUnitOfWork) -> None:
    await seed(uow)

    async with uow:
        with pytest.raises(PolicyNotResolvedError):
            await resolve_run_policy(uow, project_id="p-1", environment_id="e-1")


async def test_a_dangling_reference_fails_instead_of_falling_through(
    uow: InMemoryUnitOfWork,
) -> None:
    """A misconfigured default is an error, not a reason to use a weaker policy."""
    await seed(uow, project_default="pol-missing")

    async with uow:
        with pytest.raises(NotFoundError):
            await resolve_run_policy(uow, project_id="p-1")


async def test_a_policy_from_another_project_is_refused(uow: InMemoryUnitOfWork) -> None:
    await seed(uow, policies=(make_policy("pol-other", project_id="p-other"),))

    async with uow:
        with pytest.raises(PolicyNotResolvedError):
            await resolve_run_policy(uow, project_id="p-1", requested_policy_id="pol-other")


async def test_an_environment_of_another_project_is_refused(uow: InMemoryUnitOfWork) -> None:
    await seed(uow, project_default="pol-project", policies=(make_policy("pol-project"),))
    async with uow:
        await uow.environments.add(
            Environment(environment_id="e-other", project_id="p-other", name="other")
        )
        await uow.commit()

    async with uow:
        with pytest.raises(PolicyNotResolvedError):
            await resolve_run_policy(uow, project_id="p-1", environment_id="e-other")
