"""A browser gateway that cannot execute what the policy forbids.

Enforcement lives in a wrapper rather than inside each adapter: an adapter that
forgot the check would still be a valid `BrowserGateway`, whereas a run that only
ever receives a guarded gateway cannot bypass the policy at all.

Retrieved memory, page content and model output can all suggest actions. None of
them can widen a policy — the check happens here, after any suggestion and before
any effect (CLAUDE.md invariants, docs/13).
"""

import logging

from agentic_qa.application.ports.browser import ActionOutcome, BrowserGateway
from agentic_qa.domain.browser.actions import BrowserAction
from agentic_qa.domain.browser.policy_guard import PolicyDecision, evaluate_action
from agentic_qa.domain.projects.run_policy import RunPolicy

logger = logging.getLogger(__name__)


class ActionDeniedError(Exception):
    """The run policy forbade an action; it was never executed."""

    def __init__(self, action: BrowserAction, decision: PolicyDecision) -> None:
        super().__init__(f"{action.type} denied: {decision.detail}")
        self.action = action
        self.decision = decision


class GuardedBrowserGateway:
    def __init__(self, inner: BrowserGateway, policy: RunPolicy) -> None:
        self._inner = inner
        self._policy = policy

    async def execute(self, action: BrowserAction) -> ActionOutcome:
        decision = evaluate_action(action, self._policy)
        if not decision.allowed:
            # Denied actions are logged and raised, never silently downgraded to a
            # no-op: a caller must not mistake "blocked" for "did nothing useful".
            logger.warning(
                "policy denied %s (%s): %s",
                action.type,
                decision.violation,
                decision.detail,
            )
            raise ActionDeniedError(action, decision)
        return await self._inner.execute(action)

    async def capture_screenshot(self) -> bytes:
        # Forwarded without a check: capturing the page changes nothing about the
        # system under test, and evidence of a denied action is worth having.
        return await self._inner.capture_screenshot()

    async def current_url(self) -> str | None:
        return await self._inner.current_url()

    async def aclose(self) -> None:
        await self._inner.aclose()
