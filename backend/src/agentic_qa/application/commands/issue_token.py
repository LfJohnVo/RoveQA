"""Issue and revoke API tokens (ADR 0020).

Commands own their transaction and commit; queries take repositories (ADR 0010).

There is no HTTP router over these, deliberately. They are reachable from
`agentic_qa.interfaces.admin` and from nowhere else, so minting a credential requires the
host rather than a network request.
"""

from dataclasses import dataclass
from uuid import uuid4

from agentic_qa.application.errors import NotFoundError
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.domain.projects.api_token import ApiToken, IssuedToken, issue


@dataclass(frozen=True)
class IssueTokenCommand:
    project_id: str
    label: str
    issued_by: str = ""


async def issue_token(uow: UnitOfWork, command: IssueTokenCommand) -> IssuedToken:
    """Mint a token for a project.

    The project is checked first, so a typo in the id is a `NotFoundError` rather than a
    live credential pointing at nothing — which would be a token that authenticates and
    authorises for a project that does not exist, and therefore for none.
    """
    if await uow.projects.get(command.project_id) is None:
        raise NotFoundError("project", command.project_id)

    minted = issue(
        token_id=str(uuid4()),
        project_id=command.project_id,
        label=command.label,
        issued_by=command.issued_by,
    )
    await uow.api_tokens.add(minted.record)
    await uow.commit()
    return minted


async def revoke_token(uow: UnitOfWork, *, token_id: str) -> bool:
    """Remove a token. True when there was one.

    Not idempotent-by-silence: the caller is a person at a terminal, and telling them
    "there was no such token" is the difference between a revocation and a typo they are
    about to walk away from believing.
    """
    removed = await uow.api_tokens.revoke(token_id)
    await uow.commit()
    return removed


async def list_tokens(uow: UnitOfWork, *, project_id: str) -> list[ApiToken]:
    """A project's tokens, newest first. Records only; there is nothing else to list."""
    return await uow.api_tokens.list_for_project(project_id)
