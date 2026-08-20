"""Browser gateway port.

Application asks for typed actions and never touches Playwright. There is no
`evaluate`/`run_script` member here either: the closed action set is the security
boundary, not a convention the adapter is trusted to respect.
"""

from dataclasses import dataclass, field
from typing import Protocol

from agentic_qa.domain.browser.actions import BrowserAction
from agentic_qa.domain.exploration.state import PageState


class UnperformableActionError(Exception):
    """The gateway cannot carry out this action as described.

    A fact about the *attempt*, not a malfunction: a planner asked for a click on a
    target with no usable locator, or named an element role that does not exist. The
    action set is closed and the schema is validated, so this is what is left — a
    structurally valid request the page cannot satisfy.

    Typed so the agent graph can record it as a failed step and let the planner try
    something else. Letting it escape would surface as an activity crash, and Temporal
    would retry the whole episode only for the planner to propose the same unusable
    action again (ADR 0009).
    """


@dataclass(frozen=True)
class ActionOutcome:
    """What actually happened, kept separate from what was intended."""

    succeeded: bool
    current_url: str | None = None
    extracted_text: str | None = None
    detail: str = ""
    artifacts: tuple[str, ...] = field(default=())


class BrowserGateway(Protocol):
    async def execute(self, action: BrowserAction) -> ActionOutcome: ...

    async def capture_screenshot(self) -> bytes:
        """Capture the page as it is now.

        A capability rather than an action outcome: the bytes only exist while the
        page does, and deciding whether to keep them belongs to the caller. It is
        read-only, so no policy check gates it — a screenshot changes nothing.
        """
        ...

    async def current_url(self) -> str | None: ...

    async def describe_page(self) -> PageState:
        """Where the page is and what it offers, as roles and accessible names.

        Read-only, so no policy check gates it — describing a page changes nothing.
        Deliberately *not* the DOM: an explorer that remembered markup would treat
        every render as a new place, and a report built on it would claim the whole
        application changed whenever a footer year rolled over (Phase 12).
        """
        ...

    async def aclose(self) -> None: ...
