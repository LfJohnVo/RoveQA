"""No route answers without a token unless it is on a list somebody wrote down.

This is the structural half of ADR 0020, and the reason the check is a dependency rather
than a line in each handler. A rule enforced by discipline survives until the twelfth
endpoint; a rule enforced by a test that walks the whole application survives the
thirteenth, written by somebody who never read the ADR.

The test does not read the source for `Depends(authorise)`. It *calls* every route
without a token and demands a refusal, because what matters is the behaviour and not the
spelling — a route could be guarded by something else entirely and still be correct.
"""

from collections.abc import AsyncIterator, Iterable

import httpx
import pytest

from agentic_qa.bootstrap.container import Container
from agentic_qa.interfaces.http.app import create_app
from agentic_qa.interfaces.http.authorisation import OPEN_PATHS
from tests.fakes.repositories import InMemoryStore
from tests.fakes.unit_of_work import InMemoryUnitOfWork
from tests.http.test_api_contract import asgi_client

REFUSALS = {401, 403}

PLACEHOLDERS = {
    "project_id": "p-does-not-exist",
    "run_id": "r-does-not-exist",
    "environment_id": "e-does-not-exist",
    "story_id": "s-does-not-exist",
    "session_id": "sess-does-not-exist",
    "token_id": "tok-does-not-exist",
    "artifact_id": "a-does-not-exist",
    "plan_id": "pl-does-not-exist",
    "plan_version": "1",
    "schedule_id": "sch-does-not-exist",
    "cluster_id": "c-does-not-exist",
}
"""Ids nothing owns.

Deliberately: a guard must refuse *before* the handler looks anything up, so a route that
answers `404` here is a route that did its lookup first — which means an unauthenticated
caller learned whether an id exists.
"""


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    store = InMemoryStore()
    async with asgi_client(Container(unit_of_work=lambda: InMemoryUnitOfWork(store))) as http:
        yield http


def routes() -> Iterable[tuple[str, str]]:
    """Every route the application documents, as (method, concrete path).

    Read from the OpenAPI document rather than by walking `app.routes`, and that is not a
    stylistic choice. FastAPI keeps an included router in `app.routes` as a container
    rather than splicing its routes in, so a tree walk found `/health` and nothing else —
    every assertion below would have passed against an application the test never
    visited. `test_the_application_actually_has_routes` is what caught it.

    The document is also what ADR 0020 promises this test reads, and it is stable across
    FastAPI's internals in a way that private route classes are not.
    """
    app = create_app(Container(unit_of_work=lambda: InMemoryUnitOfWork(InMemoryStore())))
    for template, operations in app.openapi()["paths"].items():
        path = template
        for name, value in PLACEHOLDERS.items():
            path = path.replace("{" + name + "}", value)
        if "{" in path:
            raise AssertionError(
                f"{template} has a path parameter this test does not know how to fill; "
                "add it to PLACEHOLDERS so the route is actually exercised"
            )
        for method in operations:
            if method.upper() in {"HEAD", "OPTIONS"}:
                continue
            yield method.upper(), path


ROUTES = sorted(set(routes()))


def test_the_application_actually_has_routes() -> None:
    # A bug in the collector would make every assertion below vacuously true, which is
    # the failure mode of this kind of test.
    assert len(ROUTES) > 15


@pytest.mark.parametrize(("method", "path"), ROUTES)
async def test_no_route_answers_without_a_token(
    client: httpx.AsyncClient, method: str, path: str
) -> None:
    if path in OPEN_PATHS:
        pytest.skip(f"{path} is deliberately open")

    response = await client.request(method, path, json={})

    assert response.status_code in REFUSALS, (
        f"{method} {path} answered {response.status_code} without a token"
    )


@pytest.mark.parametrize("path", sorted(OPEN_PATHS))
async def test_an_open_route_stays_open(client: httpx.AsyncClient, path: str) -> None:
    # `/health` is what the container's healthcheck and any proxy call. Guarding it by
    # accident would take the deployment down in a way that looks like the app crashing.
    response = await client.get(path)

    assert response.status_code == 200


async def test_the_refusal_names_the_code_the_cli_already_knows(
    client: httpx.AsyncClient,
) -> None:
    # `AUTH_REQUIRED` and exit code 3 were reserved in the CLI's contract long before
    # there was a server to send them. Using any other code would mean a client change.
    response = await client.get("/api/v1/projects")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


async def test_a_malformed_header_is_refused_like_a_missing_one(
    client: httpx.AsyncClient,
) -> None:
    for header in ("", "Bearer", "Bearer   ", "Basic abc", "roveqa_something"):
        response = await client.get("/api/v1/projects", headers={"Authorization": header})

        assert response.status_code == 401, header


async def test_an_unknown_token_is_refused_without_saying_it_was_close(
    client: httpx.AsyncClient,
) -> None:
    # The same answer as no token at all. Distinguishing them would be an oracle, and
    # there is nothing a legitimate caller does differently between the two.
    missing = await client.get("/api/v1/projects")
    unknown = await client.get(
        "/api/v1/projects", headers={"Authorization": "Bearer roveqa_nobody-issued-this"}
    )

    assert unknown.status_code == missing.status_code
    assert unknown.json()["error"]["message"] == missing.json()["error"]["message"]
