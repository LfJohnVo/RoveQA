"""A criterion's literal against what the browser actually renders.

Found against a real site. The criterion asked for `Mission Control` — the words in the
markup, in the `<title>`, and everywhere a person would copy them from. The page styles
its heading `text-transform: uppercase`, so the browser reports the text as
`THE MISSION CONTROL FOR YOUR IT`, and a substring check missed it.

What makes this worth its own module is the consequence, not the inconvenience. A failed
deterministic check reports `FailureKind.PRODUCT`, and `PRODUCT` is the only kind that
produces `failed`. So a stylesheet was one completed run away from making RoveQA accuse
an application of not saying something it said.
"""

import pytest

from agentic_qa.domain.qa.text_match import TextMatch, describe_match, find_text


class TestWhatCountsAsThePageSayingIt:
    def test_the_literal_as_written_is_an_exact_match(self) -> None:
        assert find_text("Mission Control", "The Mission Control for IT") is TextMatch.EXACT

    def test_a_heading_the_stylesheet_uppercased_still_counts(self) -> None:
        # The measured case, verbatim.
        rendered = "AITOPS®\nSERVICES\nIT MISSION CONTROL\nTHE MISSION CONTROL FOR YOUR IT"

        assert find_text("Mission Control", rendered) is TextMatch.NORMALIZED

    def test_a_line_break_the_viewport_chose_still_counts(self) -> None:
        # Where a heading wraps is decided by the width of the window, which the person
        # writing the criterion cannot see.
        assert find_text("Mission Control for Your IT", "MISSION CONTROL\nFOR YOUR IT") is (
            TextMatch.NORMALIZED
        )

    def test_absent_text_is_still_absent(self) -> None:
        # The fix must not turn the check into one that passes on anything.
        assert find_text("Mission Control", "AITops, services and industries") is None

    def test_an_empty_literal_is_not_a_match(self) -> None:
        # An empty string is inside every page, so treating it as found would report a
        # criterion satisfied by a check nobody performed.
        assert find_text("", "anything at all") is None

    @pytest.mark.parametrize(
        ("expected", "visible"),
        [
            ("Operación", "OPERACION AUTONOMA"),  # accents are content
            ("Mission Control", "Mission-Control"),  # punctuation is content
            ("Mission Control", "Control Mission"),  # word order is content
        ],
    )
    def test_only_rendering_is_discounted_never_content(self, expected: str, visible: str) -> None:
        assert find_text(expected, visible) is None

    def test_accents_survive_the_fold(self) -> None:
        # Case folding must not become accent stripping: `Operación` and `Operacion` are
        # different words, and one of them is a typo worth reporting.
        assert find_text("Operación", "OPERACIÓN AUTÓNOMA") is TextMatch.NORMALIZED


class TestTheObservationSaysWhichComparisonAnswered:
    def test_an_exact_match_claims_exactly_that(self) -> None:
        assert describe_match("Mission Control", TextMatch.EXACT) == (
            "the page contains 'Mission Control'"
        )

    def test_a_normalized_match_admits_it(self) -> None:
        # A weaker match presented as an exact one is how a report stops being readable:
        # the reader has no way to tell which results to check by hand.
        said = describe_match("Mission Control", TextMatch.NORMALIZED)

        assert "ignoring case" in said
        assert "Mission Control" in said
