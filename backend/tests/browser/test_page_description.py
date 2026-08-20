"""Describing a real page: what Chromium actually offers.

The parser lives in `tests/exploration/test_affordances.py`; this is the half that
cannot be faked. The format the parser reads is Playwright's, so a version bump could
change it — and the failure would not be an exception. It would be "this page offers
nothing", which an explorer reads as a dead end and a regression report reads as an
application that lost every control it had.
"""

from collections.abc import AsyncIterator

import pytest

from agentic_qa.infrastructure.browser.playwright.gateway import (
    BrowserSession,
    start_browser_session,
)

PAGE = (
    "<h1>Records</h1>"
    '<a href="/new">New record</a>'
    '<button type="button">Delete all</button>'
    '<label for="q">Search</label><input id="q" type="text">'
    "<ul><li><a href=/o/8821>Order 8821</a></li><li><a href=/o/9007>Order 9007</a></li></ul>"
    "<p>Copyright 2026</p>"
)


@pytest.fixture
async def session() -> AsyncIterator[BrowserSession]:
    browser = await start_browser_session(headless=True)
    try:
        yield browser
    finally:
        await browser.aclose()


async def test_a_real_page_reports_what_it_offers(session: BrowserSession) -> None:
    await session.gateway.page.set_content(PAGE)

    state = await session.gateway.describe_page()

    offered = {(item.role, item.name) for item in state.affordances}
    assert ("link", "New record") in offered
    assert ("button", "Delete all") in offered
    assert ("textbox", "Search") in offered


async def test_structure_is_not_reported_as_something_to_do(session: BrowserSession) -> None:
    await session.gateway.page.set_content(PAGE)

    state = await session.gateway.describe_page()

    assert not any(
        item.role in {"heading", "paragraph", "list", "listitem"} for item in state.affordances
    )


async def test_two_rows_of_the_same_kind_are_one_affordance(session: BrowserSession) -> None:
    """The property the whole design rests on: a list that grew is not a new place."""
    await session.gateway.page.set_content(PAGE)
    state = await session.gateway.describe_page()

    orders = [item for item in state.affordances if item.name.lower().startswith("order")]
    assert len(orders) == 1


async def test_the_same_page_with_different_data_has_the_same_signature(
    session: BrowserSession,
) -> None:
    await session.gateway.page.set_content(PAGE)
    before = await session.gateway.describe_page()

    await session.gateway.page.set_content(
        PAGE.replace("Order 8821", "Order 4410").replace("Copyright 2026", "Copyright 2027")
    )
    after = await session.gateway.describe_page()

    assert before.signature == after.signature


async def test_a_page_that_gained_a_control_is_a_different_state(session: BrowserSession) -> None:
    await session.gateway.page.set_content(PAGE)
    before = await session.gateway.describe_page()

    await session.gateway.page.set_content(
        PAGE + '<button type="button">Export everything</button>'
    )
    after = await session.gateway.describe_page()

    assert before.signature != after.signature
