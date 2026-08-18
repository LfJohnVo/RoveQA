"""The Playwright adapter against a real Chromium and the deterministic target app.

These are the tests that prove the typed actions and the policy actually work on a
browser, not just in the domain model.
"""

from collections.abc import AsyncIterator

import pytest

from agentic_qa.application.services.guarded_browser import (
    ActionDeniedError,
    GuardedBrowserGateway,
)
from agentic_qa.domain.browser.actions import (
    ActionTarget,
    BrowserAction,
    BrowserActionType,
    IdempotencyStrategy,
)
from agentic_qa.domain.projects.run_policy import RunPolicy
from agentic_qa.infrastructure.browser.playwright.gateway import (
    BrowserSession,
    start_browser_session,
)
from tests.target_app.app import VALID_PASSWORD, VALID_USER, TargetState
from tests.target_app.server import running_target_app


@pytest.fixture
async def target() -> AsyncIterator[tuple[str, TargetState]]:
    async with running_target_app() as running:
        yield running


@pytest.fixture
async def session() -> AsyncIterator[BrowserSession]:
    browser = await start_browser_session()
    try:
        yield browser
    finally:
        await browser.aclose()


def policy_for(base_url: str, *, destructive: bool = False) -> RunPolicy:
    return RunPolicy(
        policy_id="pol-browser",
        project_id="p-1",
        allowed_origins=(base_url,),
        max_duration_seconds=600,
        max_actions=100,
        max_model_calls=0,
        destructive_actions=destructive,
    )


def navigate(url: str) -> BrowserAction:
    return BrowserAction(
        type=BrowserActionType.NAVIGATE, intent="open the page", target=ActionTarget(url=url)
    )


def fill(label: str, value: str) -> BrowserAction:
    return BrowserAction(
        type=BrowserActionType.FILL,
        intent=f"type the {label.lower()}",
        target=ActionTarget(label=label),
        value=value,
        side_effect=True,
        idempotency_strategy=IdempotencyStrategy.VERIFY_BEFORE_RETRY,
        verification_strategy="the field shows the typed value",
    )


def click(name: str) -> BrowserAction:
    return BrowserAction(
        type=BrowserActionType.CLICK,
        intent=f"press {name}",
        target=ActionTarget(role="button", name=name),
        side_effect=True,
        idempotency_strategy=IdempotencyStrategy.VERIFY_BEFORE_RETRY,
        verification_strategy="the resulting page confirms the outcome",
    )


def assert_text(expected: str) -> BrowserAction:
    return BrowserAction(
        type=BrowserActionType.ASSERT_TEXT, intent=f"expect {expected}", value=expected
    )


async def test_navigation_and_text_assertion(
    target: tuple[str, TargetState], session: BrowserSession
) -> None:
    base_url, _ = target

    assert (await session.gateway.execute(navigate(f"{base_url}/"))).succeeded
    outcome = await session.gateway.execute(assert_text("Home"))

    assert outcome.succeeded is True
    assert outcome.current_url is not None


async def test_a_failing_assertion_reports_instead_of_raising(
    target: tuple[str, TargetState], session: BrowserSession
) -> None:
    """A wrong page is a finding, not a crash: the agent decides what it means."""
    base_url, _ = target
    await session.gateway.execute(navigate(f"{base_url}/"))

    outcome = await session.gateway.execute(assert_text("Definitely not on this page"))

    assert outcome.succeeded is False
    assert "text not found" in outcome.detail


async def test_semantic_locators_drive_a_real_form(
    target: tuple[str, TargetState], session: BrowserSession
) -> None:
    """Role and label locators, never coordinates."""
    base_url, _ = target
    gateway = session.gateway

    await gateway.execute(navigate(f"{base_url}/login"))
    await gateway.execute(fill("Email", VALID_USER))
    await gateway.execute(fill("Password", VALID_PASSWORD))
    await gateway.execute(click("Sign in"))

    assert (await gateway.execute(assert_text("Signed in as"))).succeeded


async def test_extract_reads_page_content(
    target: tuple[str, TargetState], session: BrowserSession
) -> None:
    base_url, _ = target
    await session.gateway.execute(navigate(f"{base_url}/"))

    outcome = await session.gateway.execute(
        BrowserAction(
            type=BrowserActionType.EXTRACT,
            intent="read the status",
            target=ActionTarget(text="ready"),
        )
    )

    assert outcome.extracted_text == "ready"


async def test_the_policy_blocks_navigation_outside_the_allowlist(
    target: tuple[str, TargetState], session: BrowserSession
) -> None:
    """The origin gate, enforced on the real adapter rather than only in the domain."""
    base_url, _ = target
    guarded = GuardedBrowserGateway(session.gateway, policy_for(base_url))

    assert (await guarded.execute(navigate(f"{base_url}/"))).succeeded

    with pytest.raises(ActionDeniedError):
        await guarded.execute(navigate("https://evil.test/exfiltrate"))

    # The browser never left the allowed page.
    assert base_url in (await guarded.current_url() or "")


async def test_untrusted_page_content_cannot_widen_the_policy(
    target: tuple[str, TargetState], session: BrowserSession
) -> None:
    """A page telling the agent to enable destructive actions changes nothing."""
    base_url, _ = target
    guarded = GuardedBrowserGateway(session.gateway, policy_for(base_url))

    await guarded.execute(navigate(f"{base_url}/injection"))
    instructions = await guarded.execute(
        BrowserAction(
            type=BrowserActionType.EXTRACT,
            intent="read the page",
            target=ActionTarget(text="SYSTEM:"),
        )
    )

    assert instructions.extracted_text is not None  # the text is readable data
    with pytest.raises(ActionDeniedError):  # and still just data
        await guarded.execute(navigate("https://evil.test/exfiltrate"))
    with pytest.raises(ActionDeniedError):
        await guarded.execute(click("Create record"))


async def test_console_and_network_failures_are_observed(
    target: tuple[str, TargetState], session: BrowserSession
) -> None:
    base_url, _ = target

    await session.gateway.execute(navigate(f"{base_url}/console-error"))
    await session.gateway.execute(
        BrowserAction(
            type=BrowserActionType.WAIT_FOR,
            intent="let the script run",
            target=ActionTarget(role="heading", name="Console error"),
        )
    )

    assert any(
        "deliberate console failure" in error for error in session.gateway.failures.console_errors
    )


async def test_dynamic_content_can_be_waited_for(
    target: tuple[str, TargetState], session: BrowserSession
) -> None:
    base_url, _ = target
    await session.gateway.execute(navigate(f"{base_url}/slow"))

    outcome = await session.gateway.execute(
        BrowserAction(
            type=BrowserActionType.WAIT_FOR,
            intent="wait for the delayed content",
            target=ActionTarget(text="loaded"),
        )
    )

    assert outcome.succeeded is True


async def test_contexts_are_isolated_between_runs(
    target: tuple[str, TargetState],
) -> None:
    """One BrowserContext per run: a session's login never leaks into another."""
    base_url, _ = target

    first = await start_browser_session()
    second = await start_browser_session()
    try:
        await first.gateway.execute(navigate(f"{base_url}/login"))
        await first.gateway.execute(fill("Email", VALID_USER))
        await first.gateway.execute(fill("Password", VALID_PASSWORD))
        await first.gateway.execute(click("Sign in"))
        assert (await first.gateway.execute(assert_text("Signed in as"))).succeeded

        await second.gateway.execute(navigate(f"{base_url}/dashboard"))
        assert (await second.gateway.execute(assert_text("Please sign in"))).succeeded
    finally:
        await first.aclose()
        await second.aclose()
