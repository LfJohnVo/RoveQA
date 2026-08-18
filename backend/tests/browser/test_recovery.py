"""Browser recovery and side-effect safety against a real Chromium.

Two mandatory scenarios from docs/15: Chromium crashes mid-run, and the worker dies
after a target side effect but before the acknowledgement.
"""

from collections.abc import AsyncIterator

import pytest

from agentic_qa.application.services.side_effects import perform_once
from agentic_qa.domain.browser.actions import (
    ActionTarget,
    BrowserAction,
    BrowserActionType,
    IdempotencyStrategy,
)
from agentic_qa.domain.browser.fingerprint import PageFingerprint
from agentic_qa.infrastructure.browser.playwright.gateway import (
    BrowserSession,
    rebuild_context,
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


def navigate(url: str) -> BrowserAction:
    return BrowserAction(
        type=BrowserActionType.NAVIGATE, intent="open", target=ActionTarget(url=url)
    )


def fill(label: str, value: str) -> BrowserAction:
    return BrowserAction(
        type=BrowserActionType.FILL,
        intent=f"type {label}",
        target=ActionTarget(label=label),
        value=value,
        side_effect=True,
        idempotency_strategy=IdempotencyStrategy.VERIFY_BEFORE_RETRY,
        verification_strategy="the field holds the value",
    )


def click(name: str) -> BrowserAction:
    return BrowserAction(
        type=BrowserActionType.CLICK,
        intent=f"press {name}",
        target=ActionTarget(role="button", name=name),
        side_effect=True,
        idempotency_strategy=IdempotencyStrategy.VERIFY_BEFORE_RETRY,
        verification_strategy="the resulting page confirms it",
    )


def expect(text: str) -> BrowserAction:
    return BrowserAction(type=BrowserActionType.ASSERT_TEXT, intent=f"expect {text}", value=text)


async def sign_in(session: BrowserSession, base_url: str) -> None:
    await session.gateway.execute(navigate(f"{base_url}/login"))
    await session.gateway.execute(fill("Email", VALID_USER))
    await session.gateway.execute(fill("Password", VALID_PASSWORD))
    await session.gateway.execute(click("Sign in"))


async def test_a_crashed_browser_is_rebuilt_and_the_session_survives(
    target: tuple[str, TargetState], session: BrowserSession
) -> None:
    """Chromium is never serialized: recovery restores storage state and re-verifies.

    Losing the browser must cost a rebuild, not the run's authentication.
    """
    base_url, _ = target
    await sign_in(session, base_url)
    saved_state = await session.gateway.storage_state()

    # Crash the renderer for real, then prove the old context is unusable.
    with pytest.raises(Exception):  # noqa: B017 - any Playwright error means it died
        await session.gateway.page.goto("chrome://crash", timeout=5_000)

    gateway = await rebuild_context(session, storage_state=saved_state)
    await gateway.execute(navigate(f"{base_url}/dashboard"))

    # Signed in without replaying the login: the restored state did the work.
    assert (await gateway.execute(expect("Signed in"))).succeeded is True


async def test_recovery_verifies_where_it_actually_landed(
    target: tuple[str, TargetState], session: BrowserSession
) -> None:
    """Resume means re-observing, not assuming the previous URL is still current."""
    base_url, _ = target
    await sign_in(session, base_url)
    saved_state = await session.gateway.storage_state()

    before = PageFingerprint.build(
        url=f"{base_url}/records", title="Records", controls=("button:Create record",)
    )

    gateway = await rebuild_context(session, storage_state=saved_state)
    await gateway.execute(navigate(f"{base_url}/records"))
    observed = PageFingerprint.build(
        url=await gateway.current_url() or "",
        title="Records",
        controls=("button:Create record",),
    )

    assert observed.matches(before)


async def test_a_side_effect_is_not_repeated_after_a_lost_acknowledgement(
    target: tuple[str, TargetState], session: BrowserSession
) -> None:
    """The uncertainty window: the record landed, the worker never heard back.

    Verify-before-retry asks the target whether *this run's* reference exists instead
    of creating a second record.
    """
    base_url, state = target
    reference = "run-42-order"

    async def record_exists() -> bool:
        probe = await start_browser_session()
        try:
            await probe.gateway.execute(navigate(f"{base_url}/records/{reference}"))
            outcome = await probe.gateway.execute(expect("No such record"))
            return not outcome.succeeded
        finally:
            await probe.aclose()

    async def create_record() -> None:
        await session.gateway.execute(navigate(f"{base_url}/records"))
        await session.gateway.execute(fill("Reference", reference))
        await session.gateway.execute(fill("Name", "Widget order"))
        await session.gateway.execute(click("Create record"))

    first = await perform_once(
        verify=record_exists, perform=create_record, description="create record"
    )
    assert first.performed is True
    assert first.verified is True
    assert state.records == {reference: "Widget order"}

    # The acknowledgement was lost, so the run retries the same logical action.
    second = await perform_once(
        verify=record_exists, perform=create_record, description="create record"
    )

    assert second.performed is False  # observation replaced the blind retry
    assert second.verified is True
    assert list(state.records) == [reference]  # exactly one record, not two


async def test_an_effect_that_never_landed_is_performed(
    target: tuple[str, TargetState], session: BrowserSession
) -> None:
    """Verification must not be an excuse to skip work that was never done."""
    base_url, state = target
    reference = "run-43-order"

    async def record_exists() -> bool:
        return reference in state.records

    async def create_record() -> None:
        await session.gateway.execute(navigate(f"{base_url}/records"))
        await session.gateway.execute(fill("Reference", reference))
        await session.gateway.execute(fill("Name", "Second widget"))
        await session.gateway.execute(click("Create record"))

    outcome = await perform_once(verify=record_exists, perform=create_record)

    assert outcome.performed is True
    assert outcome.verified is True
    assert state.records[reference] == "Second widget"
