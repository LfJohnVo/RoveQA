"""Typed action set and policy enforcement.

Two gates of Phase 04 live here: no arbitrary JS is reachable, and the origin policy
is enforced before anything executes.
"""

from dataclasses import dataclass

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
from agentic_qa.domain.exploration.state import PageState
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

    async def describe_page(self) -> PageState:
        return PageState(url="")

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


@dataclass
class _LandingBrowser:
    """A browser that reports where a navigation ended, which is the whole question.

    Deliberately a double rather than real Chromium: what is under test is the guard's
    rule, and reproducing a real cross-origin redirect would make the test depend on a
    second server rather than on the rule.
    """

    landed_on: str
    status: int | None = 200

    async def execute(self, action: BrowserAction) -> ActionOutcome:
        return ActionOutcome(succeeded=True, current_url=self.landed_on, http_status=self.status)

    async def capture_screenshot(self) -> bytes:
        return b""

    async def current_url(self) -> str | None:
        return self.landed_on

    async def describe_page(self) -> PageState:
        return PageState(url=self.landed_on)

    async def aclose(self) -> None:
        return None


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


class TestAReadOnlyPolicyCanStillLook:
    """Phase 15, slice 9 — ADR 0014.

    `side_effect` is the model's own read and can only be raised. Keying the ban on it
    meant a planner marking `navigate` as state-changing — over-cautious, not wrong —
    made a read-only run impossible: at temperature 0 every one died on its first
    navigation, and the verdict blamed `policy`, which reads as the user's own
    configuration. The action *type* decides what is forbidden.
    """

    def test_navigation_survives_an_over_cautious_planner(self) -> None:
        escalated = BrowserAction(
            type=BrowserActionType.NAVIGATE,
            intent="open the application",
            target=ActionTarget(url="https://app.test/"),
            side_effect=True,
            idempotency_strategy=IdempotencyStrategy.VERIFY_BEFORE_RETRY,
            verification_strategy="confirm the page loaded",
        )

        assert evaluate_action(escalated, make_policy()).allowed

    def test_a_write_is_still_refused_by_its_type(self) -> None:
        # The case the guard exists for. `click` is outside READ_ONLY_ACTIONS, so an
        # unverified click on "Delete account" is refused exactly as before.
        decision = evaluate_action(click_submit(), make_policy())

        assert decision.allowed is False
        assert decision.violation is PolicyViolation.DESTRUCTIVE_NOT_ALLOWED

    def test_a_write_cannot_even_be_built_claiming_to_be_harmless(self) -> None:
        # Stronger than a policy denial: the guard never sees such an action, because
        # the domain refuses to construct one. `side_effect` can be raised, never
        # lowered, at both layers.
        with pytest.raises(InvalidEntityError):
            BrowserAction(
                type=BrowserActionType.CLICK,
                intent="delete the account",
                target=ActionTarget(role="button", name="Delete account"),
            )

    def test_asserting_text_needs_no_permission(self) -> None:
        assertion = BrowserAction(
            type=BrowserActionType.ASSERT_TEXT,
            intent="confirm the heading",
            value="Sign in",
        )

        assert evaluate_action(assertion, make_policy()).allowed

    def test_the_allowlist_still_bounds_a_read_only_run(self) -> None:
        # Loosening the destructive check must not loosen the origin fence.
        escalated = BrowserAction(
            type=BrowserActionType.NAVIGATE,
            intent="wander off",
            target=ActionTarget(url="https://evil.test/"),
            side_effect=True,
            idempotency_strategy=IdempotencyStrategy.VERIFY_BEFORE_RETRY,
            verification_strategy="confirm the page loaded",
        )

        decision = evaluate_action(escalated, make_policy())

        assert decision.allowed is False
        assert decision.violation is PolicyViolation.ORIGIN_NOT_ALLOWED


class TestWhereANavigationLanded:
    """Phase 16, slice 1 — ADR 0015.

    `page.goto` follows redirects. The guard validated the URL a run *asked* for, so a
    navigation to an allowed origin that redirected to a disallowed one arrived unchecked
    and the observation was taken from it. `docs/13` documents this allowlist as the
    control against reaching internal services.
    """

    async def test_a_redirect_off_origin_is_refused(self) -> None:
        landed = _LandingBrowser("http://169.254.169.254/latest/meta-data")
        guarded = GuardedBrowserGateway(landed, make_policy())

        with pytest.raises(ActionDeniedError) as refused:
            await guarded.execute(navigate("https://app.test/redirector"))

        assert refused.value.decision.violation is PolicyViolation.ORIGIN_NOT_ALLOWED
        assert "outside the allowed origins" in refused.value.decision.detail

    async def test_staying_on_an_allowed_origin_is_fine(self) -> None:
        landed = _LandingBrowser("https://app.test/checkout")
        guarded = GuardedBrowserGateway(landed, make_policy())

        outcome = await guarded.execute(navigate("https://app.test/cart"))

        assert outcome.succeeded

    async def test_going_back_into_a_disallowed_origin_is_refused(self) -> None:
        # History can walk somewhere the allowlist does not permit, and a run that got
        # there backwards is in the same place as one that got there forwards.
        landed = _LandingBrowser("https://evil.test/")
        guarded = GuardedBrowserGateway(landed, make_policy())
        back = BrowserAction(type=BrowserActionType.BACK, intent="go back")

        with pytest.raises(ActionDeniedError):
            await guarded.execute(back)

    async def test_the_status_reaches_the_caller(self) -> None:
        landed = _LandingBrowser("https://app.test/missing", status=404)
        guarded = GuardedBrowserGateway(landed, make_policy())

        outcome = await guarded.execute(navigate("https://app.test/missing"))

        # Not a verdict on its own — provenance decides who is responsible (ADR 0015) —
        # but a run that cannot see it reads an error page as the application.
        assert outcome.http_status == 404

    async def test_an_unknown_url_is_not_treated_as_a_violation(self) -> None:
        # A dead context reports no url. Calling that an origin violation would report a
        # policy failure for an environment one, and there is nothing to protect: a page
        # that cannot report its own url cannot be observed either.
        landed = _LandingBrowser("", status=None)
        landed.landed_on = ""
        guarded = GuardedBrowserGateway(landed, make_policy())

        outcome = await guarded.execute(navigate("https://app.test/cart"))

        assert outcome.succeeded
