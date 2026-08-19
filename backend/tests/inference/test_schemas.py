"""What a model is allowed to say, and what happens when it says something else.

These are the first half of the phase gate: output that does not satisfy the contract
must be rejected here, before anything downstream has a chance to act on it.
"""

import pytest
from pydantic import ValidationError

from agentic_qa.domain.browser.actions import BrowserActionType, IdempotencyStrategy
from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.infrastructure.inference.schemas import (
    BrowserDecision,
    DecisionTarget,
    VerificationJudgement,
)


def test_a_valid_decision_becomes_a_domain_action() -> None:
    decision = BrowserDecision.model_validate_json(
        '{"action_type": "click", "intent": "open the cart",'
        ' "target": {"role": "button", "name": "Cart"}, "rationale": "the cart is next"}'
    )

    action = decision.to_domain_action()

    assert action is not None
    assert action.type is BrowserActionType.CLICK
    assert action.target.name == "Cart"


def test_a_model_cannot_ask_for_javascript_execution() -> None:
    """The closed action set is the control, so `evaluate` fails as an unknown value."""
    with pytest.raises(ValidationError):
        BrowserDecision.model_validate_json(
            '{"action_type": "evaluate", "intent": "run a script", "value": "alert(1)"}'
        )


def test_unknown_fields_are_rejected_rather_than_ignored() -> None:
    """Silently dropping an unknown field hides a contract drift until it matters."""
    with pytest.raises(ValidationError):
        BrowserDecision.model_validate_json(
            '{"action_type": "back", "intent": "go back", "javascript": "alert(1)"}'
        )


def test_a_finished_decision_carries_no_action() -> None:
    decision = BrowserDecision.model_validate_json('{"finished": true, "rationale": "done"}')

    assert decision.to_domain_action() is None


def test_an_action_missing_what_it_needs_is_refused_by_the_domain() -> None:
    """The schema accepts a click with no target; the domain does not."""
    decision = BrowserDecision(action_type=BrowserActionType.CLICK, intent="click something")

    with pytest.raises(InvalidEntityError):
        decision.to_domain_action()


def test_a_side_effecting_action_gets_a_retry_and_verification_strategy() -> None:
    """A write that arrives with no safety fields must not become one without them."""
    decision = BrowserDecision(
        action_type=BrowserActionType.CLICK,
        intent="submit the order",
        target=DecisionTarget(role="button", name="Place order"),
        side_effect=True,
    )

    action = decision.to_domain_action()

    assert action is not None
    assert action.idempotency_strategy is IdempotencyStrategy.VERIFY_BEFORE_RETRY
    assert action.verification_strategy


def test_a_model_cannot_declare_a_state_changing_action_harmless() -> None:
    """`side_effect: false` on a click is not believed — the action type decides."""
    decision = BrowserDecision(
        action_type=BrowserActionType.CLICK,
        intent="delete the account",
        target=DecisionTarget(role="button", name="Delete account"),
        side_effect=False,
    )

    action = decision.to_domain_action()

    assert action is not None
    assert action.side_effect is True
    assert action.idempotency_strategy is IdempotencyStrategy.VERIFY_BEFORE_RETRY


def test_a_model_may_escalate_a_read_only_action() -> None:
    """The flag works in the safe direction: a GET that confirms something is a write."""
    decision = BrowserDecision(
        action_type=BrowserActionType.NAVIGATE,
        intent="follow the confirmation link",
        target=DecisionTarget(url="http://target.test/confirm?token=abc"),
        side_effect=True,
    )

    action = decision.to_domain_action()

    assert action is not None
    assert action.side_effect is True
    assert action.verification_strategy


def test_a_plain_read_stays_a_read() -> None:
    decision = BrowserDecision(
        action_type=BrowserActionType.ASSERT_URL,
        intent="confirm we landed on the cart",
        value="http://target.test/cart",
    )

    action = decision.to_domain_action()

    assert action is not None
    assert action.side_effect is False
    assert action.idempotency_strategy is IdempotencyStrategy.NONE_READ_ONLY


def test_a_judgement_cannot_declare_itself_an_observation() -> None:
    """`model_derived` is pinned to True: a hypothesis never becomes evidence."""
    with pytest.raises(ValidationError):
        VerificationJudgement.model_validate_json(
            '{"verdict": "satisfied", "model_derived": false}'
        )
