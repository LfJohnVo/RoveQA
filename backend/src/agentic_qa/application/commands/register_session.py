"""Register and revoke a borrowed browser session (ADR 0019).

Commands own their transaction and commit; queries take repositories (ADR 0010).

The ordering in each of these is the interesting part, and both are chosen so that a
crash in the middle leaves the safe state rather than the convenient one.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from agentic_qa.application.errors import NotFoundError
from agentic_qa.application.ports.sessions import SecretKeyring
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.domain.projects.session import EnvironmentSession


@dataclass(frozen=True)
class RegisterSessionCommand:
    environment_id: str
    label: str
    storage_state: str
    """The session as the browser exported it, JSON. The only place in this system a
    caller hands one over, and the last place it exists unsealed."""

    valid_until: datetime | None = None
    established_by: str = ""


async def register_session(
    uow: UnitOfWork, keyring: SecretKeyring, command: RegisterSessionCommand
) -> EnvironmentSession:
    """Seal the state, then record it.

    Sealed *before* the row is written, and deliberately in that order. A crash between
    the two leaves a key with no record — an orphan file nothing points at, which the next
    registration ignores. The other order leaves a record with no ciphertext, which is a
    session that looks usable in a listing and fails at the moment a run needs it.
    """
    if await uow.environments.get(command.environment_id) is None:
        raise NotFoundError("environment", command.environment_id)

    session = EnvironmentSession(
        session_id=str(uuid4()),
        environment_id=command.environment_id,
        label=command.label,
        established_at=datetime.now(UTC),
        valid_until=command.valid_until,
        established_by=command.established_by,
    )
    sealed = await keyring.seal(session.session_id, command.storage_state.encode("utf-8"))
    await uow.sessions.add(session, sealed)
    await uow.commit()
    return session


async def revoke_session(
    uow: UnitOfWork, keyring: SecretKeyring, *, environment_id: str, session_id: str
) -> None:
    """Destroy the key. The record stays as the audit trail.

    Checked against the environment before anything is destroyed, so a session id from
    another environment cannot be used to revoke by guessing.

    Idempotent by construction: `forget` on a key already gone is the state the caller
    wanted, and a revocation endpoint that threw on the second call would be one nobody
    could safely retry.
    """
    session = await uow.sessions.get(session_id)
    if session is None or session.environment_id != environment_id:
        raise NotFoundError("environment_session", session_id)
    await keyring.forget(session_id)
