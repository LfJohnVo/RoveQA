"""Unit-of-work contract suite.

Both implementations must give the same transaction guarantees, otherwise a use case
that forgets to commit passes against fakes and loses data in production.
"""

from collections.abc import Callable

import pytest

from agentic_qa.application.commands.create_run_draft import (
    CreateRunDraftCommand,
    create_run_draft,
)
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.domain.projects.project import Project
from agentic_qa.domain.runs.run import Run, RunStatus

UnitOfWorkFactory = Callable[[], UnitOfWork]


class Boom(Exception):
    pass


async def test_commit_makes_writes_visible_to_a_later_transaction(
    unit_of_work_factory: UnitOfWorkFactory,
) -> None:
    async with unit_of_work_factory() as uow:
        await uow.projects.add(Project(project_id="p-commit", name="Checkout"))
        await uow.commit()

    async with unit_of_work_factory() as uow:
        assert await uow.projects.get("p-commit") is not None


async def test_leaving_the_block_without_commit_rolls_back(
    unit_of_work_factory: UnitOfWorkFactory,
) -> None:
    async with unit_of_work_factory() as uow:
        await uow.projects.add(Project(project_id="p-forgot", name="Checkout"))
        # deliberately no commit

    async with unit_of_work_factory() as uow:
        assert await uow.projects.get("p-forgot") is None


async def test_an_exception_rolls_back_every_write_in_the_block(
    unit_of_work_factory: UnitOfWorkFactory,
) -> None:
    with pytest.raises(Boom):
        async with unit_of_work_factory() as uow:
            await uow.projects.add(Project(project_id="p-boom", name="Checkout"))
            await uow.runs.add(Run(run_id="r-boom", project_id="p-boom"))
            raise Boom

    async with unit_of_work_factory() as uow:
        assert await uow.projects.get("p-boom") is None
        assert await uow.runs.get("r-boom") is None


async def test_repositories_of_one_unit_of_work_share_the_transaction(
    unit_of_work_factory: UnitOfWorkFactory,
) -> None:
    """A run written next to its project must be atomic with it, not half-committed."""
    async with unit_of_work_factory() as uow:
        await uow.projects.add(Project(project_id="p-atomic", name="Checkout"))
        await uow.commit()

    async with unit_of_work_factory() as uow:
        result = await create_run_draft(
            uow, CreateRunDraftCommand(project_id="p-atomic", idempotency_key="k-atomic")
        )

    async with unit_of_work_factory() as uow:
        stored = await uow.runs.get(result.run.run_id)
        assert stored is not None
        assert stored.status is RunStatus.CREATED
        assert await uow.projects.get("p-atomic") is not None


async def test_writes_after_a_commit_still_roll_back(
    unit_of_work_factory: UnitOfWorkFactory,
) -> None:
    async with unit_of_work_factory() as uow:
        await uow.projects.add(Project(project_id="p-first", name="First"))
        await uow.commit()
        await uow.projects.add(Project(project_id="p-second", name="Second"))

    async with unit_of_work_factory() as uow:
        assert await uow.projects.get("p-first") is not None
        assert await uow.projects.get("p-second") is None


async def test_using_repositories_outside_the_context_is_rejected(
    unit_of_work_factory: UnitOfWorkFactory,
) -> None:
    uow = unit_of_work_factory()
    with pytest.raises(RuntimeError):
        _ = uow.projects

    async with uow:
        await uow.projects.add(Project(project_id="p-scope", name="Scoped"))
        await uow.commit()

    with pytest.raises(RuntimeError):
        _ = uow.projects
