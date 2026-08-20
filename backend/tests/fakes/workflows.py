"""Workflow gateway double that records what the API asked for.

It records intent only: it never changes run status, because in production only the
workflow's activities do. A fake that flipped status here would hide the very
divergence the phase gates test for.
"""

from dataclasses import dataclass, field


@dataclass
class RecordingWorkflowGateway:
    started: list[tuple[str, str]] = field(default_factory=list)
    signals: list[tuple[str, str]] = field(default_factory=list)
    explored: list[str] = field(default_factory=list)
    """Runs asked to explore. Recorded separately so a test can tell an exploration
    from a planned run without reading past the API boundary."""

    async def start_run(self, run_id: str, project_id: str, *, explore: bool = False) -> None:
        self.started.append((run_id, project_id))
        if explore:
            self.explored.append(run_id)

    async def request_pause(self, run_id: str) -> None:
        self.signals.append((run_id, "pause"))

    async def request_resume(self, run_id: str) -> None:
        self.signals.append((run_id, "resume"))

    async def request_cancel(self, run_id: str) -> None:
        self.signals.append((run_id, "cancel"))


@dataclass
class FailingWorkflowGateway:
    """Start fails after the run was committed — the recoverable case in ADR 0010."""

    started: list[tuple[str, str]] = field(default_factory=list)

    async def start_run(self, run_id: str, project_id: str, *, explore: bool = False) -> None:
        raise RuntimeError("temporal unreachable")

    async def request_pause(self, run_id: str) -> None: ...

    async def request_resume(self, run_id: str) -> None: ...

    async def request_cancel(self, run_id: str) -> None: ...
