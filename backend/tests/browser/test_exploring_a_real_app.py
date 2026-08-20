"""Exploring a real application, in a real browser, under a real policy.

This is the Phase 12 gate that only reality can answer: an exploration of an actual
site terminates, maps more than the page it started on, and stays inside the origins
the policy allows — while calling no model at all.

The read-only case matters most, because it is the default a team would start with: an
explorer must be able to map an application it is not allowed to change.
"""

from collections.abc import AsyncIterator

import pytest

from agentic_qa.application.services.guarded_browser import GuardedBrowserGateway
from agentic_qa.domain.agent.state import AgentState
from agentic_qa.domain.exploration.frontier import ExplorationBudget
from agentic_qa.domain.projects.run_policy import RunPolicy
from agentic_qa.infrastructure.agent.langgraph.graph import build_agent_graph
from agentic_qa.infrastructure.browser.playwright.gateway import (
    BrowserSession,
    start_browser_session,
)
from tests.fakes.agent import ScriptedModelGateway
from tests.target_app.app import TargetState
from tests.target_app.server import running_target_app


@pytest.fixture
async def target() -> AsyncIterator[tuple[str, TargetState]]:
    async with running_target_app() as running:
        yield running


@pytest.fixture
async def session() -> AsyncIterator[BrowserSession]:
    browser = await start_browser_session(headless=True)
    try:
        yield browser
    finally:
        await browser.aclose()


def read_only_policy(base_url: str) -> RunPolicy:
    return RunPolicy(
        policy_id="pol-explore",
        project_id="proj-explore",
        allowed_origins=(base_url,),
        max_duration_seconds=120,
        max_actions=25,
        max_model_calls=0,
        destructive_actions=False,
    )


async def explore(
    session: BrowserSession, base_url: str, *, policy: RunPolicy, max_actions: int = 12
) -> tuple[AgentState, ScriptedModelGateway]:
    model = ScriptedModelGateway(script=[])
    await session.gateway.page.goto(base_url)
    graph = build_agent_graph(
        browser=GuardedBrowserGateway(session.gateway, policy),
        model=model,
        # The same policy the guard holds. It bounds the episode, and the frontier
        # consults it before offering anything — so a read-only run maps the
        # application instead of stopping at the first button.
        policy=policy,
        exploration_budget=ExplorationBudget(
            max_actions=max_actions,
            max_states=20,
            max_depth=3,
            max_duration_seconds=60,
        ),
    )
    result = await graph.ainvoke(
        {"agent": AgentState(run_id="run-explore", goal="explore the application")}
    )
    agent = result["agent"]
    assert isinstance(agent, AgentState)
    return agent, model


async def test_it_maps_a_real_application_and_stops(
    session: BrowserSession, target: tuple[str, TargetState]
) -> None:
    base_url, _state = target

    agent, model = await explore(session, base_url, policy=read_only_policy(base_url))

    # It ended by itself. Which reason is legitimate to vary — a real site may exhaust
    # the frontier or hit the action budget — but "still running" is not an outcome.
    assert agent.episode_summaries
    summary = agent.episode_summaries[-1]
    assert summary.steps_taken > 1
    # The claim that makes exploration cheap: zero inference.
    assert model.calls == 0


async def test_a_read_only_policy_can_still_map_the_application(
    session: BrowserSession, target: tuple[str, TargetState]
) -> None:
    """Links are followed by navigating, which changes nothing.

    Without this an explorer would need `destructive_actions: true` to see anything,
    and the safe default would be the useless one.
    """
    base_url, _state = target

    agent, _model = await explore(session, base_url, policy=read_only_policy(base_url))

    assert agent.episode_summaries[-1].steps_taken > 1
    # Nothing was denied, because nothing forbidden was ever offered. A read-only
    # exploration that queued buttons would end at the first one it met.
    assert agent.failure_reason is None


async def test_it_cannot_wander_outside_the_allowed_origin(
    session: BrowserSession, target: tuple[str, TargetState]
) -> None:
    """The page under test is untrusted data, links included.

    Exploration widens nothing: an off-origin link is refused by the same guard that
    refuses one a planner proposed.
    """
    base_url, _state = target
    elsewhere = RunPolicy(
        policy_id="pol-elsewhere",
        project_id="proj-explore",
        # Deliberately not the target: every navigation it tries must be refused.
        allowed_origins=("https://not-the-target.test",),
        max_duration_seconds=120,
        max_actions=25,
        max_model_calls=0,
    )

    agent, _model = await explore(session, base_url, policy=elsewhere, max_actions=4)

    # Nothing was taken at all: every link on the page leads somewhere this run may
    # not go, so the frontier was empty from the start. Off-origin links are declined
    # before they are attempted, by the same guard that would have refused them.
    assert agent.episode_summaries[-1].steps_taken == 0
    assert agent.failure_reason is None
