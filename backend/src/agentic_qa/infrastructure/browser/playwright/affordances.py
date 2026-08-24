"""Reading a page's affordances out of Playwright's ARIA snapshot.

An explorer needs to know what a page *offers*, and the accessible tree is the honest
answer: role plus accessible name is what a person perceives and what survives a CSS
refactor. Selectors would not — an explorer that remembered them would rediscover the
whole application every time somebody renamed a class.

Why parse a snapshot rather than run a script in the page: there is no `evaluate` in
this system, deliberately (docs/07, docs/13). The closed action set is the security
boundary, and adding a JS escape hatch for the explorer's convenience would put a hole
in it that no policy check sees.

The snapshot format is Playwright's, so this parser is pinned to a tool version by
nature — which is exactly why there is an integration test against real Chromium. A
format change has to fail loudly there rather than quietly return "this page offers
nothing", which an explorer would read as a dead end.
"""

import re
from urllib.parse import urljoin, urlsplit

from agentic_qa.domain.exploration.state import (
    MAX_AFFORDANCES,
    MAX_CONTENT_CHARS,
    Affordance,
)

_WHITESPACE = re.compile(r"\s+")

INTERACTIVE_ROLES = frozenset(
    {
        "button",
        "checkbox",
        "combobox",
        "link",
        "listbox",
        "menuitem",
        "menuitemcheckbox",
        "menuitemradio",
        "option",
        "radio",
        "searchbox",
        "slider",
        "spinbutton",
        "switch",
        "tab",
        "textbox",
    }
)
"""Roles that represent something a user can *do*.

Structural roles — heading, banner, main, list, paragraph, img — are left out on
purpose. They describe how a page is arranged, and including them would make a
reflowed layout look like a new state while telling an explorer nothing it can act on.
"""

_LINE = re.compile(r'^(\s*)-\s+([a-z]+)(?:\s+"([^"]*)")?((?:\s*\[[^\]]*\])*)(.*)$')
_URL_LINE = re.compile(r"^(\s*)-\s+/url:\s*(\S+)")
_TEXT_LINE = re.compile(
    # A heading carries its level as a trailing attribute -- `[level=1]` -- so the
    # name cannot be anchored to end of line. Missing that dropped every heading,
    # which is where a page says what it is.
    r'^\s*-\s+(heading|paragraph|text)(?:\s+"([^"]*)"(?:\s*\[[^\]]*\])*|:\s*(.*))?\s*$'
)

_DISABLED = re.compile(r"\[disabled\]")
_HAS_VALUE = re.compile(r"^\s*:\s*\S")
"""Whether the snapshot showed a value after the control's name.

The snapshot writes `- textbox "Reference": BASELINE`, and the *fact* is what matters:
an agent that cannot tell a filled field from an empty one fills the same field until
its budget runs out. Twenty-four times, measured.

The value itself is deliberately not read. A password field carries one, and an
observation is rendered into a prompt, stored in a state map and read by a person."""

TEXT_ROLES = frozenset({"heading", "paragraph", "text"})
"""Roles that carry what the page *says*, as opposed to what it offers.

Kept separate from `INTERACTIVE_ROLES` on purpose: these can never be acted on, so they
have no business in the frontier — and a planner asked to confirm "the page shows X"
cannot answer without them. Both readings come from the same snapshot; only one of them
used to survive it.
"""


def unquote_snapshot_value(value: str) -> str:
    """Strip the quotes Playwright adds around a value that needs them.

    The snapshot writes `/url: "#"` and `- text: "@2025 Acme"` — quoted because `#` and
    `@` would otherwise be read as syntax. Keeping the quotes turned `#contact` into the
    path `/"#contact"`, which no origin allowlist can resolve and no browser can open.

    The same slip would be worse in text: a criterion looking for `@2025 Acme` would not
    match `"@2025 Acme"`, and a deterministic criterion that fails is the one verdict
    that accuses the product. One helper, both readings.
    """
    text = value.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        return text[1:-1]
    return text


_BULLET_OVERHEAD = 3
"""What `PageState.describe()` adds around each kept value: a dash, a space and a
newline. Counted so the parser's budget and the rendered size mean the same thing."""

MAX_SNAPSHOT_LINES = 4000
"""Bound on how much of a snapshot is read.

A page with tens of thousands of nodes is a data grid; its ten-thousandth row offers
nothing its tenth did not, and reading all of it would make one observation cost more
than the action that follows it.
"""


def parse_affordances(snapshot: str, *, base_url: str = "") -> tuple[Affordance, ...]:
    """Pull role/name pairs out of an ARIA snapshot, deduplicated and bounded.

    A link's `/url:` line is attached to it when the snapshot carries one, because that
    is what lets the affordance be taken by navigating — a read-only action — instead of
    by clicking something whose effect nobody knows.

    The snapshot reports hrefs as the markup wrote them, which is usually relative, so
    they are resolved against `base_url` here. An unresolved `/records` has no origin at
    all, and an origin allowlist asked about it can only refuse — which would make every
    relative link on every page undeciable and stop an exploration at the front door.

    A nameless control is dropped rather than kept as an empty name: "button" with no
    accessible name is something neither a person nor this system can ask for, and
    keeping it would put an unreachable target in the frontier.
    """
    found: dict[str, Affordance] = {}
    pending_key: str | None = None
    pending_indent = 0

    for index, line in enumerate(snapshot.splitlines()):
        if index >= MAX_SNAPSHOT_LINES:
            break

        if pending_key is not None:
            url = _URL_LINE.match(line)
            if url is not None and len(url.group(1)) > pending_indent:
                existing = found[pending_key]
                resolved = _absolute(base_url, unquote_snapshot_value(url.group(2)))
                if existing.url is None and resolved is not None:
                    found[pending_key] = Affordance(
                        role=existing.role,
                        name=existing.name,
                        url=resolved,
                        # Carried over rather than defaulted: rebuilding the affordance
                        # to attach its url must not quietly re-enable a disabled one, or
                        # forget that a field already has something in it.
                        disabled=existing.disabled,
                        filled=existing.filled,
                    )
                pending_key = None
                continue

        match = _LINE.match(line)
        if match is None:
            continue
        pending_key = None
        indent, role, name = len(match.group(1)), match.group(2), (match.group(3) or "").strip()
        if role not in INTERACTIVE_ROLES or not name:
            continue

        affordance = Affordance(
            role=role,
            name=name,
            disabled=bool(_DISABLED.search(match.group(4) or "")),
            filled=bool(_HAS_VALUE.match(match.group(5) or "")),
        )
        # Keyed by the *normalised* key, so a table of a thousand rows collapses to the
        # handful of distinct things it actually offers before the cap is applied.
        if affordance.key not in found:
            found[affordance.key] = affordance
        pending_key, pending_indent = affordance.key, indent
        if len(found) >= MAX_AFFORDANCES:
            break
    return tuple(found.values())


def parse_text_content(snapshot: str, *, max_chars: int = MAX_CONTENT_CHARS) -> tuple[str, ...]:
    """Pull what the page *says* out of the same snapshot, deduplicated and bounded.

    This existed in the snapshot from the first day and never left this layer. A planner
    was handed the url, the title and a list of controls, and then asked to confirm goals
    like "the page shows the order was placed" — which the observation could not answer,
    so the run looped until its budget ran out with the evidence one method call away.

    Bounded by **characters, not by node type**: the cost to guard against is a data grid
    with ten thousand rows, and dropping every text node to avoid it also drops the four
    lines a criterion is about. Truncation is marked, because a planner told a partial
    page is complete will conclude the page lacks what it was looking for.
    """
    seen: set[str] = set()
    kept: list[str] = []
    spent = 0

    for index, line in enumerate(snapshot.splitlines()):
        if index >= MAX_SNAPSHOT_LINES:
            break
        match = _TEXT_LINE.match(line)
        if match is None:
            continue
        raw = match.group(2) if match.group(2) is not None else (match.group(3) or "")
        text = _WHITESPACE.sub(" ", unquote_snapshot_value(raw)).strip()
        # Empty paragraphs are layout, not content, and a real page is full of them.
        if not text or text in seen:
            continue
        # The rendered cost, not the raw length. `describe()` writes each kept value
        # as a bullet on its own line, so a budget counting only the text
        # under-reports by the three characters around it: fifteen hundred short
        # values would pass a 6,000-character check and render past ten thousand.
        rendered = len(text) + _BULLET_OVERHEAD
        if spent + rendered > max_chars:
            kept.append("… [truncated]")
            break
        seen.add(text)
        kept.append(text)
        spent += rendered

    return tuple(kept)


def _absolute(base_url: str, href: str) -> str | None:
    """Resolve an href against the page, or decline.

    `None` for anything that is not http(s) — `javascript:`, `mailto:`, a bare `#`.
    Declining leaves the affordance as a click, which the RunPolicy gates like any
    other state change, instead of handing a navigation a scheme nobody vetted.
    """
    candidate = urljoin(base_url, href) if base_url else href
    parts = urlsplit(candidate)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return None
    return candidate
