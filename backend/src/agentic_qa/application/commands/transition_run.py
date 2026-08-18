"""Move a run to a new lifecycle state.

Every status change goes through the domain state machine, so the database can never
hold a transition the domain rejects — that is what keeps durable status and workflow
state from diverging silently.

Only the workflow drives transitions (through its activities). The API signals intent;
it never writes status itself.
"""

from dataclasses import dataclass

from agentic_qa.application.errors import NotFoundError
from agentic_qa.application.ports.events import RUN_STATUS_CHANGED, NewRunEvent
from agentic_qa.application.ports.streams import RunEventPublisher
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.application.services.event_publishing import publish_best_effort
from agentic_qa.domain.runs.run import Run, RunStatus, Verdict


@dataclass(frozen=True)
class TransitionRunCommand:
    run_id: str
    target_status: RunStatus
    verdict: Verdict | None = None


async def transition_run(
    uow: UnitOfWork,
    command: TransitionRunCommand,
    publisher: RunEventPublisher | None = None,
) -> Run:
    run = await uow.runs.get(command.run_id)
    if run is None:
        raise NotFoundError("run", command.run_id)

    previous = run.status
    run.transition_to(command.target_status, command.verdict)
    await uow.runs.save(run)
    # Same transaction as the status change: a run can never move without leaving its
    # event, nor an event exist for a move that was rolled back.
    event = await uow.events.append(
        NewRunEvent(
            run_id=run.run_id,
            type=RUN_STATUS_CHANGED,
            payload={
                "from": previous.value,
                "to": run.status.value,
                "verdict": run.verdict.value if run.verdict else None,
            },
        )
    )
    await uow.commit()
    # Durable first, fan-out second and best-effort (ADR 0010 ordering).
    await publish_best_effort(publisher, event)
    return run
