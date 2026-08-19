"""Structured output contracts for model decisions.

A model does not return prose that we then interpret: it returns JSON matching these
schemas, and anything that fails validation is rejected. That rejection is the Phase
06 gate — invalid model output must never reach Playwright.

The action vocabulary here is the *same closed set* the browser accepts, so a model
cannot name a capability that does not exist (there is no `evaluate`, no
`execute_script`).
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from agentic_qa.domain.browser.actions import (
    READ_ONLY_ACTIONS,
    ActionTarget,
    BrowserAction,
    BrowserActionType,
    IdempotencyStrategy,
)


class DecisionTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str | None = Field(default=None, max_length=50)
    name: str | None = Field(default=None, max_length=200)
    label: str | None = Field(default=None, max_length=200)
    text: str | None = Field(default=None, max_length=200)
    url: str | None = Field(default=None, max_length=2000)

    def to_domain(self) -> ActionTarget:
        return ActionTarget(
            role=self.role, name=self.name, label=self.label, text=self.text, url=self.url
        )


class BrowserDecision(BaseModel):
    """One step the model proposes. `finished=true` means it proposes nothing."""

    model_config = ConfigDict(extra="forbid")

    finished: bool = False
    action_type: BrowserActionType | None = None
    intent: str | None = Field(default=None, max_length=500)
    target: DecisionTarget | None = None
    value: str | None = Field(default=None, max_length=4000)
    side_effect: bool = False
    """The model's own read. It can only *raise* the safety level — see below."""

    rationale: str = Field(default="", max_length=2000)
    """Model-derived by definition; recorded, never treated as an observation."""

    def to_domain_action(self) -> BrowserAction | None:
        """Build the typed action, letting domain invariants reject nonsense.

        Nothing is coerced here: a decision missing what its action type requires
        raises out of the domain rather than being patched into something plausible.

        Whether an action changes state is decided by its *type*, not by the model.
        Anything outside the read-only set is treated as side-effecting even if the
        model claimed otherwise, so a model cannot talk its way into an unverified
        click on "Delete account". The flag only lets it go the other way — marking a
        nominally read-only navigation as state-changing when it knows better.
        """
        if self.finished or self.action_type is None:
            return None

        side_effect = self.side_effect or self.action_type not in READ_ONLY_ACTIONS
        return BrowserAction(
            type=self.action_type,
            intent=self.intent or f"perform {self.action_type}",
            target=(self.target or DecisionTarget()).to_domain(),
            value=self.value,
            side_effect=side_effect,
            idempotency_strategy=(
                IdempotencyStrategy.VERIFY_BEFORE_RETRY
                if side_effect
                else IdempotencyStrategy.NONE_READ_ONLY
            ),
            verification_strategy=(
                "verify the expected postcondition on the resulting page" if side_effect else None
            ),
        )


class ExtractionResult(BaseModel):
    """Structured extraction output (docs/08 STRUCTURED_EXTRACTION)."""

    model_config = ConfigDict(extra="forbid")

    found: bool
    value: str | None = Field(default=None, max_length=8000)
    confidence: float | None = Field(default=None, ge=0, le=1)


class VerificationJudgement(BaseModel):
    """Semantic verification. Last in the priority order, never first (docs/06)."""

    model_config = ConfigDict(extra="forbid")

    verdict: Literal["satisfied", "not_satisfied", "unclear"]
    reasoning: str = Field(default="", max_length=2000)
    model_derived: Literal[True] = True
    """Structural reminder that a judgement is a hypothesis, not evidence."""
