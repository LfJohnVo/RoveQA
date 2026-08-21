"""Decide whether a RunPolicy permits a browser action.

Pure domain logic so the same decision holds wherever it is asked, and so it can be
tested without a browser. The adapter never re-implements it — it is wrapped by the
guard (see `application/services/guarded_browser.py`), which is what makes the rule
impossible to forget.
"""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePath

from agentic_qa.domain.browser.actions import (
    READ_ONLY_ACTIONS,
    BrowserAction,
    BrowserActionType,
)
from agentic_qa.domain.projects.run_policy import RunPolicy


class PolicyViolation(StrEnum):
    ORIGIN_NOT_ALLOWED = "origin_not_allowed"
    DESTRUCTIVE_NOT_ALLOWED = "destructive_not_allowed"
    UPLOAD_NOT_ALLOWED = "upload_not_allowed"
    UPLOAD_PATH_NOT_ALLOWED = "upload_path_not_allowed"


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    violation: PolicyViolation | None = None
    detail: str = ""

    @classmethod
    def permit(cls) -> "PolicyDecision":
        return cls(allowed=True)

    @classmethod
    def deny(cls, violation: PolicyViolation, detail: str) -> "PolicyDecision":
        return cls(allowed=False, violation=violation, detail=detail)


def evaluate_action(action: BrowserAction, policy: RunPolicy) -> PolicyDecision:
    if action.type is BrowserActionType.NAVIGATE:
        url = action.target.url or ""
        if not policy.allows_origin(url):
            return PolicyDecision.deny(
                PolicyViolation.ORIGIN_NOT_ALLOWED,
                f"navigation to {url} is outside the allowed origins",
            )

    if action.type not in READ_ONLY_ACTIONS and not policy.destructive_actions:
        # Deny-by-default, decided by the action *type* rather than by the model's own
        # `side_effect` flag (ADR 0014). The flag can only be raised, never lowered, so
        # keying the ban on it meant a planner marking `navigate` as state-changing —
        # over-cautious, not wrong — made a read-only run impossible: every one died on
        # its first navigation, and the verdict blamed `policy`, which reads as the
        # user's own configuration.
        #
        # Nothing is loosened. `click`, `fill` and every other write is outside
        # READ_ONLY_ACTIONS, so the case this guard exists for — an unverified click on
        # "Delete account" — is refused by type, as it always was. What the escalation
        # still buys is what it should: `to_domain_action` gives the action a real
        # idempotency strategy and a verification strategy.
        return PolicyDecision.deny(
            PolicyViolation.DESTRUCTIVE_NOT_ALLOWED,
            f"{action.type} has side effects and this policy forbids them",
        )

    if action.type is BrowserActionType.UPLOAD:
        if not policy.allow_file_uploads:
            return PolicyDecision.deny(
                PolicyViolation.UPLOAD_NOT_ALLOWED, "uploads are disabled by policy"
            )
        if not _upload_path_allowed(action.value or "", policy.upload_path_allowlist):
            return PolicyDecision.deny(
                PolicyViolation.UPLOAD_PATH_NOT_ALLOWED,
                "upload path is outside the allowlist",
            )

    return PolicyDecision.permit()


def _upload_path_allowed(candidate: str, allowlist: tuple[str, ...]) -> bool:
    """Resolve before comparing, so `allowed/../../etc/passwd` cannot sneak through."""
    if not allowlist:
        return False
    try:
        resolved = PurePath(candidate)
    except (TypeError, ValueError):
        return False
    if ".." in resolved.parts:
        return False
    return any(resolved.is_relative_to(PurePath(allowed)) for allowed in allowlist)
