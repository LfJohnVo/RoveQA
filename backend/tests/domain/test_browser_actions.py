"""Typed action set and policy enforcement.

Two gates of Phase 04 live here: no arbitrary JS is reachable, and the origin policy
is enforced before anything executes.
"""

import pytest

from agentic_qa.application.ports.browser import ActionOutcome
from agentic_qa.application.services.guarded_browser import (
    ActionDeniedError,
    GuardedBrowserGateway,
)
from agentic_qa.domain.browser.actions import (
    ActionTarget,
    BrowserAction,
    BrowserActionType,
    IdempotencyStrategy,
)
from agentic_qa.domain.browser.policy_guard import PolicyViolation, evaluate_action
from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.domain.projects.run_policy import RunPolicy


def make_policy(
    *,
    destructive_actions: bool = False,
    allow_file_uploads: bool = False,
    upload_path_allowlist: tuple[str, ...] = (),
) -> RunPolicy:
    return RunPolicy(
        policy_id="pol-1",
        project_id="p-1",
        allowed_origins=("https://app.test",),
        max_duration_seconds=600,
        max_actions=100,
        max_model_calls=10,
        destructive_actions=destructive_actions,
        allow_file_uploads=allow_file_uploads,
        upload_path_allowlist=upload_path_allowlist,
    )


def navigate(url: str) -> BrowserAction:
    return BrowserAction(
        type=BrowserActionType.NAVIGATE,
        intent="open the checkout page",
        target=ActionTarget(url=url),
    )


def click_submit() -> BrowserAction:
    return BrowserAction(
        type=BrowserActionType.CLICK,
        intent="submit the order",
        target=ActionTarget(role="button", name="Submit"),
        side_effect=True,
        idempotency_strategy=IdempotencyStrategy.VERIFY_BEFORE_RETRY,
        verification_strategy="look up the order by its run-scoped reference",
    )


class RecordingGateway:
    def __init__(self) -> None:
        self.executed: list[BrowserAction] = []

    async def execute(self, action: BrowserAction) -> ActionOutcome:
        self.executed.append(action)
        return ActionOutcome(succeeded=True)

    async def capture_screenshot(self) -> bytes:
        return b"fake-png-bytes"

    async def current_url(self) -> str | None:
        return None

    async def aclose(self) -> None:
        return None


class TestClosedActionSet:
    def test_there_is_no_javascript_action(self) -> None:
        """The control is the absence of the capability, not a flag guarding it."""
        names = {member.value for member in BrowserActionType}

        assert names.isdisjoint({"evaluate", "execute_script", "eval", "run_js", "script"})

    def test_the_action_set_matches_the_documented_v1_list(self) -> None:
        assert {member.value for member in BrowserActionType} == {
            "navigate",
            "click",
            "fill",
            "select",
            "check",
            "uncheck",
            "upload",
            "press_key",
            "wait_for",
            "extract",
            "assert_text",
            "assert_url",
            "screenshot",
            "back",
        }


class TestActionInvariants:
    def test_navigate_requires_a_url(self) -> None:
        with pytest.raises(InvalidEntityError):
            BrowserAction(type=BrowserActionType.NAVIGATE, intent="go somewhere")

    def test_click_requires_a_semantic_target(self) -> None:
        with pytest.raises(InvalidEntityError):
            BrowserAction(
                type=BrowserActionType.CLICK,
                intent="click",
                side_effect=True,
                idempotency_strategy=IdempotencyStrategy.VERIFY_BEFORE_RETRY,
                verification_strategy="check",
            )

    def test_a_state_changing_action_must_declare_its_side_effect(self) -> None:
        with pytest.raises(InvalidEntityError):
            BrowserAction(
                type=BrowserActionType.FILL,
                intent="type the email",
                target=ActionTarget(label="Email"),
                value="a@b.test",
            )

    def test_a_side_effect_needs_a_retry_and_verification_strategy(self) -> None:
        with pytest.raises(InvalidEntityError):
            BrowserAction(
                type=BrowserActionType.CLICK,
                intent="submit",
                target=ActionTarget(role="button", name="Submit"),
                side_effect=True,
            )


class TestPolicyEvaluation:
    def test_navigation_inside_the_allowlist_is_permitted(self) -> None:
        assert evaluate_action(navigate("https://app.test/checkout"), make_policy()).allowed

    def test_navigation_outside_the_allowlist_is_denied(self) -> None:
        decision = evaluate_action(navigate("https://evil.test/"), make_policy())

        assert decision.allowed is False
        assert decision.violation is PolicyViolation.ORIGIN_NOT_ALLOWED

    def test_internal_addresses_are_denied_like_any_other_origin(self) -> None:
        """The allowlist is the control against reaching internal services."""
        decision = evaluate_action(
            navigate("http://169.254.169.254/latest/meta-data"), make_policy()
        )

        assert decision.allowed is False

    def test_side_effects_are_denied_by_default(self) -> None:
        decision = evaluate_action(click_submit(), make_policy())

        assert decision.allowed is False
        assert decision.violation is PolicyViolation.DESTRUCTIVE_NOT_ALLOWED

    def test_side_effects_are_permitted_when_the_policy_says_so(self) -> None:
        assert evaluate_action(click_submit(), make_policy(destructive_actions=True)).allowed

    def test_uploads_are_denied_unless_enabled(self) -> None:
        action = BrowserAction(
            type=BrowserActionType.UPLOAD,
            intent="attach the invoice",
            target=ActionTarget(label="Invoice"),
            value="/fixtures/invoice.pdf",
            side_effect=True,
            idempotency_strategy=IdempotencyStrategy.VERIFY_BEFORE_RETRY,
            verification_strategy="check the attachment appears",
        )

        decision = evaluate_action(action, make_policy(destructive_actions=True))
        assert decision.violation is PolicyViolation.UPLOAD_NOT_ALLOWED

        allowed = evaluate_action(
            action,
            make_policy(
                destructive_actions=True,
                allow_file_uploads=True,
                upload_path_allowlist=("/fixtures",),
            ),
        )
        assert allowed.allowed is True

    def test_upload_paths_escaping_the_allowlist_are_denied(self) -> None:
        action = BrowserAction(
            type=BrowserActionType.UPLOAD,
            intent="attach a file",
            target=ActionTarget(label="Invoice"),
            value="/fixtures/../../etc/passwd",
            side_effect=True,
            idempotency_strategy=IdempotencyStrategy.VERIFY_BEFORE_RETRY,
            verification_strategy="check the attachment appears",
        )

        decision = evaluate_action(
            action,
            make_policy(
                destructive_actions=True,
                allow_file_uploads=True,
                upload_path_allowlist=("/fixtures",),
            ),
        )
        assert decision.violation is PolicyViolation.UPLOAD_PATH_NOT_ALLOWED


class TestGuardedGateway:
    async def test_a_permitted_action_reaches_the_browser(self) -> None:
        inner = RecordingGateway()
        guarded = GuardedBrowserGateway(inner, make_policy())

        await guarded.execute(navigate("https://app.test/"))

        assert len(inner.executed) == 1

    async def test_a_denied_action_never_reaches_the_browser(self) -> None:
        """Blocked means not executed, and raised — never a silent no-op."""
        inner = RecordingGateway()
        guarded = GuardedBrowserGateway(inner, make_policy())

        with pytest.raises(ActionDeniedError):
            await guarded.execute(navigate("https://evil.test/"))

        assert inner.executed == []
