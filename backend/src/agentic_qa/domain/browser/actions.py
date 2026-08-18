"""Typed browser actions (Browser bounded context).

The action set is **closed** and mirrors `contracts/browser-action.schema.json`.
That closure is the security control: there is no `evaluate`/`execute_script`
member, so arbitrary JavaScript is not something the agent can ask for — not a
capability guarded by a flag, but one that does not exist (docs/07, docs/13).

Targets are semantic (role/name/label/text) rather than coordinates, so an action
says what it means and can be verified afterwards.
"""

from dataclasses import dataclass, field
from enum import StrEnum

from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.domain.validation import require_text


class BrowserActionType(StrEnum):
    NAVIGATE = "navigate"
    CLICK = "click"
    FILL = "fill"
    SELECT = "select"
    CHECK = "check"
    UNCHECK = "uncheck"
    UPLOAD = "upload"
    PRESS_KEY = "press_key"
    WAIT_FOR = "wait_for"
    EXTRACT = "extract"
    ASSERT_TEXT = "assert_text"
    ASSERT_URL = "assert_url"
    SCREENSHOT = "screenshot"
    BACK = "back"


READ_ONLY_ACTIONS = frozenset(
    {
        BrowserActionType.WAIT_FOR,
        BrowserActionType.EXTRACT,
        BrowserActionType.ASSERT_TEXT,
        BrowserActionType.ASSERT_URL,
        BrowserActionType.SCREENSHOT,
        BrowserActionType.BACK,
        BrowserActionType.NAVIGATE,
    }
)
"""Actions that cannot change the target's state.

Everything else may, so it must declare `side_effect` and carry a verification
strategy (docs/02 action safety fields).
"""


class IdempotencyStrategy(StrEnum):
    NONE_READ_ONLY = "none_read_only"
    IDEMPOTENCY_KEY = "idempotency_key"
    VERIFY_BEFORE_RETRY = "verify_before_retry"
    NON_RETRYABLE_REQUIRES_HUMAN = "non_retryable_requires_human"


@dataclass(frozen=True)
class ActionTarget:
    """Semantic locator. Coordinates are deliberately absent from v1."""

    role: str | None = None
    name: str | None = None
    label: str | None = None
    text: str | None = None
    url: str | None = None

    def is_empty(self) -> bool:
        return not any((self.role, self.name, self.label, self.text, self.url))


@dataclass(frozen=True)
class BrowserAction:
    type: BrowserActionType
    intent: str
    target: ActionTarget = field(default_factory=ActionTarget)
    value: str | None = None
    side_effect: bool = False
    idempotency_strategy: IdempotencyStrategy = IdempotencyStrategy.NONE_READ_ONLY
    expected_postconditions: tuple[str, ...] = field(default=())
    verification_strategy: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "intent", require_text(self.intent, field="intent"))

        if self.type is BrowserActionType.NAVIGATE and not self.target.url:
            raise InvalidEntityError("navigate requires a target url")
        if self.type in _NEEDS_TARGET and self.target.is_empty():
            raise InvalidEntityError(f"{self.type} requires a semantic target")
        if self.type in _NEEDS_VALUE and not self.value:
            raise InvalidEntityError(f"{self.type} requires a value")

        if self.side_effect:
            if self.idempotency_strategy is IdempotencyStrategy.NONE_READ_ONLY:
                # A write that claims to need no retry strategy is how duplicate
                # side effects get created after a crash (docs/05).
                raise InvalidEntityError(
                    "a side-effecting action needs a real idempotency strategy"
                )
            if not self.verification_strategy:
                raise InvalidEntityError("a side-effecting action needs a verification strategy")
        elif self.type not in READ_ONLY_ACTIONS:
            raise InvalidEntityError(f"{self.type} changes state and must declare side_effect")


_NEEDS_TARGET = frozenset(
    {
        BrowserActionType.CLICK,
        BrowserActionType.FILL,
        BrowserActionType.SELECT,
        BrowserActionType.CHECK,
        BrowserActionType.UNCHECK,
        BrowserActionType.UPLOAD,
        BrowserActionType.WAIT_FOR,
        BrowserActionType.EXTRACT,
    }
)

_NEEDS_VALUE = frozenset(
    {
        BrowserActionType.FILL,
        BrowserActionType.SELECT,
        BrowserActionType.UPLOAD,
        BrowserActionType.PRESS_KEY,
        BrowserActionType.ASSERT_TEXT,
        BrowserActionType.ASSERT_URL,
    }
)
