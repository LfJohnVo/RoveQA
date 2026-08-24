"""Registering, listing and revoking a borrowed browser session (ADR 0019).

Three operations and a rule that shapes all of them: **a session goes in and never comes
back out**. There is no endpoint that returns a stored `storage_state`, and adding one
would undo the containment — the value would then be readable by anyone who can read the
API, which is a wider set than the worker that needs it.

Rotating is registering another. There is no update: an overwrite erases the answer to
"what were we using yesterday", which is the first question asked after runs start
failing.
"""

from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from agentic_qa.application.commands.register_session import (
    RegisterSessionCommand,
    register_session,
    revoke_session,
)
from agentic_qa.interfaces.http.dependencies import SecretKeyringDep, UnitOfWorkDep
from agentic_qa.interfaces.http.schemas import (
    EnvironmentSessionResponse,
    RegisterSessionRequest,
)

router = APIRouter(prefix="/api/v1/environments/{environment_id}/sessions", tags=["sessions"])

DEFAULT_SESSION_PAGE_SIZE = 50
MAX_SESSION_PAGE_SIZE = 200

EnvironmentId = Annotated[str, Path(description="The environment this session belongs to")]


@router.post("", response_model=EnvironmentSessionResponse, status_code=status.HTTP_201_CREATED)
async def post_session(
    environment_id: EnvironmentId,
    payload: RegisterSessionRequest,
    uow: UnitOfWorkDep,
    keyring: SecretKeyringDep,
) -> EnvironmentSessionResponse:
    """Register a session somebody established by logging in.

    The `storage_state` goes in the request body and nowhere else: it is sealed before
    the transaction commits, and the response carries the record without it.
    """
    session = await register_session(
        uow,
        keyring,
        RegisterSessionCommand(
            environment_id=environment_id,
            label=payload.label,
            storage_state=payload.storage_state,
            valid_until=payload.valid_until,
            established_by=payload.established_by,
        ),
    )
    return EnvironmentSessionResponse.from_domain(session)


@router.get("", response_model=list[EnvironmentSessionResponse])
async def list_sessions(
    environment_id: EnvironmentId,
    uow: UnitOfWorkDep,
    limit: Annotated[int, Query(ge=1, le=MAX_SESSION_PAGE_SIZE)] = DEFAULT_SESSION_PAGE_SIZE,
) -> list[EnvironmentSessionResponse]:
    """Every session recorded for the environment, newest first.

    Records only. A listing that carried the sealed bytes would be a listing nobody could
    safely render, and one that carried them opened would not be a listing at all.
    """
    sessions = await uow.sessions.list_for_environment(environment_id)
    return [EnvironmentSessionResponse.from_domain(session) for session in sessions[:limit]]


@router.post("/{session_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def post_revoke(
    environment_id: EnvironmentId,
    session_id: str,
    uow: UnitOfWorkDep,
    keyring: SecretKeyringDep,
) -> None:
    """Revoke a session by destroying its key.

    A command rather than `DELETE`, because the record is not deleted and saying so with
    the wrong verb would be a lie the client acts on: a caller that sent `DELETE` and then
    listed the sessions would still see this one, and reasonably conclude the delete
    failed. What is destroyed is the key — the row stays as the audit trail of who
    registered what and when, and the absence of a key the database never held is what
    makes the session unusable. Restoring any backup ever taken brings the ciphertext
    back and it decrypts to nothing (ADR 0019).

    Idempotent. Revoking something already revoked is the state the caller asked for, so
    a client that lost the response can safely repeat it.
    """
    await revoke_session(uow, keyring, environment_id=environment_id, session_id=session_id)
