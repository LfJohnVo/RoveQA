"""Browser gateway port.

Application asks for typed actions and never touches Playwright. There is no
`evaluate`/`run_script` member here either: the closed action set is the security
boundary, not a convention the adapter is trusted to respect.
"""

from dataclasses import dataclass, field
from typing import Protocol

from agentic_qa.domain.browser.actions import BrowserAction


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

    async def aclose(self) -> None: ...
