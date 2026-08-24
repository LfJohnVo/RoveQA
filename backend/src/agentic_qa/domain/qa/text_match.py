"""Whether a page says a thing, when "says" has to survive CSS.

Found against a real corporate site. A criterion asked for `Mission Control` — the words
in the markup, in the `<title>`, and in every place a person would copy them from. The
page renders the heading through `text-transform: uppercase`, so what the browser reports
as its text is `THE MISSION CONTROL FOR YOUR IT`, and a substring check missed it.

The consequence is the one this project cares about most. A deterministic check that fails
reports `FailureKind.PRODUCT`, and `PRODUCT` is the only kind that produces `failed` — an
accusation against an application whose page said exactly what it was asked to say. One
false accusation makes every later report suspect (docs/00).

So the comparison happens twice, and the second attempt is *reported* rather than silently
substituted:

- **Exact** first, always. When the literal is there as written, that is what is said.
- **Normalized** second — case folded, runs of whitespace collapsed. Case is chosen by a
  stylesheet at render time and line breaks by the viewport, and the person writing the
  criterion can see neither. Both are properties of the rendering, not of the content.

Nothing else is normalized. Accents stay, punctuation stays, and word order stays: those
are content, and a match that ignored them would be a different claim wearing this one's
name.
"""

from enum import StrEnum


class TextMatch(StrEnum):
    EXACT = "exact"
    NORMALIZED = "normalized"
    """Matched only after folding case and collapsing whitespace.

    Carried out of the function rather than folded into a boolean so the observation can
    say so. A reader deciding whether to trust a result needs to know the page did not
    literally contain what was asked for — it contained the same words, rendered
    differently.
    """


def find_text(expected: str, visible: str) -> TextMatch | None:
    """How `expected` appears in `visible`, or None if it does not.

    Deliberately not a bool. "Found" and "found once the stylesheet is discounted" are
    different facts, and a caller that could not tell them apart would have to pick one
    story to tell about both.
    """
    if not expected:
        # An empty literal is in everything, which is not a check. The caller decides
        # what to do about a criterion with nothing to look for; it is not a match.
        return None
    if expected in visible:
        return TextMatch.EXACT
    if _flattened(expected) in _flattened(visible):
        return TextMatch.NORMALIZED
    return None


def describe_match(expected: str, match: TextMatch) -> str:
    """The observation line, which has to be honest about which comparison answered."""
    if match is TextMatch.EXACT:
        return f"the page contains {expected!r}"
    return (
        f"the page contains {expected!r}, ignoring case and line breaks "
        "(the page renders it differently)"
    )


def _flattened(text: str) -> str:
    """Case folded, runs of whitespace collapsed to one space.

    `casefold` rather than `lower`: it is the comparison Unicode defines for this, and it
    handles the pairs `lower` gets wrong. `split()` with no argument collapses every kind
    of whitespace, which is what a rendered line break arrives as.
    """
    return " ".join(text.split()).casefold()
