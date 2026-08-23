"""`python -m agentic_qa.admin token issue|list|revoke` — run on the host.

    docker compose exec api python -m agentic_qa.admin token issue \
        --project <id> --label "github actions"

The value is printed **once**, to stdout, and never exists anywhere again: not in the
database, which holds only its SHA-256, and not in a second copy this command could show
later. Losing it means issuing another and revoking this one, which is cheap and is the
only honest recovery from a secret nobody kept.

Written for a person at a terminal rather than for a script, which is why a revocation
that matched nothing says so instead of exiting quietly. A machine-readable mode would be
a second contract to keep, and the caller here is already logged into the host.
"""

import argparse
import asyncio
import sys
from collections.abc import Callable, Sequence

from agentic_qa.application.commands.issue_token import (
    IssueTokenCommand,
    issue_token,
    list_tokens,
    revoke_token,
)
from agentic_qa.application.errors import NotFoundError
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.bootstrap.container import build_container
from agentic_qa.bootstrap.settings import Settings

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_NOT_FOUND = 4
"""Distinct from usage: "you asked for something that is not there" and "you asked
wrongly" are different mistakes and a person fixes them differently."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agentic_qa.admin",
        description="Operations that require the host. Tokens are issued here and nowhere else.",
    )
    groups = parser.add_subparsers(dest="group", required=True)
    token = groups.add_parser("token", help="API tokens for a project's CI").add_subparsers(
        dest="action", required=True
    )

    issue = token.add_parser("issue", help="mint a token; its value is printed once")
    issue.add_argument("--project", required=True, help="the project this token may act on")
    issue.add_argument("--label", required=True, help='what to call it, e.g. "github actions"')
    issue.add_argument("--issued-by", default="", help="who issued it, for the record")

    listing = token.add_parser("list", help="a project's tokens; never their values")
    listing.add_argument("--project", required=True)

    revoke = token.add_parser("revoke", help="remove a token")
    revoke.add_argument("token_id", help="from `token list`")

    return parser


async def run(
    argv: Sequence[str],
    *,
    unit_of_work: Callable[[], UnitOfWork],
    out: Callable[[str], None] = print,
) -> int:
    """The whole command, with its collaborators injected so a test needs no process."""
    args = build_parser().parse_args(list(argv))

    async with unit_of_work() as uow:
        if args.action == "issue":
            try:
                minted = await issue_token(
                    uow,
                    IssueTokenCommand(
                        project_id=args.project, label=args.label, issued_by=args.issued_by
                    ),
                )
            except NotFoundError:
                # Checked before minting, so a typo in the id cannot leave a live
                # credential pointing at a project that does not exist.
                out(f"no such project: {args.project}")
                return EXIT_NOT_FOUND
            out(f"token {minted.record.token_id} for project {minted.record.project_id}")
            out("")
            out(minted.secret)
            out("")
            # Said at the moment it can still be acted on, not in a manual nobody opens.
            out("This is the only time this value is shown. Store it as a CI secret now.")
            return EXIT_OK

        if args.action == "list":
            tokens = await list_tokens(uow, project_id=args.project)
            if not tokens:
                out("No tokens. This project's API is unreachable until one is issued.")
                return EXIT_OK
            for token in tokens:
                issued = token.issued_at.strftime("%Y-%m-%d %H:%M %Z")
                by = f" by {token.issued_by}" if token.issued_by else ""
                out(f"{token.token_id}  {token.label}  issued {issued}{by}")
            return EXIT_OK

        removed = await revoke_token(uow, token_id=args.token_id)
        if not removed:
            out(f"no such token: {args.token_id}")
            return EXIT_NOT_FOUND
        out(f"revoked {args.token_id}. The next request presenting it is refused.")
        return EXIT_OK


async def _main(argv: Sequence[str]) -> int:
    """One event loop for the command *and* the shutdown.

    Two `asyncio.run` calls looked tidier and printed `RuntimeError: Event loop is
    closed` on every invocation: the engine's pool is bound to the loop that created it,
    so closing it in a second loop tears down connections that belong to a loop already
    gone. Harmless to the outcome, alarming to read, and exactly the kind of noise that
    trains an operator to ignore stderr.
    """
    container = build_container(Settings.from_env())
    try:
        return await run(argv, unit_of_work=container.unit_of_work)
    finally:
        await container.aclose()


def main(argv: Sequence[str] | None = None) -> int:
    return asyncio.run(_main(argv if argv is not None else sys.argv[1:]))


if __name__ == "__main__":  # pragma: no cover - the process entry point
    raise SystemExit(main())
