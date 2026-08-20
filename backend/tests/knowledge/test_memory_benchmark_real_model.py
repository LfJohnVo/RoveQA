"""Cold versus warm against the real model.

`test_memory_benchmark.py` measures the mechanism: retrieval reaches the planner and
acting on it is cheaper. This measures the thing that mechanism exists for — whether a
real language model, given a remembered route in its prompt, actually stops exploring.

Skipped without `VLLM_BASE_URL`, like every other real-model test here. A skipped
measurement is honest; a measurement taken from a double and reported as a model result
is not.

Everything is real: Chromium, the target app, the LangGraph agent, the vLLM endpoint,
and the same `MemoryContext` a production run would receive. Only the memory itself is
constructed directly rather than earned over two prior runs — three full browser runs
per assertion would make this too slow to keep in the suite, and what is under test is
the model's reaction to memory, not the promotion path (covered elsewhere).
"""

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx
import pytest

from agentic_qa.application.ports.episodes import EpisodeRequest
from agentic_qa.application.ports.models import (
    CriterionJudgement,
    JudgementRequest,
    PlannedAction,
    PlanningRequest,
)
from agentic_qa.domain.inference.tasks import InferenceBudget, ModelCapability
from agentic_qa.domain.knowledge.compatibility import Compatibility
from agentic_qa.domain.knowledge.experience import (
    CandidateKind,
    CandidateStatus,
    KnowledgeExperienceCandidate,
    Provenance,
    Quality,
    Validity,
)
from agentic_qa.domain.knowledge.memory_context import MemoryItem, build_item
from agentic_qa.domain.projects.run_policy import RunPolicy
from agentic_qa.infrastructure.agent.langgraph.checkpointer import open_checkpointer
from agentic_qa.infrastructure.agent.langgraph.episode_runner import LangGraphEpisodeRunner
from agentic_qa.infrastructure.browser.playwright.gateway import start_browser_session
from agentic_qa.infrastructure.inference.router import ModelEndpoint, ModelRouter
from agentic_qa.infrastructure.inference.vllm.gateway import VLLMModelGateway
from tests.conftest import postgres_test_dsn
from tests.fakes.semaphores import InMemoryResourceSemaphore

NOW = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)

GOAL = "confirm the records page is open and shows its create-record form"
"""Phrased as an outcome, not a path. Naming `/records` in the goal would let a cold
run navigate straight there and the benchmark would be measuring the wording."""

MIN_REDUCTION = 0.20


def endpoint() -> tuple[str, str] | None:
    base_url = os.environ.get("VLLM_BASE_URL")
    model = os.environ.get("VLLM_MODEL")
    return (base_url, model) if base_url and model else None


@dataclass
class CountingModel:
    """The real gateway, with the two numbers the benchmark needs.

    Counting at this seam rather than inside the client is deliberate: what the gate
    asks about is planner *decisions*, and a retry or a token count would answer a
    different question.
    """

    inner: Any
    planner_calls: int = 0
    judgements: int = 0
    intents: list[str] = field(default_factory=list)

    async def next_action(self, request: PlanningRequest) -> PlannedAction:
        self.planner_calls += 1
        decision: PlannedAction = await self.inner.next_action(request)
        if decision.action is not None:
            self.intents.append(decision.action.intent)
        return decision

    async def judge(self, request: JudgementRequest) -> CriterionJudgement:
        self.judgements += 1
        result: CriterionJudgement = await self.inner.judge(request)
        return result


def remembered_route(url: str, project_id: str) -> MemoryItem:
    """A promoted, observed route — what two agreeing runs would have produced."""
    candidate = KnowledgeExperienceCandidate(
        candidate_id=f"cand-{uuid4()}",
        project_id=project_id,
        environment_id="staging",
        kind=CandidateKind.ROUTE,
        observed=True,
        model_derived=False,
        created_at=NOW,
        provenance=Provenance(source_run_id="run-earlier"),
        validity=Validity(valid_from=NOW),
        payload={"url": url, "summary": f"reachable: {url}"},
        status=CandidateStatus.PROMOTED,
        quality=Quality(support_count=2, success_count=2, last_verified_at=NOW),
    )
    return build_item(candidate, compatibility=Compatibility.COMPATIBLE, now=NOW)


@dataclass
class Measurement:
    planner_calls: int
    actions: list[str]
    final_url: str

    @property
    def reached(self) -> bool:
        """Where the browser actually ended up.

        Read from the episode's observed URL rather than from the model's own words:
        an action's `intent` is the planner describing itself, and using it would make
        the benchmark grade the model on its narration instead of on where it went.
        """
        return self.final_url.rstrip("/").endswith("/records")


@asynccontextmanager
async def _checkpointer() -> AsyncIterator[Any]:
    """The real LangGraph saver, as the worker uses it.

    Not stubbed out: the episode runner asks the graph for prior state before deciding
    whether it is resuming, so a graph without a checkpointer cannot run at all. Both
    runs pay the same setup cost, which cancels in a difference.
    """
    async with open_checkpointer(postgres_test_dsn()) as saver:
        yield saver


@asynccontextmanager
async def episode_runner(base_url: str, model: str) -> AsyncIterator[Any]:
    async with httpx.AsyncClient() as http:
        router = ModelRouter(
            [
                ModelEndpoint(
                    name="vllm-fast",
                    base_url=base_url,
                    model=model,
                    capability=ModelCapability.FAST,
                    max_concurrency=1,
                    budget=InferenceBudget(timeout_seconds=120.0),
                )
            ]
        )
        counting = CountingModel(
            VLLMModelGateway(router=router, http=http, semaphore=InMemoryResourceSemaphore())
        )

        @asynccontextmanager
        async def browser_factory() -> AsyncIterator[Any]:
            session = await start_browser_session(headless=True)
            try:
                yield session.gateway
            finally:
                await session.aclose()

        yield counting, browser_factory


async def measure(
    target_url: str, *, memory: tuple[MemoryItem, ...], max_steps: int
) -> Measurement:
    configured = endpoint()
    assert configured is not None
    base_url, model = configured

    async with episode_runner(base_url, model) as (counting, browser_factory):
        runner = LangGraphEpisodeRunner(
            model=counting,
            browser_factory=browser_factory,
            checkpointer_factory=_checkpointer,
        )
        result = await runner.run_episode(
            EpisodeRequest(
                run_id=f"bench-{uuid4()}",
                goal=f"{GOAL}. Start at {target_url}",
                episode_index=0,
                policy=RunPolicy(
                    policy_id="pol-bench",
                    project_id="proj-bench",
                    allowed_origins=(target_url,),
                    max_duration_seconds=300,
                    max_actions=max_steps,
                    max_model_calls=max_steps + 2,
                    # The model may escalate any action to `side_effect`, and this one
                    # marks its navigations that way. A read-only policy would deny the
                    # first step of both runs and the benchmark would be measuring the
                    # policy rather than memory. The target app is disposable.
                    destructive_actions=True,
                ),
                memory=memory,
            )
        )

    return Measurement(
        planner_calls=counting.planner_calls,
        actions=list(counting.intents),
        final_url=result.observed_url or "",
    )


def run_benchmark() -> tuple[Measurement, Measurement]:
    from tests.target_app.server import running_target_app

    async def scenario() -> tuple[Measurement, Measurement]:
        async with running_target_app() as (target_url, _state):
            cold = await measure(target_url, memory=(), max_steps=8)
            warm = await measure(
                target_url,
                memory=(remembered_route(f"{target_url}/records", "proj-bench"),),
                max_steps=8,
            )
            return cold, warm

    return asyncio.run(scenario())


@pytest.mark.skipif(endpoint() is None, reason="set VLLM_BASE_URL and VLLM_MODEL")
def test_the_real_model_reacts_to_a_remembered_route() -> None:
    """The measurement the phase gate actually asks for.

    Reported rather than merely asserted: the numbers go in the eval document, and a
    result below the threshold is a finding about the model, not a broken test — so
    the failure message carries both runs.
    """
    cold, warm = run_benchmark()

    report = (
        f"cold: {cold.planner_calls} planner calls, {len(cold.actions)} actions "
        f"{cold.actions}, ended at {cold.final_url}\n"
        f"warm: {warm.planner_calls} planner calls, {len(warm.actions)} actions "
        f"{warm.actions}, ended at {warm.final_url}"
    )
    print(f"\n{report}")

    assert warm.reached, f"the warm run never reached the records page\n{report}"
    saved = (cold.planner_calls - warm.planner_calls) / cold.planner_calls
    assert saved >= MIN_REDUCTION, (
        f"the model saved {saved:.0%}, below the {MIN_REDUCTION:.0%} the gate requires\n{report}"
    )


@pytest.mark.skipif(endpoint() is None, reason="set VLLM_BASE_URL and VLLM_MODEL")
def test_memory_does_not_change_where_the_run_ends_up() -> None:
    # The failure a speed number hides: a warm run that is faster because it stopped
    # checking. Both runs have to arrive at the same place.
    cold, warm = run_benchmark()

    assert cold.reached == warm.reached
