"""What the browser saw go wrong, that belongs to no acceptance criterion.

A JavaScript exception or an image answering 404 is first-class QA signal on any site,
and it fits nowhere in `CriterionResult`: that type answers *a criterion*, and its
identity is `(run, criterion_id)`. A landing page has no criteria at all, and even a
story-driven run sees things the story never asked about.

The distinction this file exists to hold: **an observation is not a verdict.** Only a
deterministic check against a criterion may accuse the product (docs/00). A console
error is worth reporting precisely when it is strange, and reporting it must never be
the same act as blaming the application for it.
"""

from dataclasses import dataclass
from enum import StrEnum

from agentic_qa.domain.errors import InvalidEntityError

MAX_DETAIL_CHARS = 2_000
"""One problem's text. A stack trace is worth keeping and a minified bundle printed to
the console is not; past this it is noise that costs storage in every run."""


class ObservedFailureKind(StrEnum):
    CONSOLE_ERROR = "console_error"
    """The page's own JavaScript threw, or logged at error level."""

    FAILED_REQUEST = "failed_request"
    """A request the page made never completed — a dead image, a 404 script, a CORS
    refusal. Distinguished from an HTTP status, which belongs to a response that did
    arrive."""


@dataclass(frozen=True)
class ObservedFailure:
    """One thing that went wrong, attributed to a run and an episode.

    Not to a page — yet. The adapter accumulates these across an episode and never
    clears between navigations, so claiming a page here would be inventing an
    attribution nobody measured. A site sweep will need that grain and will have to
    earn it; saying "this episode" is the true statement available today.
    """

    kind: ObservedFailureKind
    detail: str
    episode_index: int = 0

    def __post_init__(self) -> None:
        # Truncated, not rejected. Everywhere else in the domain an over-long string is a
        # mistake worth refusing; here it is the finding. A minified bundle printing a
        # 40 KB stack trace is exactly what someone wants to see, and raising would lose
        # the observation — or fail the run that found it.
        if not isinstance(self.detail, str):
            raise InvalidEntityError(f"detail must be a string, got {type(self.detail).__name__}")
        text = self.detail.strip()
        if not text:
            raise InvalidEntityError("detail must not be blank")
        if len(text) > MAX_DETAIL_CHARS:
            text = f"{text[:MAX_DETAIL_CHARS]}…"
        object.__setattr__(self, "detail", text)
        if self.episode_index < 0:
            raise InvalidEntityError("episode_index must not be negative")
