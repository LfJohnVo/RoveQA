"""Recovery points: the domain's view of where a run can safely resume (ADR 0009).

Two checkpoint concepts meet here and must not be confused:

- LangGraph's checkpointer persists graph state at every superstep. That is an
  infrastructure detail and its ids mean nothing to the domain.
- A `RecoveryPoint` is a *semantically significant* moment (login verified, stable
  navigation, submit verified, episode closed) plus everything needed to rebuild the
  browser there. It references the graph checkpoint but is not the same thing.

Resume loads the latest graph checkpoint and validates it against the newest
RecoveryPoint. If validation fails, the run falls back to the RecoveryPoint and
re-derives, because a graph state whose browser preconditions no longer hold is not
a place to continue from (docs/05).
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from agentic_qa.domain.validation import require_identifier, require_text


class RecoveryTrigger(StrEnum):
    """Why this point was considered safe. Not every step earns one."""

    LOGIN_VERIFIED = "login_verified"
    NAVIGATION_STABLE = "navigation_stable"
    SUBMIT_VERIFIED = "submit_verified"
    GOAL_COMPLETED = "goal_completed"
    ERROR_DISCOVERED = "error_discovered"
    EPISODE_CLOSED = "episode_closed"


@dataclass(frozen=True)
class BrowserRecoveryData:
    """What it takes to rebuild the browser here. Chromium itself is never serialized."""

    url: str
    page_fingerprint: str | None = None
    storage_state_ref: str | None = None
    """Artifact id of the stored storage state; the secret itself never lives here."""

    last_verified_action: str | None = None


@dataclass(frozen=True)
class RecoveryPoint:
    recovery_point_id: str
    run_id: str
    episode_index: int
    trigger: RecoveryTrigger
    graph_checkpoint_id: str
    """Opaque to the domain: it only has to be handed back to the checkpointer."""

    browser: BrowserRecoveryData
    created_at: datetime

    def __post_init__(self) -> None:
        require_identifier(self.recovery_point_id, field="recovery_point_id")
        require_identifier(self.run_id, field="run_id")
        require_text(self.graph_checkpoint_id, field="graph_checkpoint_id", max_length=500)
