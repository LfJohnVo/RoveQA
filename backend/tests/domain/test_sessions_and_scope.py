"""What a borrowed session is, and what a run with one may still not do (ADR 0019).

Domain-level and deliberately so: none of this needs a browser, a database or a key. The
rules that keep a secret out of the wrong place are rules about *types* — an action that
carries a name instead of a value, a session object with nowhere to put a cookie — and a
rule that can be checked without infrastructure is a rule that cannot be forgotten by one
call site.
"""

from datetime import UTC, datetime, timedelta

import pytest

from agentic_qa.domain.browser.actions import (
    ActionTarget,
    BrowserAction,
    BrowserActionType,
    IdempotencyStrategy,
)
from agentic_qa.domain.browser.policy_guard import PolicyViolation, evaluate_action
from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.domain.projects.run_policy import RunPolicy
from agentic_qa.domain.projects.session import EnvironmentSession, SecretName
from agentic_qa.domain.qa.verification import BLOCKING_KINDS, PRODUCT_DEFECT_KINDS, FailureKind

ESTABLISHED = datetime(2026, 8, 22, 12, 0, tzinfo=UTC)


def policy_for(*, forbidden: tuple[str, ...] = (), destructive: bool = True) -> RunPolicy:
    return RunPolicy(
        policy_id="pol-1",
        project_id="proj-1",
        allowed_origins=("https://app.test",),
        max_duration_seconds=600,
        max_actions=50,
        max_model_calls=50,
        destructive_actions=destructive,
        forbidden_paths=forbidden,
    )


def navigate_to(url: str) -> BrowserAction:
    return BrowserAction(
        type=BrowserActionType.NAVIGATE,
        intent="go there",
        target=ActionTarget(url=url),
    )


class TestASessionKnowsWhatItIsAndNotWhatItHolds:
    def test_it_has_nowhere_to_put_a_cookie(self) -> None:
        # Structural. The sealed storage state is infrastructure's, and a domain object
        # that carried it would be a domain object somebody could log.
        from dataclasses import fields

        assert {field.name for field in fields(EnvironmentSession)} == {
            "session_id",
            "environment_id",
            "label",
            "established_at",
            "valid_until",
            "established_by",
        }

    def test_an_unstated_expiry_is_not_an_expiry(self) -> None:
        # "Nobody said when this ends" and "this ended" are different facts, and treating
        # the first as the second would refuse every session captured without a note.
        session = EnvironmentSession(
            session_id="sess-1",
            environment_id="env-1",
            label="admin",
            established_at=ESTABLISHED,
        )

        assert session.has_expired(now=ESTABLISHED + timedelta(days=365)) is False

    def test_a_stated_expiry_is_honoured_to_the_second(self) -> None:
        session = EnvironmentSession(
            session_id="sess-1",
            environment_id="env-1",
            label="admin",
            established_at=ESTABLISHED,
            valid_until=ESTABLISHED + timedelta(hours=2),
        )

        assert session.has_expired(now=ESTABLISHED + timedelta(hours=1, minutes=59)) is False
        assert session.has_expired(now=ESTABLISHED + timedelta(hours=2)) is True

    def test_a_naive_timestamp_is_refused_where_it_is_cheap_to_refuse(self) -> None:
        # Comparing a naive datetime against an aware one raises, and the moment it would
        # raise is halfway through provisioning a browser for a run that already started.
        with pytest.raises(InvalidEntityError, match="timezone-aware"):
            EnvironmentSession(
                session_id="sess-1",
                environment_id="env-1",
                label="admin",
                established_at=datetime(2026, 8, 22, 12, 0),  # noqa: DTZ001 - the point
            )

    def test_a_session_cannot_expire_before_it_existed(self) -> None:
        with pytest.raises(InvalidEntityError):
            EnvironmentSession(
                session_id="sess-1",
                environment_id="env-1",
                label="admin",
                established_at=ESTABLISHED,
                valid_until=ESTABLISHED - timedelta(minutes=1),
            )


class TestASecretIsANameAndNothingElse:
    def test_an_action_carries_the_name_instead_of_the_password(self) -> None:
        action = BrowserAction(
            type=BrowserActionType.FILL,
            intent="type the password",
            target=ActionTarget(role="textbox", label="Password"),
            secret_ref=SecretName("login.password"),
            side_effect=True,
            idempotency_strategy=IdempotencyStrategy.VERIFY_BEFORE_RETRY,
            verification_strategy="the account page appears",
        )

        assert action.value is None
        # The whole containment argument: this can be printed anywhere.
        assert "login.password" in repr(action)

    def test_an_action_cannot_carry_both(self) -> None:
        # Somebody would have to decide which wins, and the wrong answer prints a password.
        with pytest.raises(InvalidEntityError, match="never both"):
            BrowserAction(
                type=BrowserActionType.FILL,
                intent="type the password",
                target=ActionTarget(label="Password"),
                value="hunter2",
                secret_ref=SecretName("login.password"),
                side_effect=True,
                idempotency_strategy=IdempotencyStrategy.VERIFY_BEFORE_RETRY,
                verification_strategy="the account page appears",
            )

    def test_a_secret_cannot_ride_on_an_action_that_takes_no_value(self) -> None:
        # A second path for a secret to travel is a second path nothing downstream expects.
        with pytest.raises(InvalidEntityError, match="takes no secret"):
            BrowserAction(
                type=BrowserActionType.CLICK,
                intent="press it",
                target=ActionTarget(role="button", name="Sign in"),
                secret_ref=SecretName("login.password"),
                side_effect=True,
                idempotency_strategy=IdempotencyStrategy.VERIFY_BEFORE_RETRY,
                verification_strategy="the account page appears",
            )

    @pytest.mark.parametrize("bad", ["login password", "LOGIN", "a\nb", "</secret>", ""])
    def test_a_name_that_could_carry_structure_into_a_prompt_is_refused(self, bad: str) -> None:
        # The name reaches a prompt. A name able to hold a newline or an angle bracket is
        # a name able to look like a delimiter once it is there.
        with pytest.raises(InvalidEntityError):
            SecretName(bad)


class TestPolicyScopeReachesInsideTheApplication:
    def test_a_forbidden_prefix_is_refused_and_named(self) -> None:
        decision = evaluate_action(
            navigate_to("https://app.test/admin/users"), policy_for(forbidden=("/admin",))
        )

        assert decision.allowed is False
        assert decision.violation is PolicyViolation.PATH_FORBIDDEN
        # Named, so the refusal sends nobody to read the policy to find out which rule.
        assert "/admin" in decision.detail

    def test_a_prefix_matches_segments_and_not_letters(self) -> None:
        # `/administrators` is a different area of the application, and forbidding
        # `/admin` was not a statement about it.
        allowed = evaluate_action(
            navigate_to("https://app.test/administrators"), policy_for(forbidden=("/admin",))
        )

        assert allowed.allowed is True

    def test_the_prefix_itself_is_forbidden_not_only_what_is_under_it(self) -> None:
        decision = evaluate_action(
            navigate_to("https://app.test/admin"), policy_for(forbidden=("/admin",))
        )

        assert decision.allowed is False

    @pytest.mark.parametrize("written", ["/admin", "admin", "/admin/"])
    def test_one_rule_however_it_was_written(self, written: str) -> None:
        # Three spellings of the same intention. A policy that honoured one of them is a
        # policy whose fence depends on a trailing slash.
        decision = evaluate_action(
            navigate_to("https://app.test/admin/users"), policy_for(forbidden=(written,))
        )

        assert decision.allowed is False

    def test_the_origin_still_decides_first(self) -> None:
        # The path fence narrows the allowlist; it is not a way through it.
        decision = evaluate_action(
            navigate_to("https://elsewhere.test/public"), policy_for(forbidden=("/admin",))
        )

        assert decision.violation is PolicyViolation.ORIGIN_NOT_ALLOWED

    def test_a_policy_that_forbids_nothing_allows_the_application(self) -> None:
        assert evaluate_action(navigate_to("https://app.test/admin"), policy_for()).allowed


class TestAnExpiredSessionIsNotADefect:
    def test_it_blocks_the_run_and_never_accuses_the_product(self) -> None:
        # The page comes back as a login form and the criterion's literal is absent. A
        # deterministic check would call that `failed`, which accuses an application that
        # is working exactly as designed.
        assert FailureKind.SESSION in BLOCKING_KINDS
        assert FailureKind.SESSION not in PRODUCT_DEFECT_KINDS

    def test_it_is_told_apart_from_the_site_being_down(self) -> None:
        # Different people read these and fix them in different places, so they have to
        # survive as different strings all the way into a report. Asserted on the values
        # rather than on the members: two members aliased to one string are one kind by
        # the time anything reads them back.
        kinds = {kind.value for kind in FailureKind}

        assert FailureKind.SESSION.value == "session"
        assert len(kinds) == len(list(FailureKind))
