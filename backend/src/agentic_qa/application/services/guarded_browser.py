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
from agentic_qa.domain.browser.actions import BrowserAction, BrowserActionType
from agentic_qa.domain.browser.policy_guard import (
    PolicyDecision,
    PolicyViolation,
    evaluate_action,
)
from agentic_qa.domain.exploration.state import PageState
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

        outcome = await self._inner.execute(action)

        # The allowlist has to hold for where the browser *ended up*, not only for what
        # was asked. `goto` follows redirects, so a navigation to an allowed origin that
        # redirects to a disallowed one used to arrive unchecked and the observation was
        # taken from it -- and `docs/13` documents this allowlist as the control against
        # reaching internal services (ADR 0015).
        #
        # What this does and does not do, stated because the distinction matters: the
        # request has already been made by the time we see the response, so this stops the
        # run from *observing* or acting on a disallowed origin, and ends the episode as a
        # policy violation rather than a browser error. Aborting the request itself needs
        # interception below this layer and is not what this does.
        # Only when we actually know where it landed. A missing url means the context
        # died, and calling that an origin violation would report a policy failure for an
        # environment one -- the misclassification this project spends real effort
        # avoiding. Nothing is at risk either: the harm here is an observation taken from
        # a disallowed origin, and a page that cannot report its own url cannot be
        # observed at all.
        landed_on = outcome.current_url
        if _is_navigation(action) and landed_on and not self._policy.allows_origin(landed_on):
            landed = PolicyDecision.deny(
                PolicyViolation.ORIGIN_NOT_ALLOWED,
                f"navigation ended on {landed_on}, outside the allowed origins",
            )
            logger.warning(
                "policy denied %s after the fact (%s): %s",
                action.type,
                landed.violation,
                landed.detail,
            )
            raise ActionDeniedError(action, landed)

        return outcome

    async def capture_screenshot(self) -> bytes:
        # Forwarded without a check: capturing the page changes nothing about the
        # system under test, and evidence of a denied action is worth having.
        return await self._inner.capture_screenshot()

    async def current_url(self) -> str | None:
        return await self._inner.current_url()

    async def describe_page(self) -> PageState:
        # Forwarded without a check, like the screenshot: reading what a page offers
        # changes nothing, and the policy still gates every action taken on it.
        return await self._inner.describe_page()

    async def aclose(self) -> None:
        await self._inner.aclose()


def _is_navigation(action: BrowserAction) -> bool:
    """Actions that can move the page, and therefore can land somewhere else.

    `back` is included: history can walk into an origin the allowlist no longer permits,
    and a run that got there by going backwards is in the same place as one that got there
    by going forwards.
    """
    return action.type in (BrowserActionType.NAVIGATE, BrowserActionType.BACK)
