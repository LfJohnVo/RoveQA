"""What a model is allowed to say, and what happens when it says something else.

These are the first half of the phase gate: output that does not satisfy the contract
must be rejected here, before anything downstream has a chance to act on it.
"""

import pytest
from pydantic import ValidationError

from agentic_qa.domain.browser.actions import (
    NEEDS_VALUE,
    BrowserActionType,
    IdempotencyStrategy,
)
from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.infrastructure.inference.schemas import (
    ACTION_VARIANTS,
    BrowserDecision,
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
    decision = BrowserDecision.model_validate(
        {"action_type": BrowserActionType.CLICK, "intent": "click something", "target": {}}
    )

    with pytest.raises(InvalidEntityError):
        decision.to_domain_action()


def test_a_side_effecting_action_gets_a_retry_and_verification_strategy() -> None:
    """A write that arrives with no safety fields must not become one without them."""
    decision = BrowserDecision.model_validate(
        {
            "action_type": BrowserActionType.CLICK,
            "intent": "submit the order",
            "target": {"role": "button", "name": "Place order"},
            "side_effect": True,
        }
    )

    action = decision.to_domain_action()

    assert action is not None
    assert action.idempotency_strategy is IdempotencyStrategy.VERIFY_BEFORE_RETRY
    assert action.verification_strategy


def test_a_model_cannot_declare_a_state_changing_action_harmless() -> None:
    """`side_effect: false` on a click is not believed — the action type decides."""
    decision = BrowserDecision.model_validate(
        {
            "action_type": BrowserActionType.CLICK,
            "intent": "delete the account",
            "target": {"role": "button", "name": "Delete account"},
            "side_effect": False,
        }
    )

    action = decision.to_domain_action()

    assert action is not None
    assert action.side_effect is True
    assert action.idempotency_strategy is IdempotencyStrategy.VERIFY_BEFORE_RETRY


def test_a_model_may_escalate_a_read_only_action() -> None:
    """The flag works in the safe direction: a GET that confirms something is a write."""
    decision = BrowserDecision.model_validate(
        {
            "action_type": BrowserActionType.NAVIGATE,
            "intent": "follow the confirmation link",
            "target": {"url": "http://target.test/confirm?token=abc"},
            "side_effect": True,
        }
    )

    action = decision.to_domain_action()

    assert action is not None
    assert action.side_effect is True
    assert action.verification_strategy


def test_a_plain_read_stays_a_read() -> None:
    decision = BrowserDecision.model_validate(
        {
            "action_type": BrowserActionType.ASSERT_URL,
            "intent": "confirm we landed on the cart",
            "value": "http://target.test/cart",
        }
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


class TestTheSchemaCarriesTheRule:
    """What used to live only as prose in the prompt.

    The planner answered `{"action_type": "assert_text", "target": {"text": "Sign in"}}`
    with a correct rationale. `assert_text` reads only `value`, so the domain rejected it
    -- after a model call had already been spent, and once per loop iteration until the
    budget ran out. Guided decoding could not help: every field on the old model was
    optional, so `required` came back empty.
    """

    def test_an_assertion_without_its_literal_cannot_be_expressed(self) -> None:
        with pytest.raises(ValidationError):
            BrowserDecision.model_validate(
                {
                    "action_type": BrowserActionType.ASSERT_TEXT,
                    "intent": "check the heading",
                    "target": {"text": "Sign in"},
                }
            )

    def test_an_assertion_with_its_literal_is_fine(self) -> None:
        decision = BrowserDecision.model_validate(
            {
                "action_type": BrowserActionType.ASSERT_TEXT,
                "intent": "check the heading",
                "value": "Sign in",
            }
        )

        action = decision.to_domain_action()

        assert action is not None
        assert action.value == "Sign in"

    def test_an_action_that_reads_no_target_is_not_offered_one(self) -> None:
        # The field the literal landed in does not exist on this variant at all.
        with pytest.raises(ValidationError):
            BrowserDecision.model_validate(
                {
                    "action_type": BrowserActionType.ASSERT_TEXT,
                    "intent": "check the heading",
                    "value": "Sign in",
                    "target": {"text": "Sign in"},
                }
            )

    def test_navigation_without_a_url_cannot_be_expressed(self) -> None:
        with pytest.raises(ValidationError):
            BrowserDecision.model_validate(
                {"action_type": BrowserActionType.NAVIGATE, "intent": "go to the app"}
            )

    def test_every_action_the_domain_knows_has_a_variant(self) -> None:
        """The drift guard. A member added to the enum or to either requirement set
        changes what the model can emit in the same commit, or this fails."""
        covered = {
            variant.model_fields["action_type"].annotation.__args__[0]  # type: ignore[union-attr]
            for variant in ACTION_VARIANTS
        }

        assert covered == set(BrowserActionType)

    def test_a_valued_action_requires_its_value(self) -> None:
        for action_type in NEEDS_VALUE:
            with pytest.raises(ValidationError, match="value"):
                BrowserDecision.model_validate(
                    {"action_type": action_type, "intent": "try it", "target": {"role": "button"}}
                )
