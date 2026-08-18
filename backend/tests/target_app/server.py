"""Serve the deterministic target app on an ephemeral port for browser tests."""

import asyncio
import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn

from tests.target_app.app import TargetState, create_target_app


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port: int = probe.getsockname()[1]
        return port


@asynccontextmanager
async def running_target_app() -> AsyncIterator[tuple[str, TargetState]]:
    """Yield the base URL and the app's state, so tests can assert real side effects."""
    state = TargetState()
    port = _free_port()
    config = uvicorn.Config(
        create_target_app(state), host="127.0.0.1", port=port, log_level="warning"
    )
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    try:
        while not server.started:
            await asyncio.sleep(0.02)
        yield f"http://127.0.0.1:{port}", state
    finally:
        server.should_exit = True
        await task
