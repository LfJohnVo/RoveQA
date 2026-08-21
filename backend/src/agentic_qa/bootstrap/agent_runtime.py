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

from agentic_qa.application.ports.artifacts import ArtifactRepository
from agentic_qa.application.ports.browser import BrowserGateway
from agentic_qa.application.ports.deep_analysis import DeepAnalyst
from agentic_qa.application.ports.episodes import EpisodeRunner
from agentic_qa.bootstrap.settings import Settings
from agentic_qa.domain.inference.tasks import InferenceBudget, ModelCapability
from agentic_qa.infrastructure.agent.langgraph.checkpointer import open_checkpointer
from agentic_qa.infrastructure.agent.langgraph.episode_runner import LangGraphEpisodeRunner
from agentic_qa.infrastructure.browser.playwright.gateway import (
    DEFAULT_NAVIGATION_TIMEOUT_MS,
    start_browser_session,
)
from agentic_qa.infrastructure.cache.redis.semaphores import RedisResourceSemaphore
from agentic_qa.infrastructure.inference.airllm.gateway import AirLLMDeepAnalyst
from agentic_qa.infrastructure.inference.router import ModelEndpoint, ModelRouter
from agentic_qa.infrastructure.inference.vllm.gateway import VLLMModelGateway

logger = logging.getLogger(__name__)

FAST_ENDPOINT_NAME = "vllm-fast"
DEEP_ENDPOINT_NAME = "deep"


def build_model_router(settings: Settings) -> ModelRouter | None:
    """None when no endpoint is configured at all — an honest absence, not a fake model.

    The capabilities are genuinely independent, and each absence costs exactly one
    thing. No fast endpoint means no episodes; no deep endpoint means no hypotheses.
    A machine configured with only the deep model — the sensible way to run analysis on
    a second box — still gets a router, because refusing to build one there would make
    a fully configured capability unreachable.
    """
    endpoints = []
    if settings.vllm_base_url and settings.vllm_model:
        endpoints.append(
            ModelEndpoint(
                name=FAST_ENDPOINT_NAME,
                base_url=settings.vllm_base_url,
                model=settings.vllm_model,
                capability=ModelCapability.FAST,
                max_concurrency=settings.model_max_concurrency,
                budget=InferenceBudget(timeout_seconds=settings.model_timeout_seconds),
            )
        )
    else:
        logger.info("no fast model endpoint configured; the worker will not run episodes")

    if settings.deep_base_url and settings.deep_model:
        endpoints.append(
            ModelEndpoint(
                name=DEEP_ENDPOINT_NAME,
                base_url=settings.deep_base_url,
                model=settings.deep_model,
                capability=ModelCapability.DEEP,
                # One at a time: a model streamed layer by layer already owns the card
                # it runs on, and a second concurrent call would just make both slower.
                max_concurrency=1,
                budget=InferenceBudget(
                    timeout_seconds=settings.deep_timeout_seconds,
                    max_output_tokens=settings.deep_max_output_tokens,
                    # No transport retry. Re-sending a call that costs minutes doubles
                    # the wait for an endpoint that has already shown it cannot answer.
                    max_attempts=1,
                ),
            )
        )
    else:
        logger.info("no deep endpoint configured; failure triage runs without hypotheses")

    return ModelRouter(endpoints) if endpoints else None


def build_deep_analyst(
    *, router: ModelRouter, redis: Redis, http: httpx.AsyncClient
) -> DeepAnalyst | None:
    """None when nothing serves DEEP. Callers treat that as "no hypothesis", never as
    an error: deep analysis is an addition to a run's findings, not a precondition."""
    if not router.serves(ModelCapability.DEEP):
        return None
    return AirLLMDeepAnalyst(router=router, http=http, semaphore=RedisResourceSemaphore(redis))


def build_episode_runner(
    settings: Settings,
    *,
    router: ModelRouter,
    redis: Redis,
    http: httpx.AsyncClient,
    artifacts: ArtifactRepository | None = None,
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
        session = await start_browser_session(
            headless=settings.browser_headless,
            # `or` on purpose: an unset override means the adapter's own default, so the
            # number lives in exactly one place instead of two that can drift.
            navigation_timeout_ms=(
                settings.browser_navigation_timeout_ms or DEFAULT_NAVIGATION_TIMEOUT_MS
            ),
        )
        try:
            yield session.gateway
        finally:
            await session.aclose()

    return LangGraphEpisodeRunner(
        model=model,
        browser_factory=browser_factory,
        checkpointer_factory=lambda: open_checkpointer(settings.postgres_dsn),
        artifacts=artifacts,
    )
