"""Move a run to a new lifecycle state.

Every status change goes through the domain state machine, so the database can never
hold a transition the domain rejects — that is what keeps durable status and workflow
state from diverging silently.

Only the workflow drives transitions (through its activities). The API signals intent;
it never writes status itself.
"""

from dataclasses import dataclass

from agentic_qa.application.errors import NotFoundError
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.domain.runs.run import Run, RunStatus, Verdict


@dataclass(frozen=True)
class TransitionRunCommand:
    run_id: str
    target_status: RunStatus
    verdict: Verdict | None = None


async def transition_run(uow: UnitOfWork, command: TransitionRunCommand) -> Run:
    run = await uow.runs.get(command.run_id)
    if run is None:
        raise NotFoundError("run", command.run_id)

    run.transition_to(command.target_status, command.verdict)
    await uow.runs.save(run)
    await uow.commit()
    return run
