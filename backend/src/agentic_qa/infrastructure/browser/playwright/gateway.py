"""Playwright adapter for the BrowserGateway port.

Locators are semantic (role/label/text) rather than coordinates, so an action states
what it meant and can be verified afterwards (docs/07 interaction ladder).

One `BrowserContext` per run: cookies, storage and permissions never leak between
runs, and a crashed context can be rebuilt without touching any other run.

This class enforces nothing. Policy lives in `GuardedBrowserGateway`, and callers
receive this adapter only through `open_browser_session`, which wraps it.
"""

import logging
from dataclasses import dataclass, field
from types import TracebackType
from typing import Self, cast

from playwright._impl._api_structures import AriaRole
from playwright.async_api import (
    Browser,
    BrowserContext,
    ConsoleMessage,
    Locator,
    Page,
    Playwright,
    Request,
    StorageState,
    async_playwright,
)
from playwright.async_api import (
    Error as PlaywrightError,
)

from agentic_qa.application.ports.browser import ActionOutcome
from agentic_qa.domain.browser.actions import ActionTarget, BrowserAction, BrowserActionType

logger = logging.getLogger(__name__)

DEFAULT_ACTION_TIMEOUT_MS = 10_000


class BrowserSessionError(Exception):
    """The browser could not carry out the action for a mechanical reason."""


# Playwright types roles as a Literal; the domain carries a plain string because the
# contract does. Membership is checked here so the narrowing below rests on evidence
# rather than on hope, and an unknown role fails loudly instead of silently matching
# nothing.
ARIA_ROLES = frozenset(
    {
        "alert",
        "alertdialog",
        "application",
        "article",
        "banner",
        "blockquote",
        "button",
        "caption",
        "cell",
        "checkbox",
        "code",
        "columnheader",
        "combobox",
        "complementary",
        "contentinfo",
        "definition",
        "deletion",
        "dialog",
        "directory",
        "document",
        "emphasis",
        "feed",
        "figure",
        "form",
        "generic",
        "grid",
        "gridcell",
        "group",
        "heading",
        "img",
        "insertion",
        "link",
        "list",
        "listbox",
        "listitem",
        "log",
        "main",
        "marquee",
        "math",
        "menu",
        "menubar",
        "menuitem",
        "menuitemcheckbox",
        "menuitemradio",
        "meter",
        "navigation",
        "none",
        "note",
        "option",
        "paragraph",
        "presentation",
        "progressbar",
        "radio",
        "radiogroup",
        "region",
        "row",
        "rowgroup",
        "rowheader",
        "scrollbar",
        "search",
        "searchbox",
        "separator",
        "slider",
        "spinbutton",
        "status",
        "strong",
        "subscript",
        "superscript",
        "switch",
        "tab",
        "table",
        "tablist",
        "tabpanel",
        "term",
        "textbox",
        "time",
        "timer",
        "toolbar",
        "tooltip",
        "tree",
        "treegrid",
        "treeitem",
    }
)


def _aria_role(role: str) -> AriaRole:
    normalized = role.strip().lower()
    if normalized not in ARIA_ROLES:
        raise BrowserSessionError(f"unknown ARIA role: {role}")
    return cast(AriaRole, normalized)


@dataclass
class ObservedFailures:
    """Console and network problems seen while the page was driven.

    Collected passively so a verdict can cite them, never to change control flow.
    """

    console_errors: list[str] = field(default_factory=list)
    failed_requests: list[str] = field(default_factory=list)

    def clear(self) -> None:
        self.console_errors.clear()
        self.failed_requests.clear()


class PlaywrightBrowserGateway:
    def __init__(self, context: BrowserContext, page: Page) -> None:
        self._context = context
        self._page = page
        self.failures = ObservedFailures()
        page.on("console", self._on_console)
        page.on("requestfailed", self._on_request_failed)

    def _on_console(self, message: ConsoleMessage) -> None:
        if message.type == "error":
            self.failures.console_errors.append(message.text)

    def _on_request_failed(self, request: Request) -> None:
        self.failures.failed_requests.append(f"{request.method} {request.url}")

    @property
    def page(self) -> Page:
        return self._page

    async def current_url(self) -> str | None:
        try:
            return self._page.url
        except PlaywrightError:  # context died
            return None

    async def storage_state(self) -> StorageState:
        """Serializable auth state: what recovery restores instead of replaying a login."""
        return await self._context.storage_state()

    async def execute(self, action: BrowserAction) -> ActionOutcome:
        try:
            return await self._dispatch(action)
        except PlaywrightError as error:
            # Mechanical failure (selector, navigation, dead context) — reported, not
            # raised as a verdict. Deciding what it means is the agent's job.
            logger.info("browser action %s failed: %s", action.type, error.message)
            return ActionOutcome(
                succeeded=False,
                current_url=await self.current_url(),
                detail=error.message.splitlines()[0] if error.message else "browser error",
            )

    async def _dispatch(self, action: BrowserAction) -> ActionOutcome:
        match action.type:
            case BrowserActionType.NAVIGATE:
                await self._page.goto(action.target.url or "", timeout=DEFAULT_ACTION_TIMEOUT_MS)
            case BrowserActionType.CLICK:
                await self._locate(action.target).click(timeout=DEFAULT_ACTION_TIMEOUT_MS)
            case BrowserActionType.FILL:
                await self._locate(action.target).fill(
                    action.value or "", timeout=DEFAULT_ACTION_TIMEOUT_MS
                )
            case BrowserActionType.SELECT:
                await self._locate(action.target).select_option(
                    action.value or "", timeout=DEFAULT_ACTION_TIMEOUT_MS
                )
            case BrowserActionType.CHECK:
                await self._locate(action.target).check(timeout=DEFAULT_ACTION_TIMEOUT_MS)
            case BrowserActionType.UNCHECK:
                await self._locate(action.target).uncheck(timeout=DEFAULT_ACTION_TIMEOUT_MS)
            case BrowserActionType.UPLOAD:
                await self._locate(action.target).set_input_files(action.value or "")
            case BrowserActionType.PRESS_KEY:
                await self._page.keyboard.press(action.value or "")
            case BrowserActionType.WAIT_FOR:
                await self._locate(action.target).wait_for(timeout=DEFAULT_ACTION_TIMEOUT_MS)
            case BrowserActionType.EXTRACT:
                text = await self._locate(action.target).inner_text(
                    timeout=DEFAULT_ACTION_TIMEOUT_MS
                )
                return ActionOutcome(
                    succeeded=True, current_url=self._page.url, extracted_text=text
                )
            case BrowserActionType.ASSERT_TEXT:
                expected = action.value or ""
                body = await self._page.locator("body").inner_text(
                    timeout=DEFAULT_ACTION_TIMEOUT_MS
                )
                return ActionOutcome(
                    succeeded=expected in body,
                    current_url=self._page.url,
                    detail="" if expected in body else f"text not found: {expected}",
                )
            case BrowserActionType.ASSERT_URL:
                expected_url = action.value or ""
                matches = expected_url in self._page.url
                return ActionOutcome(
                    succeeded=matches,
                    current_url=self._page.url,
                    detail="" if matches else f"url mismatch, expected {expected_url}",
                )
            case BrowserActionType.SCREENSHOT:
                return ActionOutcome(succeeded=True, current_url=self._page.url)
            case BrowserActionType.BACK:
                await self._page.go_back(timeout=DEFAULT_ACTION_TIMEOUT_MS)

        return ActionOutcome(succeeded=True, current_url=self._page.url)

    def _locate(self, target: ActionTarget) -> Locator:
        """Semantic first: role, then label, then visible text.

        Playwright's Locator stays inside infrastructure; nothing above this layer
        ever sees it.
        """
        if target.role:
            return self._page.get_by_role(_aria_role(target.role), name=target.name)
        if target.label:
            return self._page.get_by_label(target.label)
        if target.text:
            return self._page.get_by_text(target.text)
        if target.name:
            return self._page.get_by_role(_aria_role("button"), name=target.name)
        raise BrowserSessionError("action target has no semantic locator")

    async def screenshot_bytes(self) -> bytes:
        return await self._page.screenshot(type="png")

    async def aclose(self) -> None:
        try:
            await self._context.close()
        except PlaywrightError:  # already gone after a crash
            logger.debug("context already closed")


@dataclass
class BrowserSession:
    """Owns the Playwright process and browser for the life of a run."""

    playwright: Playwright
    browser: Browser
    gateway: PlaywrightBrowserGateway

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self.gateway.aclose()
        await self.browser.close()
        await self.playwright.stop()


async def start_browser_session(
    *, headless: bool = True, storage_state: StorageState | None = None
) -> BrowserSession:
    """Launch Chromium with an isolated context, optionally restoring auth state."""
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=headless)
    context = await browser.new_context(storage_state=storage_state)
    page = await context.new_page()
    return BrowserSession(
        playwright=playwright, browser=browser, gateway=PlaywrightBrowserGateway(context, page)
    )


async def rebuild_context(
    session: BrowserSession, *, storage_state: StorageState | None = None
) -> PlaywrightBrowserGateway:
    """Replace a dead context on the same browser, restoring auth state.

    Chromium is never serialized (docs/05): recovery relaunches a clean context and
    restores storage state, then the caller re-verifies where it actually is.
    """
    context = await session.browser.new_context(storage_state=storage_state)
    page = await context.new_page()
    session.gateway = PlaywrightBrowserGateway(context, page)
    return session.gateway
