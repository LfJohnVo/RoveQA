"""Consent overlays, and the one option a run is allowed to take.

A cookie banner is the first thing an agent meets on the public web, it covers the
content, and on many sites it intercepts every click. So the agent sees it, cannot get
past it, and the run is over before it started.

The obvious fix is to press a button, and that is where this stops being a browser
problem. **Accepting cookies is a legal act performed on somebody's behalf** — consent
that must be freely given, specific, informed and unambiguous, manufactured by a process
nobody asked. Worse, "Accept all" is usually the easiest button to find: larger, higher
contrast, first in the DOM. Any heuristic optimising for "get past the overlay" lands on
the most-conceding option, by the site's design.

So the policy decides, the default is to touch nothing, and the option taken is the least
conceding one the overlay itself offers (ADR 0018).
"""

import re
from enum import StrEnum

from agentic_qa.domain.exploration.state import Affordance

_REJECT = re.compile(
    r"\b("
    r"reject|decline|refuse|deny"
    r"|only\s+(essential|necessary|required)"
    r"|(essential|necessary|required)\s+only"
    r"|no,?\s+thanks"
    r")\b",
    re.IGNORECASE,
)
"""Least-conceding, in the words banners actually use.

Ordered first everywhere it is consulted. A page offering both "Reject all" and "Accept
all" must never resolve to the second because it appeared earlier in the DOM.
"""

_MANAGE = re.compile(r"\b(manage|preferences|settings|customi[sz]e|choose)\b", re.IGNORECASE)
"""A second screen rather than a decision. Taken only when nothing rejects outright — it
concedes nothing by itself, and it at least stops the overlay from blocking the page."""

_ACCEPT = re.compile(r"\b(accept|allow|agree|got\s+it|i\s+understand|ok(ay)?)\b", re.IGNORECASE)
"""Never reached unless a policy explicitly asked for it."""

_CONSENT_CONTEXT = re.compile(
    # `cookies?` and not `cookie`: a word boundary after "cookie" does not match
    # "cookies", and every banner on the web says the plural. gov.uk's reads "We use some
    # essential cookies to make this service work", which this failed to recognise until
    # the test written from that exact sentence said so.
    r"\b(cookies?|consent|privacy|tracking|gdpr)\b",
    re.IGNORECASE,
)
"""What makes this an overlay rather than a page with an "Accept" button on it.

Matched against the page's own text, not against the button: a checkout with an
"I agree" button is not a consent banner, and pressing it would be a purchase.
"""


class ConsentPolicy(StrEnum):
    LEAVE = "leave"
    """Touch nothing. The default, and it costs runs on purpose.

    A run that fails because a banner was in the way is a visible failure with an obvious
    remedy. A run that quietly accepted tracking on the operator's behalf, on a site they
    do not own, is a thing nobody finds out about until somebody else does.
    """

    REJECT = "reject"
    """Take the least-conceding option. Recommended, and still not the default:
    recommending it is advice, and putting it in a policy is the operator saying "yes, on
    my behalf". Only they can say that."""

    ACCEPT = "accept"
    """Take the accepting option. Never inferred, never a fallback."""


def looks_like_consent(page_text: str) -> bool:
    """Whether this page is asking about cookies at all.

    Deliberately conservative: without this, a checkout's "I agree to the terms" button
    would read as a consent banner and the agent would press it. That is a purchase.
    """
    return bool(_CONSENT_CONTEXT.search(page_text))


def consent_choice(affordances: tuple[Affordance, ...], policy: ConsentPolicy) -> Affordance | None:
    """The one control this run may press, or nothing.

    Returns `None` far more often than it returns a button, and every one of those is a
    deliberate refusal rather than a gap:

    - the policy said `leave`;
    - nothing on the page is shaped like a consent choice — a banner whose buttons say
      "Sure" and "Maybe later" is one a person should look at, not one to guess at;
    - the policy said `reject` and the overlay offers no way to reject. Pressing "Accept"
      because it was the only button is exactly the failure this whole module exists to
      prevent.
    """
    if policy is ConsentPolicy.LEAVE:
        return None

    pressable = tuple(
        affordance for affordance in affordances if affordance.role in {"button", "link"}
    )

    rejecting = _first_matching(pressable, _REJECT)
    if rejecting is not None:
        return rejecting

    managing = _first_matching(pressable, _MANAGE)
    if managing is not None:
        return managing

    if policy is ConsentPolicy.ACCEPT:
        return _first_matching(pressable, _ACCEPT)

    # `reject` with nothing to reject. Silence is the answer; the run reports the overlay
    # unhandled and a person decides.
    return None


def _first_matching(
    affordances: tuple[Affordance, ...], pattern: re.Pattern[str]
) -> Affordance | None:
    for affordance in affordances:
        if pattern.search(affordance.name):
            return affordance
    return None
