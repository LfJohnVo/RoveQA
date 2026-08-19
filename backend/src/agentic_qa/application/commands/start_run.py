"""Start a run, idempotently.

Ordering is the durability contract (ADR 0010): the run and its idempotency record
are committed *before* the workflow is started. If starting then fails, a queued run
exists and is recoverable; the reverse order could leave a workflow with no durable
row behind it.
"""

from dataclasses import dataclass
from uuid import uuid4

from agentic_qa.application.errors import IdempotencyConflictError, NotFoundError
from agentic_qa.application.ports.events import RUN_CREATED, NewRunEvent
from agentic_qa.application.ports.idempotency import (
    RUN_CREATION_SCOPE,
    IdempotencyRecord,
    request_fingerprint,
)
from agentic_qa.application.ports.streams import RunEventPublisher
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.application.ports.workflows import WorkflowGateway
from agentic_qa.application.services.event_publishing import publish_best_effort
from agentic_qa.application.services.policy_resolution import resolve_run_policy
from agentic_qa.domain.qa.test_plan import TestPlan
from agentic_qa.domain.runs.run import Run, RunStatus


@dataclass(frozen=True)
class StartRunCommand:
    project_id: str
    idempotency_key: str
    environment_id: str | None = None
    run_policy_id: str | None = None
    plan_id: str | None = None
    plan_version: str | None = None
    """Which plan to run. Without a version the latest is resolved *once*, here, and
    pinned onto the run: the plan a run is judged by must not change under it."""

    request_id: str | None = None
    """Recorded on the run.created event so one id correlates client, API and run."""

    def fingerprint(self) -> str:
        return request_fingerprint(
            RUN_CREATION_SCOPE,
            {
                "project_id": self.project_id,
                "environment_id": self.environment_id or "",
                "run_policy_id": self.run_policy_id or "",
                "plan_id": self.plan_id or "",
                "plan_version": self.plan_version or "",
            },
        )


@dataclass(frozen=True)
class StartRunResult:
    run: Run
    replayed: bool
    """True when an existing run was returned for a repeated request."""


async def start_run(
    uow: UnitOfWork,
    workflows: WorkflowGateway,
    command: StartRunCommand,
    publisher: RunEventPublisher | None = None,
) -> StartRunResult:
    fingerprint = command.fingerprint()
    existing = await uow.idempotency.get(RUN_CREATION_SCOPE, command.idempotency_key)

    if existing is not None:
        if existing.request_fingerprint != fingerprint:
            raise IdempotencyConflictError(RUN_CREATION_SCOPE, command.idempotency_key)
        replayed = await uow.runs.get(existing.resource_id)
        if replayed is None:
            # Record and run commit together, so this cannot happen without data loss.
            raise NotFoundError("run", existing.resource_id)
        return StartRunResult(run=replayed, replayed=True)

    if await uow.projects.get(command.project_id) is None:
        raise NotFoundError("project", command.project_id)

    # No policy, no run: the origin allowlist is the primary control against reaching
    # services nobody asked for (docs/13), so an unresolvable policy fails typed here
    # rather than becoming a permissive default later.
    policy = await resolve_run_policy(
        uow,
        project_id=command.project_id,
        environment_id=command.environment_id,
        requested_policy_id=command.run_policy_id,
    )

    plan = await _resolve_plan(uow, command)

    run = Run(
        run_id=str(uuid4()),
        project_id=command.project_id,
        environment_id=command.environment_id,
        run_policy_id=policy.policy_id,
        plan_id=plan.plan_id if plan else None,
        plan_version=plan.plan_version if plan else None,
    )
    run.transition_to(RunStatus.QUEUED)  # accepted; the worker will pick it up
    await uow.runs.add(run)
    event = await uow.events.append(
        NewRunEvent(
            run_id=run.run_id,
            type=RUN_CREATED,
            payload={
                "project_id": run.project_id,
                "status": run.status.value,
                "run_policy_id": policy.policy_id,
                "plan_id": run.plan_id,
                "plan_version": run.plan_version,
            },
            request_id=command.request_id,
        )
    )
    await uow.idempotency.add(
        IdempotencyRecord(
            scope=RUN_CREATION_SCOPE,
            key=command.idempotency_key,
            request_fingerprint=fingerprint,
            resource_id=run.run_id,
        )
    )
    await uow.commit()

    # Durable first, side effects second. Starting is itself idempotent, so a retry
    # after a lost acknowledgement cannot produce a second workflow.
    await publish_best_effort(publisher, event)
    await workflows.start_run(run.run_id, run.project_id)
    return StartRunResult(run=run, replayed=False)


async def _resolve_plan(uow: UnitOfWork, command: StartRunCommand) -> TestPlan | None:
    """Pin the plan version now, or run without a plan (exploratory).

    Resolving "latest" happens exactly once, here. If the activity resolved it per
    episode instead, publishing a new version mid-run would change what the run is
    being judged by while it is running.
    """
    if command.plan_id is None:
        if command.plan_version is not None:
            raise NotFoundError("test_plan", command.plan_version)
        return None

    plan = (
        await uow.plans.get(command.plan_id, command.plan_version)
        if command.plan_version is not None
        else await uow.plans.latest(command.plan_id)
    )
    if plan is None:
        raise NotFoundError("test_plan", f"{command.plan_id}@{command.plan_version or 'latest'}")
    if plan.project_id != command.project_id:
        # A plan from another project would run under this project's policy against
        # another project's expectations.
        raise NotFoundError("test_plan", plan.plan_id)
    return plan
