"""A credential on a page must not survive into anything this system keeps.

Phase 09 redacts what goes into *memory*. This is the other half, and the one nobody
had checked: a run walks a page that renders an API key and links to a URL carrying a
token, and afterwards the value must not appear in an observation, a stored URL, a
state map, a log line or an artifact's name.

The fixture is the point. A secret nobody planted is a secret nobody can prove was not
leaked, so `LEAKED_TOKEN` is planted in two shapes real applications actually produce:
rendered text, and a query parameter.
"""

import logging
from collections.abc import AsyncIterator

import pytest

from agentic_qa.application.services.guarded_browser import GuardedBrowserGateway
from agentic_qa.domain.agent.state import AgentState
from agentic_qa.domain.browser.actions import ActionTarget, BrowserAction, BrowserActionType
from agentic_qa.domain.exploration.frontier import ExplorationBudget, FrontierSnapshot
from agentic_qa.domain.projects.run_policy import RunPolicy
from agentic_qa.infrastructure.agent.langgraph.graph import build_agent_graph
from agentic_qa.infrastructure.browser.playwright.gateway import (
    BrowserSession,
    start_browser_session,
)
from tests.fakes.agent import ScriptedModelGateway
from tests.target_app.app import LEAKED_TOKEN, TargetState
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


def policy_for(base_url: str) -> RunPolicy:
    return RunPolicy(
        policy_id="pol-secrets",
        project_id="proj-secrets",
        allowed_origins=(base_url,),
        max_duration_seconds=60,
        max_actions=10,
        max_model_calls=0,
    )


async def explore_the_secrets_page(
    session: BrowserSession, base_url: str
) -> tuple[AgentState, FrontierSnapshot]:
    policy = policy_for(base_url)
    await session.gateway.page.goto(f"{base_url}/secrets")
    graph = build_agent_graph(
        browser=GuardedBrowserGateway(session.gateway, policy),
        model=ScriptedModelGateway(script=[]),
        policy=policy,
        exploration_budget=ExplorationBudget(
            max_actions=6, max_states=10, max_depth=2, max_duration_seconds=30
        ),
    )
    final = await graph.ainvoke(
        {"agent": AgentState(run_id="run-secrets", goal="explore the application")}
    )
    agent = final["agent"]
    assert isinstance(agent, AgentState)
    snapshot = final["exploration"]
    assert isinstance(snapshot, FrontierSnapshot)
    return agent, snapshot


async def test_a_token_in_a_url_does_not_reach_the_state_map(
    session: BrowserSession, target: tuple[str, TargetState]
) -> None:
    """A state map is kept for weeks and compared night after night.

    A session token in a stored URL would outlive the session that issued it, in a
    table nobody thinks of as holding credentials.
    """
    base_url, _state = target

    _agent, snapshot = await explore_the_secrets_page(session, base_url)

    for page in snapshot.visited:
        assert LEAKED_TOKEN not in page.url, page.url
        assert LEAKED_TOKEN not in page.title
        assert not any(LEAKED_TOKEN in key for key in page.affordance_keys)


async def test_a_rendered_credential_does_not_reach_an_observation(
    session: BrowserSession, target: tuple[str, TargetState]
) -> None:
    base_url, _state = target

    agent, _snapshot = await explore_the_secrets_page(session, base_url)

    assert LEAKED_TOKEN not in agent.last_observation
    assert all(LEAKED_TOKEN not in step.detail for step in agent.recent_steps)
    assert all(LEAKED_TOKEN not in summary.summary for summary in agent.episode_summaries)


async def test_a_credential_does_not_reach_the_logs(
    session: BrowserSession,
    target: tuple[str, TargetState],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Logs travel further than any other output here — to a file, a terminal, a
    shipper. A secret in one is a secret in all of them."""
    base_url, _state = target

    with caplog.at_level(logging.DEBUG, logger="agentic_qa"):
        await explore_the_secrets_page(session, base_url)

    leaked = [
        record.getMessage() for record in caplog.records if LEAKED_TOKEN in record.getMessage()
    ]
    assert leaked == []


async def test_extracting_the_secret_is_still_possible_and_still_contained(
    session: BrowserSession, target: tuple[str, TargetState]
) -> None:
    """The agent may *read* a secret — that is what a page shows — but reading is not
    keeping. What comes back is data for the caller to decide about, and nothing here
    writes it anywhere durable on its own."""
    base_url, _state = target
    guarded = GuardedBrowserGateway(session.gateway, policy_for(base_url))
    await guarded.execute(
        BrowserAction(
            type=BrowserActionType.NAVIGATE,
            intent="open settings",
            target=ActionTarget(url=f"{base_url}/secrets"),
        )
    )

    extracted = await guarded.execute(
        BrowserAction(
            type=BrowserActionType.EXTRACT,
            intent="read the api key line",
            target=ActionTarget(text="API key:"),
        )
    )

    assert extracted.extracted_text is not None
    assert LEAKED_TOKEN in extracted.extracted_text
    # And the page description — the thing that *is* stored — does not carry it.
    described = await guarded.describe_page()
    assert LEAKED_TOKEN not in described.url
    assert all(LEAKED_TOKEN not in affordance.name for affordance in described.affordances)
