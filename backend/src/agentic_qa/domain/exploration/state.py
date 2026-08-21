"""What "the same page" means to an explorer.

An exploring agent has to answer one question thousands of times: have I been here
before? Answering it with the raw DOM makes every render a new place — a timestamp in
the footer, one more row in a table, a different order id — and the crawl never ends
while the report claims the whole application changed overnight.

So a state is identified by what it *offers*, not by what it says. The signature is
built from the route and the set of interactive affordances, both normalised: two pages
with the same controls are the same state even when every value on them differs. That
is the same rule Phase 11 applies to failures, for the same reason — grouping has to be
something a human can disagree with, and "the DOM bytes differ" is not.
"""

import hashlib
import json
import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from agentic_qa.domain.browser.urls import safe_url

MAX_AFFORDANCES = 200
"""Affordances kept per state.

A page with a thousand controls is a list, and its thousandth link tells an explorer
nothing its tenth did not. Bounded so a signature stays cheap and a state map stays
readable; the cap is applied after sorting, so which ones survive is deterministic.
"""

CLICKABLE_ROLES = frozenset(
    {"link", "button", "tab", "menuitem", "menuitemcheckbox", "menuitemradio", "option"}
)
"""Affordances an explorer can actually take, with nothing but the page to go on.

A textbox or a combobox still *identifies* a state — a page with a search box is not
the same page without one — but taking one needs a value, and inventing values is what
`synthetic_data_allowed` and a plan are for. An explorer that typed guesses into forms
would be generating side effects nobody asked for.
"""

MAX_NAME_CHARS = 80

MAX_DESCRIBED_AFFORDANCES = 40
"""Affordances shown to a planner, as opposed to kept for a signature.

A signature can afford two hundred; a prompt rebuilt on every step cannot, and a model
choosing between forty controls is not helped by the forty-first."""

MAX_CONTENT_CHARS = 6000
"""Page text shown to a planner.

A budget in characters rather than a list of allowed node types: the cost worth guarding
against is a data grid with ten thousand rows, and dropping every text node to avoid it
also drops the four lines a criterion is about.

The number is calibrated, not guessed. Three pages: an application screen's whole
accessible tree was 883 characters; a marketing landing's was 9,183, of which the text
nodes are roughly 4,300. A first attempt at 2,000 truncated that landing before three of
its four section headings, and a run against it could see one criterion and never the
rest — the marker said so, which is why the cap is a number and not a silent slice. Six
thousand carries a long landing whole and still refuses a table.
"""

_UUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)
_LONG_NUMBER = re.compile(r"\d{2,}")
_WHITESPACE = re.compile(r"\s+")
_NUMERIC_SEGMENT = re.compile(r"^\d+$")
_HEX_SEGMENT = re.compile(r"^[0-9a-f]{8,}$", re.I)


@dataclass(frozen=True)
class Affordance:
    """One thing a page offers to do, named the way a human would name it.

    Role plus accessible name, never a CSS selector or an element id: a selector is a
    fact about today's markup, and an explorer that remembers selectors rediscovers the
    whole application every time someone renames a class.
    """

    role: str
    name: str
    url: str | None = None
    """Where a link goes, when the page said so. Absolute, always.

    Whoever builds one resolves it against the page first: a relative `/records` has no
    origin, and an origin allowlist asked about it can only refuse.

    It changes *how* the affordance is taken, not what it is: a link with a url can be
    followed by navigating, which is a read-only action, while a button can only be
    clicked, which may change the world. That distinction is what lets an exploration
    run under a read-only policy at all.

    Deliberately not part of `key`: ten rows linking to ten order pages are one thing
    to try, and the url of the first is a fine representative.
    """

    disabled: bool = False
    """Whether the page currently refuses this control.

    The snapshot has always said so — `button "Sign in" [disabled]` — and dropping it
    left the agent proposing actions on controls that cannot be taken, paying a full
    locator timeout to learn what the observation already knew. A form that enables its
    submit only once the fields are filled is ordinary, and it was invisible.

    **Deliberately not part of `key`, and this one is load-bearing.** `key` feeds
    `state_signature`, so putting a transient state in it would give every stored
    exploration baseline and every memory fingerprint a new meaning overnight — silently,
    since nothing would fail. A control that greys out is the same control.
    """

    @property
    def is_clickable(self) -> bool:
        """Whether an explorer can take this with no information beyond the page.

        A disabled control is not takeable: offering it to the frontier would spend an
        action and an entry on something the page has already refused.
        """
        return not self.disabled and self.role.strip().lower() in CLICKABLE_ROLES

    @property
    def key(self) -> str:
        """What identifies this affordance across renders, with the volatile parts gone.

        "Order 8821" and "Order 9007" collapse to one key. Without that, a list page
        has a different signature for every row count it has ever had, and an explorer
        crawls the same table forever.
        """
        return f"{self.role.strip().lower()}:{normalize_name(self.name)}"


@dataclass(frozen=True)
class PageState:
    """A page reduced to where it is and what it offers.

    A state map is kept for weeks and compared night after night, so the url it holds
    is the safe one: scheme, host and path. Applications put session tokens in query
    strings, and a token stored here would outlive the session that issued it, in a
    table nobody thinks of as holding credentials.
    """

    url: str
    """Sanitised on construction — see `safe_url`. Whatever a caller passes in, what
    this object holds is safe to store, log and put in a report."""

    affordances: tuple[Affordance, ...] = field(default=())
    title: str = ""
    """Recorded for the report, never for the signature: a title carrying a cart count
    would make every cart change a new state."""

    content: tuple[str, ...] = field(default=())
    """What the page says, for the planner to read.

    Never for the signature: a state identified by its text would be a new state every
    time a footer date rolled over, which is the whole reason signatures are built from
    affordances. And not persisted with the state map either — this is what the planner
    is shown at observation time, not a fact about the state worth keeping for weeks.
    """

    def __post_init__(self) -> None:
        object.__setattr__(self, "url", safe_url(self.url))

    @property
    def route(self) -> str:
        """Path with identifier-shaped segments replaced.

        `/orders/8821` and `/orders/9007` are the same place. The query string is
        dropped entirely: the same page reached with different parameters is the same
        page, and keeping them would fork a state per filter combination.
        """
        parts = urlsplit(self.url)
        segments = [_normalize_segment(segment) for segment in parts.path.split("/")]
        return "/".join(segments) or "/"

    @property
    def origin(self) -> str:
        parts = urlsplit(self.url)
        if not parts.scheme or not parts.hostname:
            return ""
        port = f":{parts.port}" if parts.port is not None else ""
        return f"{parts.scheme}://{parts.hostname}{port}"

    @property
    def affordance_keys(self) -> tuple[str, ...]:
        """Sorted, deduplicated and bounded — so a signature does not depend on the
        order the page happened to render in, nor on how many rows a table had."""
        return tuple(sorted({affordance.key for affordance in self.affordances}))[:MAX_AFFORDANCES]

    @property
    def signature(self) -> str:
        return state_signature(self.route, self.affordance_keys)

    def describe(self) -> str:
        """The page as a planner can read it: where it is, what it says, what it offers.

        A planner given only a url has to guess at element names, and a guess costs a
        locator timeout before anyone learns it was wrong. Naming what is actually on
        the page is the difference between choosing and inventing.

        `text` and `elements` are separate sections on purpose. They answer different
        questions — "is the goal already true?" and "what can I do next?" — and a planner
        that has to infer the first from a list of buttons answers neither. Withholding
        the text is what made an assertion-shaped goal unreachable: the run could see the
        controls around a heading and never the heading.

        Bounded on purpose, and separately per section: this is rebuilt on every step, so
        a prompt that grows with the page is a cost that grows with the run.
        """
        header = f"url: {self.url or 'about:blank'}"
        if self.title:
            header += f"\ntitle: {self.title}"

        sections = [header]

        if self.content:
            sections.append("text:\n" + "\n".join(f"- {line}" for line in self.content))

        offers = [
            f"- {affordance.role}: {affordance.name}"
            # Said, not implied by absence. A planner that reads a disabled control as
            # available spends an action and a locator timeout finding out otherwise.
            + (" [disabled]" if affordance.disabled else "")
            + (f" -> {affordance.url}" if affordance.url else "")
            for affordance in self.affordances[:MAX_DESCRIBED_AFFORDANCES]
        ]
        if offers:
            more = len(self.affordances) - len(offers)
            tail = f"\n- ... and {more} more" if more > 0 else ""
            sections.append("elements:\n" + "\n".join(offers) + tail)
        else:
            sections.append("(no interactive elements found)")

        return "\n".join(sections)


def state_signature(route: str, affordance_keys: tuple[str, ...]) -> str:
    """Stable id for a state. Same route and same offers means same id, anywhere."""
    payload = json.dumps([route, list(affordance_keys)], separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def normalize_name(value: str) -> str:
    text = _UUID.sub("<id>", value.strip().lower())
    text = _LONG_NUMBER.sub("<n>", text)
    return _WHITESPACE.sub(" ", text).strip()[:MAX_NAME_CHARS]


def _normalize_segment(segment: str) -> str:
    if _NUMERIC_SEGMENT.match(segment) or _UUID.fullmatch(segment) or _HEX_SEGMENT.match(segment):
        return "<id>"
    return segment.lower()
