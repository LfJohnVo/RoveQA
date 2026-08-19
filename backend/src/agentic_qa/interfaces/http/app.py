"""FastAPI application factory."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response

from agentic_qa.bootstrap.container import Container, build_container, connect_workflows
from agentic_qa.bootstrap.settings import Settings
from agentic_qa.interfaces.http.errors import register_error_handlers
from agentic_qa.interfaces.http.request_context import (
    REQUEST_ID_HEADER,
    accept_inbound_request_id,
    set_request_id,
)
from agentic_qa.interfaces.http.routers import artifacts, plans, projects, realtime, runs


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
    app.include_router(projects.router)
    app.include_router(artifacts.router)
    app.include_router(plans.router)
    app.include_router(runs.router)
    app.include_router(realtime.router)

    @app.get("/health", tags=["ops"])
    async def health() -> dict[str, str]:
        """Liveness only. Readiness against dependencies lands with the worker."""
        return {"status": "ok"}

    return app
