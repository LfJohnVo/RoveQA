"""Run aggregate: lifecycle state machine and terminal verdict.

RunStatus is the lifecycle state; Verdict is the QA outcome and exists only on
terminal runs. Mapping rules live in docs/02-domain-model.md.
"""

from dataclasses import dataclass, field
from enum import StrEnum

from agentic_qa.domain.errors import DomainError
from agentic_qa.domain.validation import require_identifier


class RunStatus(StrEnum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSING = "pausing"
    PAUSED = "paused"
    RECOVERING = "recovering"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    FAILED = "failed"
    COMPLETED = "completed"


class Verdict(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    INCONCLUSIVE = "inconclusive"
    CANCELLED = "cancelled"


TERMINAL_STATUSES = frozenset({RunStatus.CANCELLED, RunStatus.FAILED, RunStatus.COMPLETED})

# Every non-terminal status may additionally transition to FAILED
# (infrastructure can die at any point); encoded in _allowed_targets().
_TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    RunStatus.CREATED: frozenset({RunStatus.QUEUED, RunStatus.CANCELLING}),
    RunStatus.QUEUED: frozenset({RunStatus.RUNNING, RunStatus.CANCELLING}),
    RunStatus.RUNNING: frozenset(
        {
            RunStatus.PAUSING,
            RunStatus.RECOVERING,
            RunStatus.CANCELLING,
            RunStatus.COMPLETED,
        }
    ),
    RunStatus.PAUSING: frozenset({RunStatus.PAUSED, RunStatus.CANCELLING}),
    RunStatus.PAUSED: frozenset({RunStatus.RUNNING, RunStatus.CANCELLING}),
    RunStatus.RECOVERING: frozenset({RunStatus.RUNNING, RunStatus.CANCELLING}),
    RunStatus.CANCELLING: frozenset({RunStatus.CANCELLED}),
    RunStatus.CANCELLED: frozenset(),
    RunStatus.FAILED: frozenset(),
    RunStatus.COMPLETED: frozenset(),
}

_COMPLETED_VERDICTS = frozenset(
    {Verdict.PASSED, Verdict.FAILED, Verdict.BLOCKED, Verdict.INCONCLUSIVE}
)
_INFRA_FAILURE_VERDICTS = frozenset({Verdict.INCONCLUSIVE, Verdict.BLOCKED})


class RunTransitionError(DomainError):
    """A run lifecycle invariant was violated."""


def _allowed_targets(status: RunStatus) -> frozenset[RunStatus]:
    if status in TERMINAL_STATUSES:
        return _TRANSITIONS[status]
    return _TRANSITIONS[status] | {RunStatus.FAILED}


@dataclass
class Run:
    run_id: str
    project_id: str
    status: RunStatus = RunStatus.CREATED
    verdict: Verdict | None = field(default=None)
    run_policy_id: str | None = None
    """The policy that governs this run, resolved once at creation and never re-read."""

    environment_id: str | None = None

    def __post_init__(self) -> None:
        self.run_id = require_identifier(self.run_id, field="run_id")
        self.project_id = require_identifier(self.project_id, field="project_id")
        if self.run_policy_id is not None:
            self.run_policy_id = require_identifier(self.run_policy_id, field="run_policy_id")
        if self.environment_id is not None:
            self.environment_id = require_identifier(self.environment_id, field="environment_id")

    def transition_to(self, new_status: RunStatus, verdict: Verdict | None = None) -> None:
        if self.status in TERMINAL_STATUSES:
            raise RunTransitionError(f"run {self.run_id} is terminal ({self.status})")
        if new_status not in _allowed_targets(self.status):
            raise RunTransitionError(
                f"illegal transition {self.status} -> {new_status} for run {self.run_id}"
            )
        self._validate_verdict(new_status, verdict)
        self.status = new_status
        self.verdict = self._resolve_verdict(new_status, verdict)

    def _validate_verdict(self, new_status: RunStatus, verdict: Verdict | None) -> None:
        if new_status not in TERMINAL_STATUSES:
            if verdict is not None:
                raise RunTransitionError("verdict is only valid on terminal transitions")
            return
        if new_status is RunStatus.COMPLETED and verdict not in _COMPLETED_VERDICTS:
            raise RunTransitionError(
                "COMPLETED requires a QA verdict (passed/failed/blocked/inconclusive)"
            )
        if new_status is RunStatus.CANCELLED and verdict not in (None, Verdict.CANCELLED):
            raise RunTransitionError("CANCELLED runs carry verdict=cancelled")
        if new_status is RunStatus.FAILED and verdict not in (None, *_INFRA_FAILURE_VERDICTS):
            raise RunTransitionError(
                "FAILED means infrastructure failure; verdict must be inconclusive or blocked"
            )

    def _resolve_verdict(self, new_status: RunStatus, verdict: Verdict | None) -> Verdict | None:
        if new_status is RunStatus.CANCELLED:
            return Verdict.CANCELLED
        if new_status is RunStatus.FAILED:
            return verdict or Verdict.INCONCLUSIVE
        if new_status is RunStatus.COMPLETED:
            return verdict
        return None

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES
