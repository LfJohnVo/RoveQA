"""Run one episode of the agent graph.

Resume is the default path, not a special case: the graph is always invoked against
the run's own thread id, so a worker that takes over an interrupted episode continues
from the checkpoint instead of starting again.

The browser is obtained already wrapped in the run's policy. This adapter never sees
an unguarded gateway, so it cannot hand one to the graph even by mistake.
"""

import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver

from agentic_qa.application.ports.browser import BrowserGateway
from agentic_qa.application.ports.episodes import EpisodeRequest, EpisodeResult
from agentic_qa.application.ports.models import ModelGateway
from agentic_qa.application.services.guarded_browser import GuardedBrowserGateway
from agentic_qa.domain.agent.state import AgentState
from agentic_qa.infrastructure.agent.langgraph.graph import build_agent_graph

logger = logging.getLogger(__name__)

BrowserFactory = Callable[[], AbstractAsyncContextManager[BrowserGateway]]
CheckpointerFactory = Callable[[], AbstractAsyncContextManager[BaseCheckpointSaver[str]]]


def thread_id_for(run_id: str) -> str:
    """One graph thread per run: episodes of one run share it, runs never share."""
    return f"run:{run_id}"


class LangGraphEpisodeRunner:
    def __init__(
        self,
        *,
        model: ModelGateway,
        browser_factory: BrowserFactory,
        checkpointer_factory: CheckpointerFactory,
    ) -> None:
        self._model = model
        self._browser_factory = browser_factory
        self._checkpointer_factory = checkpointer_factory

    async def run_episode(self, request: EpisodeRequest) -> EpisodeResult:
        async with self._checkpointer_factory() as checkpointer, self._browser_factory() as raw:
            guarded = GuardedBrowserGateway(raw, request.policy)
            graph = build_agent_graph(browser=guarded, model=self._model, checkpointer=checkpointer)
            config: RunnableConfig = {"configurable": {"thread_id": thread_id_for(request.run_id)}}

            resuming = await _has_pending_state(graph, config)
            initial = (
                None
                if resuming
                else {
                    "agent": AgentState(
                        run_id=request.run_id,
                        goal=request.goal,
                        episode_index=request.episode_index,
                    )
                }
            )
            if resuming:
                logger.info("resuming run %s from its checkpoint", request.run_id)

            final = await graph.ainvoke(initial, config)
            snapshot = await graph.aget_state(config)
            agent: AgentState = final["agent"]

            return EpisodeResult(
                # Phase 05 executes one goal per episode; multi-episode planning
                # arrives with the story workflow in Phase 07.
                more_work=False,
                graph_checkpoint_id=snapshot.config["configurable"].get("checkpoint_id"),
                safe_point=final.get("safe_point"),
                failure_reason=agent.failure_reason,
            )


async def _has_pending_state(graph: Any, config: RunnableConfig) -> bool:
    """True when this thread already has checkpointed state to continue from."""
    snapshot = await graph.aget_state(config)
    return bool(snapshot.next)
