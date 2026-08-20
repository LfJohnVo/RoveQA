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

from agentic_qa.application.ports.artifacts import ArtifactRepository
from agentic_qa.application.ports.browser import BrowserGateway
from agentic_qa.application.ports.episodes import EpisodeRequest, EpisodeResult
from agentic_qa.application.ports.models import ModelGateway
from agentic_qa.application.services.guarded_browser import GuardedBrowserGateway
from agentic_qa.domain.agent.state import AgentState
from agentic_qa.domain.exploration.comparison import StateMap
from agentic_qa.domain.exploration.frontier import ExplorationReport, FrontierSnapshot
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
        artifacts: ArtifactRepository | None = None,
    ) -> None:
        self._model = model
        self._browser_factory = browser_factory
        self._checkpointer_factory = checkpointer_factory
        self._artifacts = artifacts

    async def run_episode(self, request: EpisodeRequest) -> EpisodeResult:
        async with self._checkpointer_factory() as checkpointer, self._browser_factory() as raw:
            guarded = GuardedBrowserGateway(raw, request.policy)
            graph = build_agent_graph(
                browser=guarded,
                model=self._model,
                checkpointer=checkpointer,
                assertions=request.assertions,
                hints=request.verification_hints,
                memory=request.memory,
                artifacts=self._artifacts,
                # An exploring episode replaces the planner with the frontier. Both are
                # never active at once, and which one applies is decided here, once.
                exploration_budget=request.exploration,
                # Always: the policy bounds every episode, and decides what an exploring
                # one may offer itself.
                policy=request.policy,
                run_id=request.run_id,
                # One evidence set per episode: a bundle must never mix two, and
                # deriving the id keeps that true without anyone remembering to.
                evidence_set_id=f"{request.run_id}-e{request.episode_index}",
            )
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
            report = final.get("exploration_report")

            return EpisodeResult(
                # Phase 05 executes one goal per episode; multi-episode planning
                # arrives with the story workflow in Phase 07.
                more_work=False,
                graph_checkpoint_id=snapshot.config["configurable"].get("checkpoint_id"),
                safe_point=final.get("safe_point"),
                failure_reason=agent.failure_reason,
                criterion_results=final.get("criterion_results", ()),
                evidence=final.get("evidence", ()),
                # Read from the live browser, not from the agent's last observation:
                # the recovery point has to name where the page actually ended up.
                observed_url=await raw.current_url(),
                state_map=_state_map(final.get("exploration"), report),
                exploration_report=report,
            )


async def _has_pending_state(graph: Any, config: RunnableConfig) -> bool:
    """True when this thread already has checkpointed state to continue from."""
    snapshot = await graph.aget_state(config)
    return bool(snapshot.next)


def _state_map(
    snapshot: FrontierSnapshot | None, report: ExplorationReport | None
) -> StateMap | None:
    """What an exploring episode mapped, or nothing for a planned one.

    `complete` comes from the report rather than from the map's size: a map of twelve
    states that stopped on a budget and a map of twelve states that ran out of places
    to go look identical, and only the second one can support the claim that a state
    missing next time was removed.
    """
    if snapshot is None or report is None:
        return None
    return StateMap(states=snapshot.visited, complete=report.complete)
