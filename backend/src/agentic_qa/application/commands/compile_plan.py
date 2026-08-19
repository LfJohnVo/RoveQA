"""Compile a user story into a stored, versioned TestPlan.

Versioning is the point of this command. Recompiling a story that changed produces a
new version rather than overwriting the old one, so a run finished last week can still
be read against the plan it was actually judged by.

The compilation itself is deterministic (see `domain/qa/test_plan.compile_story`): no
model participates, which is what makes "a known story passes or fails reproducibly" a
property of the system.
"""

from dataclasses import dataclass
from uuid import uuid4

from agentic_qa.application.errors import NotFoundError
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.domain.qa.test_plan import PlanBudget, TestPlan, compile_story


@dataclass(frozen=True)
class CompilePlanCommand:
    story_id: str
    run_policy_id: str | None = None
    environment_id: str | None = None
    budget: PlanBudget | None = None
    plan_id: str | None = None
    """Reuse an existing plan's id to publish a new version of it."""


async def compile_plan(uow: UnitOfWork, command: CompilePlanCommand) -> TestPlan:
    story = await uow.stories.get(command.story_id)
    if story is None:
        raise NotFoundError("user_story", command.story_id)

    if command.run_policy_id is not None and await uow.policies.get(command.run_policy_id) is None:
        # Caught here rather than by a foreign key: a plan naming a policy that does not
        # exist would only fail later, when a run tries to start under it.
        raise NotFoundError("run_policy", command.run_policy_id)

    plan_id = command.plan_id or str(uuid4())
    plan = compile_story(
        story,
        plan_id=plan_id,
        plan_version=await _next_version(uow, plan_id),
        run_policy_id=command.run_policy_id,
        environment_id=command.environment_id,
        budget=command.budget,
    )

    await uow.plans.add(plan)
    await uow.commit()
    return plan


async def _next_version(uow: UnitOfWork, plan_id: str) -> str:
    """Monotonic integers as strings. The contract allows any string; sequential
    integers make "which came first" answerable without a timestamp."""
    latest = await uow.plans.latest(plan_id)
    if latest is None:
        return "1"
    try:
        return str(int(latest.plan_version) + 1)
    except ValueError:
        # An imported plan may carry a version like "2026.08-rc1"; do not try to
        # increment something we did not author.
        return f"{latest.plan_version}+1"
