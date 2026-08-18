"""Decide whether a RunPolicy permits a browser action.

Pure domain logic so the same decision holds wherever it is asked, and so it can be
tested without a browser. The adapter never re-implements it — it is wrapped by the
guard (see `application/services/guarded_browser.py`), which is what makes the rule
impossible to forget.
"""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePath

from agentic_qa.domain.browser.actions import BrowserAction, BrowserActionType
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

    if action.side_effect and not policy.destructive_actions:
        # Deny-by-default: a write only happens when the policy said writes are fine.
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
