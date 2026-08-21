"""The hazards a public page carries, against real Chromium.

Every one of these reproduces a defect that shipped. Not because anybody was careless —
because every fixture until now was a local server that answered instantly and
completely, and each of these is *invisible* in that environment. A unit test over a
hand-written snapshot cannot catch them either: what they are about is how Chromium
behaves and what Playwright's snapshot actually says.

If this file is ever deleted or skipped, the defects come back silently. That is the
whole argument for it.
"""

import asyncio
from collections.abc import AsyncIterator

import pytest
from playwright.async_api import Error as PlaywrightError

from agentic_qa.domain.exploration.state import PageState
from agentic_qa.infrastructure.browser.playwright.gateway import (
    DEFAULT_ACTION_TIMEOUT_MS,
    MAX_REPORTED_PROBLEMS,
    BrowserSession,
    start_browser_session,
)
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


class TestAPageWhoseLoadNeverFires:
    """`/real-web` holds an image pointing at a resource that never answers.

    This is ordinary: analytics tags, ad frames and image CDNs do it constantly, and the
    `load` event waits for all of them. On a measured public site `load` took 23.1s while
    the DOM was ready in 0.3 — and one 10s constant served both "click this button" and
    "load this website", so every run against that site died before seeing the page.
    """

    async def test_the_old_default_would_still_time_out(
        self, target: tuple[str, TargetState], session: BrowserSession
    ) -> None:
        # The regression itself, stated as the thing that must remain true: waiting for
        # `load` on this page cannot succeed. If this ever passes, the fixture stopped
        # reproducing the hazard and every test below it is worthless.
        base, _ = target

        with pytest.raises(PlaywrightError):
            await session.gateway.page.goto(
                f"{base}/real-web",
                wait_until="load",
                timeout=DEFAULT_ACTION_TIMEOUT_MS,
            )

    async def test_the_agent_observes_it_anyway(
        self, target: tuple[str, TargetState], session: BrowserSession
    ) -> None:
        base, _ = target

        # What the gateway does now: its own budget, and `domcontentloaded`.
        page = await session.gateway.describe_page()
        await session.gateway.page.goto(f"{base}/real-web", wait_until="domcontentloaded")
        page = await session.gateway.describe_page()

        assert page.content, "the page arrived with no text at all"
        assert any("Pricing that scales" in line for line in page.content)

    async def test_it_is_observed_quickly(
        self, target: tuple[str, TargetState], session: BrowserSession
    ) -> None:
        # Not a performance assertion — a correctness one. The content is available
        # immediately, so an observation that takes seconds is waiting for the wrong
        # thing, and the number that proves it is well under any plausible budget.
        base, _ = target
        started = asyncio.get_running_loop().time()

        await session.gateway.page.goto(f"{base}/real-web", wait_until="domcontentloaded")
        await session.gateway.describe_page()

        assert asyncio.get_running_loop().time() - started < 5


class TestQuotedValuesInTheSnapshot:
    """Playwright quotes a value that would otherwise read as syntax.

    `/url: "#pricing"` — and keeping the quotes produced `…/"#pricing"`, a path no
    allowlist can resolve and no browser can open. Three of forty-one affordances on a
    real landing page came out this way, and all three were its in-page navigation.

    Only real Chromium can say whether Playwright still quotes them, which is exactly why
    this lives here and not beside the parser's unit tests.
    """

    async def test_playwright_still_quotes_them(
        self, target: tuple[str, TargetState], session: BrowserSession
    ) -> None:
        # Guards the premise. If Playwright stops quoting, the unquoting helper becomes
        # dead code and this test says so rather than leaving it to rot.
        base, _ = target
        await session.gateway.page.goto(f"{base}/real-web", wait_until="domcontentloaded")

        snapshot = await session.gateway.page.locator("body").aria_snapshot()

        assert '/url: "#' in snapshot

    async def test_no_affordance_carries_a_quote_in_its_url(
        self, target: tuple[str, TargetState], session: BrowserSession
    ) -> None:
        base, _ = target
        await session.gateway.page.goto(f"{base}/real-web", wait_until="domcontentloaded")

        page = await session.gateway.describe_page()

        for affordance in page.affordances:
            assert affordance.url is None or '"' not in affordance.url

    async def test_an_anchor_stays_on_the_page_it_came_from(
        self, target: tuple[str, TargetState], session: BrowserSession
    ) -> None:
        base, _ = target
        await session.gateway.page.goto(f"{base}/real-web", wait_until="domcontentloaded")

        page = await session.gateway.describe_page()
        anchors = [a for a in page.affordances if a.url and "#" in a.url]

        assert anchors, "the fixture stopped offering an anchor link"
        for anchor in anchors:
            assert anchor.url is not None
            assert anchor.url.startswith(base)


class TestElementStateReachesTheAgent:
    """A submit disabled until its form is filled is ordinary, and was invisible.

    The cost was a full locator timeout per attempt to learn what the observation already
    knew.
    """

    async def test_a_disabled_control_is_described_as_disabled(
        self, target: tuple[str, TargetState], session: BrowserSession
    ) -> None:
        base, _ = target
        await session.gateway.page.goto(f"{base}/real-web", wait_until="domcontentloaded")

        page = await session.gateway.describe_page()
        save = next((a for a in page.affordances if a.name == "Save record"), None)

        assert save is not None, "the fixture stopped offering a disabled control"
        assert save.disabled is True
        assert "[disabled]" in page.describe()

    async def test_it_is_not_offered_as_takeable(
        self, target: tuple[str, TargetState], session: BrowserSession
    ) -> None:
        base, _ = target
        await session.gateway.page.goto(f"{base}/real-web", wait_until="domcontentloaded")

        page = await session.gateway.describe_page()
        save = next(a for a in page.affordances if a.name == "Save record")

        assert save.is_clickable is False


class TestTheObservationCarriesTheContent:
    """The text was captured and discarded by the method that fetched it.

    A planner was handed the url, the title and a list of controls, then asked to confirm
    goals about what the page said.
    """

    async def test_prose_reaches_the_planner(
        self, target: tuple[str, TargetState], session: BrowserSession
    ) -> None:
        base, _ = target
        await session.gateway.page.goto(f"{base}/real-web", wait_until="domcontentloaded")

        described = (await session.gateway.describe_page()).describe()

        assert "text:" in described
        assert "Trusted by teams who cannot afford downtime." in described

    async def test_the_two_readings_stay_in_separate_sections(
        self, target: tuple[str, TargetState], session: BrowserSession
    ) -> None:
        # They answer different questions — "is the goal already true?" and "what can I
        # do next?" — and a planner that has to infer the first from a list of buttons
        # answers neither.
        base, _ = target
        await session.gateway.page.goto(f"{base}/real-web", wait_until="domcontentloaded")

        described = (await session.gateway.describe_page()).describe()

        assert described.index("text:") < described.index("elements:")

    async def test_the_consent_overlay_does_not_hide_the_page(
        self, target: tuple[str, TargetState], session: BrowserSession
    ) -> None:
        # Closing it is Phase 16's decision — accepting cookies is a consent choice and
        # an agent must not make it implicitly. What must hold now is that the overlay
        # does not stop the agent reading what is behind it.
        base, _ = target
        await session.gateway.page.goto(f"{base}/real-web", wait_until="domcontentloaded")

        page = await session.gateway.describe_page()

        assert any("We use cookies" in line for line in page.content)
        assert any("Pricing that scales" in line for line in page.content)
        assert any(a.name == "Only essentials" for a in page.affordances)


class TestWhatWentWrongIsReported:
    """`ObservedFailures` was collected in the adapter and had no consumer outside it.

    A script that throws and an image that 404s are first-class QA signal on any site,
    and both were already being measured (ADR 0015).
    """

    async def test_a_console_error_is_reported(
        self, target: tuple[str, TargetState], session: BrowserSession
    ) -> None:
        base, _ = target
        await session.gateway.page.goto(f"{base}/console-error", wait_until="domcontentloaded")
        await session.gateway.page.wait_for_load_state("networkidle")

        problems = await session.gateway.page_problems()

        assert any("deliberate console failure" in message for message in problems.console_errors)

    async def test_a_failed_request_is_reported(
        self, target: tuple[str, TargetState], session: BrowserSession
    ) -> None:
        # The first version of this asserted `isinstance(..., tuple)`, which cannot fail.
        # A request to a port nothing is listening on fails immediately and deterministically,
        # which is what `/hang` -- designed never to answer -- could not provide.
        base, _ = target
        await session.gateway.page.goto(f"{base}/", wait_until="domcontentloaded")
        await session.gateway.page.evaluate(
            "fetch('http://127.0.0.1:1/nothing-here').catch(() => {})"
        )
        await session.gateway.page.wait_for_timeout(500)

        problems = await session.gateway.page_problems()

        assert any("127.0.0.1" in url for url in problems.failed_requests)

    async def test_a_healthy_page_reports_nothing(
        self, target: tuple[str, TargetState], session: BrowserSession
    ) -> None:
        base, _ = target
        await session.gateway.page.goto(f"{base}/", wait_until="domcontentloaded")

        problems = await session.gateway.page_problems()

        assert not problems

    async def test_a_token_in_a_failed_url_does_not_survive(
        self, target: tuple[str, TargetState], session: BrowserSession
    ) -> None:
        # The security-relevant half. A failed request carries its URL, and a URL carries
        # tokens in its query string — the same reason `PageState` sanitises the one it
        # stores.
        base, _ = target
        await session.gateway.page.goto(f"{base}/", wait_until="domcontentloaded")
        await session.gateway.page.evaluate(
            "fetch('/missing-endpoint?session_token=" + LEAKED_TOKEN + "').catch(() => {})"
        )
        await session.gateway.page.wait_for_timeout(500)

        problems = await session.gateway.page_problems()

        for url in problems.failed_requests:
            assert LEAKED_TOKEN not in url
        for message in problems.console_errors:
            assert LEAKED_TOKEN not in message

    async def test_the_report_is_bounded(
        self, target: tuple[str, TargetState], session: BrowserSession
    ) -> None:
        # A page in a redirect loop or a broken carousel produces thousands of identical
        # entries, and a report nobody can read is a report nobody reads.
        base, _ = target
        await session.gateway.page.goto(f"{base}/", wait_until="domcontentloaded")
        await session.gateway.page.evaluate(
            "for (let i = 0; i < 60; i++) { console.error('noise ' + i); }"
        )
        await session.gateway.page.wait_for_timeout(300)

        problems = await session.gateway.page_problems()

        assert len(problems.console_errors) <= MAX_REPORTED_PROBLEMS


class TestAnErrorPageSaysSo:
    """The fixture's `/broken` answers 500 with a page that renders fine.

    Nothing in its prose says it is an error, which is the point: an application is under
    no obligation to explain itself, and a run that cannot see the status reports whatever
    the error page rendered as the application (ADR 0015).
    """

    async def test_the_status_reaches_the_observation(
        self, target: tuple[str, TargetState], session: BrowserSession
    ) -> None:
        base, _ = target
        await session.gateway.page.goto(f"{base}/broken", wait_until="domcontentloaded")

        page = await session.gateway.describe_page()

        assert page.http_status == 500

    async def test_the_planner_is_told_in_words(
        self, target: tuple[str, TargetState], session: BrowserSession
    ) -> None:
        base, _ = target
        await session.gateway.page.goto(f"{base}/broken", wait_until="domcontentloaded")

        described = (await session.gateway.describe_page()).describe()

        assert "http status: 500" in described
        assert "error page" in described

    async def test_a_healthy_page_is_not_annotated(
        self, target: tuple[str, TargetState], session: BrowserSession
    ) -> None:
        # A line on every observation is a line the planner learns to skip, and then it
        # skips the one that mattered.
        base, _ = target
        await session.gateway.page.goto(f"{base}/", wait_until="domcontentloaded")

        described = (await session.gateway.describe_page()).describe()

        assert "http status" not in described

    async def test_the_status_stays_out_of_the_signature(
        self, target: tuple[str, TargetState], session: BrowserSession
    ) -> None:
        # The same place answering 500 today and 200 tomorrow is the same place. In the
        # key it would give every stored baseline a new meaning the first time a deploy
        # went wrong.
        base, _ = target
        await session.gateway.page.goto(f"{base}/broken", wait_until="domcontentloaded")
        broken = await session.gateway.describe_page()

        assert (
            broken.signature == PageState(url=broken.url, affordances=broken.affordances).signature
        )
