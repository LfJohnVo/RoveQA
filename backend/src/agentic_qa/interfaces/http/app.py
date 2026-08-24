"""FastAPI application factory."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, Response

from agentic_qa.bootstrap.container import Container, build_container, connect_workflows
from agentic_qa.bootstrap.settings import Settings
from agentic_qa.interfaces.http.authorisation import authorise
from agentic_qa.interfaces.http.errors import register_error_handlers
from agentic_qa.interfaces.http.request_context import (
    REQUEST_ID_HEADER,
    accept_inbound_request_id,
    set_request_id,
)
from agentic_qa.interfaces.http.routers import (
    artifacts,
    exploration,
    memory,
    meta,
    plans,
    projects,
    realtime,
    runs,
    schedules,
    sessions,
    triage,
)


def create_app(container: Container | None = None) -> FastAPI:
    """Build the API. Passing a container lets tests wire their own adapters."""
    injected = container

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if injected is None:
            settings = Settings.from_env()
            container = await connect_workflows(build_container(settings), settings)
            app.state.container = container
            try:
                yield
            finally:
                # Only dispose what we created; an injected container outlives the app.
                await container.aclose()
        else:
            yield

    app = FastAPI(title="RoveQA control plane", version="0.1.0", lifespan=lifespan)
    if injected is not None:
        # Set eagerly: an injected container must not depend on lifespan running,
        # so tests can drive the app over a plain ASGI transport.
        app.state.container = injected

    @app.middleware("http")
    async def request_id_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = accept_inbound_request_id(request.headers.get(REQUEST_ID_HEADER))
        set_request_id(request_id)
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response

    register_error_handlers(app)

    # One list, one dependency, applied at inclusion rather than on each handler. A new
    # endpoint inherits the check by living in a router that is already here, and the
    # structural test in `tests/http/test_every_route_is_guarded.py` fails on any route
    # that ends up neither guarded nor named in `OPEN_PATHS` (ADR 0020).
    guarded = [
        projects.router,
        artifacts.router,
        meta.router,
        memory.router,
        plans.router,
        runs.router,
        runs.by_project,
        sessions.router,
        triage.router,
        schedules.router,
        exploration.router,
    ]
    for router in guarded:
        app.include_router(router, dependencies=[Depends(authorise)])

    # The websocket route is included without the HTTP dependency: FastAPI resolves
    # dependencies for a socket differently, and a bearer header is not something a
    # browser can attach to one. Its own guard lands with the console's auth, and until
    # then it is on the exempt list where the test can see it rather than silently open.
    app.include_router(realtime.router)

    @app.get("/health", tags=["ops"])
    async def health() -> dict[str, str]:
        """Liveness only. Readiness against dependencies lands with the worker."""
        return {"status": "ok"}

    return app
