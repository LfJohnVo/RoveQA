"""UserStory aggregate (QA bounded context).

Mirrors contracts/user-story-contract.schema.json: a story is only executable when
it carries at least one uniquely identified acceptance criterion.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.domain.validation import require_identifier, require_text


@dataclass(frozen=True)
class AcceptanceCriterion:
    criterion_id: str
    description: str
    verification_hint: str | None = None

    def __post_init__(self) -> None:
        # frozen dataclass: normalize through object.__setattr__
        object.__setattr__(
            self, "criterion_id", require_identifier(self.criterion_id, field="criterion_id")
        )
        object.__setattr__(self, "description", require_text(self.description, field="description"))
        if self.verification_hint is not None:
            object.__setattr__(
                self,
                "verification_hint",
                require_text(self.verification_hint, field="verification_hint"),
            )


@dataclass
class UserStory:
    story_id: str
    project_id: str
    actor: str
    goal: str
    acceptance_criteria: tuple[AcceptanceCriterion, ...]
    preconditions: tuple[str, ...] = field(default=())
    forbidden_outcomes: tuple[str, ...] = field(default=())

    def __post_init__(self) -> None:
        self.story_id = require_identifier(self.story_id, field="story_id")
        self.project_id = require_identifier(self.project_id, field="project_id")
        self.actor = require_text(self.actor, field="actor")
        self.goal = require_text(self.goal, field="goal")
        self.acceptance_criteria = tuple(self.acceptance_criteria)
        if not self.acceptance_criteria:
            raise InvalidEntityError("a user story needs at least one acceptance criterion")
        self._reject_duplicate_criteria(self.acceptance_criteria)
        self.preconditions = _clean_lines(self.preconditions, field_name="preconditions")
        self.forbidden_outcomes = _clean_lines(
            self.forbidden_outcomes, field_name="forbidden_outcomes"
        )

    @staticmethod
    def _reject_duplicate_criteria(criteria: Sequence[AcceptanceCriterion]) -> None:
        seen: set[str] = set()
        for criterion in criteria:
            if criterion.criterion_id in seen:
                raise InvalidEntityError(
                    f"duplicate acceptance criterion id: {criterion.criterion_id}"
                )
            seen.add(criterion.criterion_id)


def _clean_lines(values: Iterable[str], *, field_name: str) -> tuple[str, ...]:
    return tuple(require_text(value, field=field_name) for value in values)
