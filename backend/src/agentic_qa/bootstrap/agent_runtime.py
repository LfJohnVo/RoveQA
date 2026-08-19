"""Wiring for the agent runtime: model, browser and checkpointer.

Separate from `container` because only the worker needs it. The API answers questions
about runs; it never launches Chromium or calls a model, and a composition root that
built one for it would be handing out capabilities nobody asked for.

Nothing here starts eagerly. The factories are called once per episode, so a worker
that never runs one never launches a browser.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from redis.asyncio import Redis

from agentic_qa.application.ports.browser import BrowserGateway
from agentic_qa.application.ports.episodes import EpisodeRunner
from agentic_qa.bootstrap.settings import Settings
from agentic_qa.domain.inference.tasks import InferenceBudget, ModelCapability
from agentic_qa.infrastructure.agent.langgraph.checkpointer import open_checkpointer
from agentic_qa.infrastructure.agent.langgraph.episode_runner import LangGraphEpisodeRunner
from agentic_qa.infrastructure.browser.playwright.gateway import start_browser_session
from agentic_qa.infrastructure.cache.redis.semaphores import RedisResourceSemaphore
from agentic_qa.infrastructure.inference.router import ModelEndpoint, ModelRouter
from agentic_qa.infrastructure.inference.vllm.gateway import VLLMModelGateway

logger = logging.getLogger(__name__)

FAST_ENDPOINT_NAME = "vllm-fast"


def build_model_router(settings: Settings) -> ModelRouter | None:
    """None when no endpoint is configured — an honest absence, not a fake model."""
    if not settings.vllm_base_url or not settings.vllm_model:
        logger.info("no model endpoint configured; the worker will not run episodes")
        return None
    return ModelRouter(
        [
            ModelEndpoint(
                name=FAST_ENDPOINT_NAME,
                base_url=settings.vllm_base_url,
                model=settings.vllm_model,
                capability=ModelCapability.FAST,
                max_concurrency=settings.model_max_concurrency,
                budget=InferenceBudget(timeout_seconds=settings.model_timeout_seconds),
            )
        ]
        # DEEP (AirLLM, Phase 11) and POOLING (embeddings, Phase 09) endpoints register
        # here too; the router is already indexed by capability to receive them.
    )


def build_episode_runner(
    settings: Settings, *, router: ModelRouter, redis: Redis, http: httpx.AsyncClient
) -> EpisodeRunner:
    model = VLLMModelGateway(
        router=router,
        http=http,
        # Redis, not a local counter: the limit belongs to the model server, and two
        # workers each counting to two would send four calls to a box that fits two.
        semaphore=RedisResourceSemaphore(redis),
    )

    @asynccontextmanager
    async def browser_factory() -> AsyncIterator[BrowserGateway]:
        session = await start_browser_session(headless=settings.browser_headless)
        try:
            yield session.gateway
        finally:
            await session.aclose()

    return LangGraphEpisodeRunner(
        model=model,
        browser_factory=browser_factory,
        checkpointer_factory=lambda: open_checkpointer(settings.postgres_dsn),
    )
