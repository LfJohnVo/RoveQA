"""Who is calling, and whether they may touch what they asked for (ADR 0020).

Two questions, kept apart because a person fixes them in different places. *Who* is a
bearer token hashed and looked up by its fingerprint — no token, or one nobody issued, is
`401 AUTH_REQUIRED`. *May they* is whether that token's project owns the resource the path
names — `403 FORBIDDEN`. Collapsing the two into "denied" sends someone to check their
secret when the secret was fine.

The scope check is a dependency rather than a line in each handler, and that is the whole
design. A rule written per-endpoint survives until the twelfth endpoint; this one is
enforced by a test that walks the OpenAPI document and fails on any route that is neither
covered nor exempt, so forgetting is not available.

Resolving the resource's project is the interesting half. A path may name a project
directly, or a run or an environment that belongs to one, and the row is what says which.
That is one extra query per request against an indexed primary key, which is the price of
not trusting the caller's word about what they are reaching.
"""

import logging
from typing import Annotated

from fastapi import Depends, Header, Request

from agentic_qa.application.errors import AuthenticationRequiredError, ForbiddenError
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.domain.projects.api_token import ApiToken, fingerprint
from agentic_qa.interfaces.http.dependencies import UnitOfWorkDep

logger = logging.getLogger(__name__)

BEARER = "Bearer "

OPEN_PATHS = frozenset({"/health", "/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"})
"""The routes reachable without a token, and every one of them is a decision.

The list lives here, in one place, and the structural test reads *this* — so exempting a
route is a visible edit to a named set rather than an omission nobody can see.

`/health` because the container's healthcheck and any proxy in front call it, and it says
nothing but whether the process is up. Guarding it by accident takes the deployment down
in a way that looks like the application crashing.

The three description endpoints because they describe the *shape* of the API and return
no data: every path they name refuses without a token. The team this exists for reads them
to write their integration, which is worth more than the reconnaissance they give an
attacker who can already see the port. An operator who disagrees closes them at the proxy,
which is the right place for a policy about who may look.
"""


async def authenticate(
    uow: UnitOfWorkDep,
    authorization: Annotated[str | None, Header()] = None,
) -> ApiToken:
    """The caller's token, or `401`.

    Looked up by the hash of what was presented, never by the value: the database holds
    only fingerprints, so a leaked dump yields nothing that can be replayed.
    """
    if authorization is None or not authorization.startswith(BEARER):
        raise AuthenticationRequiredError("this endpoint needs a bearer token")

    presented = authorization[len(BEARER) :].strip()
    if not presented:
        raise AuthenticationRequiredError("this endpoint needs a bearer token")

    token = await uow.api_tokens.find_by_fingerprint(fingerprint(presented))
    if token is None:
        # Deliberately the same message as no token at all. Telling an attacker that a
        # value was *almost* right is an oracle, and there is nothing a legitimate caller
        # does differently between the two.
        raise AuthenticationRequiredError("this endpoint needs a bearer token")
    return token


TokenDep = Annotated[ApiToken, Depends(authenticate)]


async def _project_of_request(request: Request, uow: UnitOfWork) -> str | None:
    """Which project the path is about, or None when it is about none.

    Read from the resolved path parameters rather than parsed out of the URL, so a route
    that renames its parameter breaks loudly here instead of silently authorising.
    """
    # `path_params` is `dict[str, Any]` to Starlette because a converter can produce
    # any type. Every parameter this resolver reads is a string path segment, and
    # saying so here is cheaper than trusting it downstream.
    params = request.path_params

    named = params.get("project_id")
    if named is not None:
        return str(named)

    if "run_id" in params:
        run = await uow.runs.get(str(params["run_id"]))
        return run.project_id if run is not None else None

    if "environment_id" in params:
        environment = await uow.environments.get(str(params["environment_id"]))
        return environment.project_id if environment is not None else None

    if "story_id" in params:
        story = await uow.stories.get(str(params["story_id"]))
        return story.project_id if story is not None else None

    return None


async def authorise(request: Request, uow: UnitOfWorkDep, token: TokenDep) -> ApiToken:
    """The caller's token, having checked it covers what the path names.

    A path that names no project at all — a listing across projects, say — is reachable by
    any valid token. That is a deliberate limit of this design rather than an oversight:
    a token proves membership of one project, and a cross-project listing has no single
    project to check it against. Such routes must therefore not expose anything a caller
    could not already reach, which is a property of what they return, not of this check.

    A resource that does not exist resolves to no project and is treated as authorised, so
    the handler can answer `404`. Refusing here instead would turn every unknown id into a
    `403` and tell a caller which ids exist.
    """
    project_id = await _project_of_request(request, uow)
    if project_id is None:
        return token
    if not token.covers(project_id):
        logger.warning(
            "token %s (project %s) was refused project %s",
            token.token_id,
            token.project_id,
            project_id,
        )
        raise ForbiddenError("this token does not cover that project")
    return token


AuthorisedDep = Annotated[ApiToken, Depends(authorise)]
"""What a router depends on. Applied per router rather than per handler, so a new
endpoint inherits it by living in a router that already has it — and the structural test
catches the router that does not."""
