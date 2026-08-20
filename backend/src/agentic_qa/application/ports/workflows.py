"""Durable workflow port.

Temporal owns the run lifecycle (ADR 0002/0009) but Application only sees this
protocol: start, and explicit lifecycle commands. A client that stops waiting never
appears here, because detaching is not cancelling (docs/12).
"""

from typing import Protocol


class WorkflowGateway(Protocol):
    async def start_run(self, run_id: str, project_id: str, *, explore: bool = False) -> None:
        """Start the durable workflow for an already-persisted run.

        Naturally idempotent: starting a workflow whose id already exists is a no-op,
        so a retried start after a lost acknowledgement cannot duplicate the run.
        """
        ...

    async def request_pause(self, run_id: str) -> None: ...

    async def request_resume(self, run_id: str) -> None: ...

    async def request_cancel(self, run_id: str) -> None:
        """Ask the run to stop at its next safe point. Idempotent."""
        ...
