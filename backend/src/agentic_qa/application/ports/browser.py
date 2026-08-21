"""Browser gateway port.

Application asks for typed actions and never touches Playwright. There is no
`evaluate`/`run_script` member here either: the closed action set is the security
boundary, not a convention the adapter is trusted to respect.
"""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

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

    http_status: int | None = None
    """What the server answered, for a navigation. None for anything else, and None when
    the response could not be read.

    `succeeded` is about the mechanism -- whether the call threw -- and was the only signal
    a run had. So a 404 and a 500 both came back successful, the agent observed whatever the
    error page rendered, and took it for the application (ADR 0015).
    """


@dataclass(frozen=True)
class PageProblems:
    """What went wrong in the browser while a page was being driven.

    Collected passively and never used to steer: a console error changes what a report
    says, not what the agent does next. Both fields were already being gathered in the
    Playwright adapter and had no consumer outside it, so a JavaScript exception or an
    image answering 404 -- first-class QA signal on any site -- was measured and thrown
    away (ADR 0015).
    """

    console_errors: tuple[str, ...] = field(default=())
    failed_requests: tuple[str, ...] = field(default=())

    def __bool__(self) -> bool:
        return bool(self.console_errors or self.failed_requests)


@runtime_checkable
class ReportsPageProblems(Protocol):
    """A gateway that watched the browser and can say what went wrong.

    Separate from `BrowserGateway`, and optional, because it is genuinely optional: a
    gateway that drives a page without listening to its console is a complete gateway.
    Folding it into the port would oblige every implementation — including the doubles
    that exist to test something else entirely — to answer a question it has no opinion
    about, which is how a port stops describing a capability and starts describing a
    class hierarchy.
    """

    async def page_problems(self) -> PageProblems: ...


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
