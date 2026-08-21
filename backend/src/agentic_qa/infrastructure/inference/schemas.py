"""Structured output contracts for model decisions.

A model does not return prose that we then interpret: it returns JSON matching these
schemas, and anything that fails validation is rejected. That rejection is the Phase
06 gate — invalid model output must never reach Playwright.

The action vocabulary here is the *same closed set* the browser accepts, so a model
cannot name a capability that does not exist (there is no `evaluate`, no
`execute_script`).
"""

from typing import TYPE_CHECKING, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, RootModel, create_model

from agentic_qa.domain.browser.actions import (
    NEEDS_TARGET,
    NEEDS_VALUE,
    READ_ONLY_ACTIONS,
    ActionTarget,
    BrowserAction,
    BrowserActionType,
    IdempotencyStrategy,
)


class DecisionTarget(BaseModel):
    """Semantic locator, for the actions that read one."""

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


class NavigationTarget(BaseModel):
    """Where to navigate. `url` is required here because the domain requires it there."""

    model_config = ConfigDict(extra="forbid")

    url: str = Field(max_length=2000)

    def to_domain(self) -> ActionTarget:
        return ActionTarget(url=self.url)


class _DecisionBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rationale: str = Field(default="", max_length=2000)
    """Model-derived by definition; recorded, never treated as an observation."""

    def to_domain_action(self) -> BrowserAction | None:
        """Build the typed action, or None when the planner proposes nothing.

        Whether an action changes state is decided by its *type*, not by the model.
        Anything outside the read-only set is treated as side-effecting even if the model
        claimed otherwise, so a model cannot talk its way into an unverified click on
        "Delete account". The flag only lets it go the other way — marking a nominally
        read-only action as state-changing when it knows better.
        """
        action_type = getattr(self, "action_type", None)
        if action_type is None:
            return None

        target = getattr(self, "target", None)
        side_effect = bool(getattr(self, "side_effect", False)) or (
            action_type not in READ_ONLY_ACTIONS
        )
        return BrowserAction(
            type=action_type,
            intent=getattr(self, "intent", "") or f"perform {action_type}",
            target=target.to_domain() if target is not None else ActionTarget(),
            value=getattr(self, "value", None),
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


class FinishedDecision(_DecisionBase):
    """The planner proposes nothing further: the goal is already satisfied."""

    model_config = ConfigDict(extra="forbid")

    finished: Literal[True]


def _variant_for(action_type: BrowserActionType) -> type[_DecisionBase]:
    """One model per action, with its requirements derived from the domain's own sets.

    Generated rather than hand-written for the reason `prompts.py` renders those same
    frozensets: a copy would drift, and the drift would be silent. A member added to
    `NEEDS_VALUE` changes what the model is *able* to emit, in the same commit.
    """
    fields: dict[str, Any] = {
        "finished": (Literal[False], False),
        "action_type": (Literal[action_type], ...),
        "intent": (str, Field(max_length=500)),
        "side_effect": (bool, False),
    }

    # A target only exists on the actions that read one. `assert_text` used to accept a
    # target its execution ignores, and that field is exactly where the literal landed.
    if action_type is BrowserActionType.NAVIGATE:
        fields["target"] = (NavigationTarget, ...)
    elif action_type in NEEDS_TARGET:
        fields["target"] = (DecisionTarget, ...)

    if action_type in NEEDS_VALUE:
        fields["value"] = (str, Field(max_length=4000))

    return create_model(
        f"{action_type.value.title().replace('_', '')}Decision",
        __base__=_DecisionBase,
        **fields,
    )


ACTION_VARIANTS: tuple[type[_DecisionBase], ...] = tuple(
    _variant_for(action_type) for action_type in BrowserActionType
)

if TYPE_CHECKING:
    # A static checker cannot name the members of a union assembled at import time, so it
    # is given the common base instead — which is precisely the interface `BrowserDecision`
    # exposes, so nothing is lost. Pydantic gets the real union, which is what constrains
    # generation. What guards the set is a test: every member of `BrowserActionType` must
    # have a variant, so an action added to the domain fails the suite rather than quietly
    # becoming impossible to ask for.
    _DecisionRoot = _DecisionBase
else:
    # `Union[...]` rather than `X | Y`: the members come from a tuple built at import
    # time, and the operator form cannot be applied to one.
    _DecisionRoot = Union[tuple([FinishedDecision, *ACTION_VARIANTS])]  # noqa: UP007


class BrowserDecision(RootModel[_DecisionRoot]):
    """One step the planner proposes, as a union the server can actually enforce.

    The old shape was one flat object whose every field was optional, so
    `required` came back empty and `response_format: json_schema` had nothing to
    hold the model to. The rule that `assert_text` needs a `value` lived only as
    prose in the prompt and as a rejection in the domain — after a model call had
    already been spent.

    A union makes the invalid combination unrepresentable rather than refused. The
    domain still validates: this narrows what can be *asked for*, and
    `BrowserAction` remains the authority on what is legal.
    """

    @property
    def rationale(self) -> str:
        return self.root.rationale

    def to_domain_action(self) -> BrowserAction | None:
        return self.root.to_domain_action()


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


class ClusterAnalysis(BaseModel):
    """A deep model's reading of one failure cluster (docs/08 ROOT_CAUSE_ANALYSIS).

    Notice what it cannot say: nothing about which failures belong to the cluster. The
    membership is decided deterministically before this is asked, and a schema with no
    field for it is how a plausible re-grouping never overwrites the evidence.
    """

    model_config = ConfigDict(extra="forbid")

    probable_cause: str = Field(max_length=2000)
    recommended_check: str = Field(max_length=1000)
    """What would confirm or kill the hypothesis. Required, because a cause nobody can
    check is prose rather than a finding."""

    confidence: Literal["low", "medium", "high"]
    model_derived: Literal[True] = True
    """Structural reminder that this is an interpretation, not an observation."""
