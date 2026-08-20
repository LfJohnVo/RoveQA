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

from agentic_qa.domain.exploration.state import MAX_AFFORDANCES, Affordance

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

_LINE = re.compile(r'^(\s*)-\s+([a-z]+)(?:\s+"([^"]*)")?')
_URL_LINE = re.compile(r"^(\s*)-\s+/url:\s*(\S+)")

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
                resolved = _absolute(base_url, url.group(2))
                if existing.url is None and resolved is not None:
                    found[pending_key] = Affordance(
                        role=existing.role, name=existing.name, url=resolved
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

        affordance = Affordance(role=role, name=name)
        # Keyed by the *normalised* key, so a table of a thousand rows collapses to the
        # handful of distinct things it actually offers before the cap is applied.
        if affordance.key not in found:
            found[affordance.key] = affordance
        pending_key, pending_indent = affordance.key, indent
        if len(found) >= MAX_AFFORDANCES:
            break
    return tuple(found.values())


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
