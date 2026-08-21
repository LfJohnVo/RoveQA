"""Reading affordances out of an ARIA snapshot.

The parsing is a pure function and is tested as one. Whether Playwright still produces
the format it parses is a question only real Chromium can answer, and lives in
`tests/browser/test_page_description.py` — because the failure mode of a stale parser is
not an exception, it is "this page offers nothing", which an explorer reads as a dead
end and a report reads as an application that lost every control it had.
"""

from agentic_qa.domain.exploration.state import MAX_AFFORDANCES
from agentic_qa.infrastructure.browser.playwright.affordances import (
    MAX_SNAPSHOT_LINES,
    parse_affordances,
    parse_text_content,
)

SNAPSHOT = """
- banner:
  - link "Home":
    - /url: /
  - heading "Records" [level=1]
- main:
  - button "New record"
  - textbox "Search"
  - list:
    - listitem:
      - link "Order 8821"
    - listitem:
      - link "Order 9007"
- contentinfo:
  - paragraph: Copyright 2026
"""


class TestParsing:
    def test_it_finds_what_a_user_can_do(self) -> None:
        found = parse_affordances(SNAPSHOT)

        assert {(item.role, item.name) for item in found} >= {
            ("link", "Home"),
            ("button", "New record"),
            ("textbox", "Search"),
        }

    def test_structure_is_not_an_affordance(self) -> None:
        # Headings, banners and paragraphs describe how a page is arranged. Including
        # them would make a reflowed layout look like a new state while telling an
        # explorer nothing it can act on.
        roles = {item.role for item in parse_affordances(SNAPSHOT)}

        assert roles.isdisjoint({"heading", "banner", "main", "list", "listitem", "paragraph"})

    def test_a_thousand_rows_collapse_to_what_they_offer(self) -> None:
        # The whole point: two order links differing only by number are one affordance.
        links = [item for item in parse_affordances(SNAPSHOT) if item.name.startswith("Order")]

        assert len(links) == 1

    def test_a_nameless_control_is_dropped(self) -> None:
        # A button nobody can name is a target nothing can ask for, and putting it in
        # the frontier would queue an action that can never be performed.
        assert parse_affordances('- button\n- button ""\n- link "Real"') == (
            *(item for item in parse_affordances('- link "Real"')),
        )

    def test_an_empty_snapshot_offers_nothing(self) -> None:
        assert parse_affordances("") == ()

    def test_prose_that_looks_like_a_snapshot_is_ignored(self) -> None:
        # Page text is untrusted data. A page claiming to contain a snapshot does not
        # get to add affordances that are not there — though anything it did smuggle in
        # would still be an ordinary action the policy gates.
        assert parse_affordances("the page said: - button 'not real'") == ()

    def test_it_is_bounded(self) -> None:
        huge = "\n".join(f'- link "unique thing {index}"' for index in range(MAX_AFFORDANCES * 3))

        assert len(parse_affordances(huge)) <= MAX_AFFORDANCES

    def test_it_stops_reading_a_pathological_snapshot(self) -> None:
        # A data grid can produce tens of thousands of nodes. Reading all of them would
        # make one observation cost more than the action that follows it.
        padding = "\n".join("- paragraph: filler" for _ in range(MAX_SNAPSHOT_LINES + 10))

        assert parse_affordances(f'{padding}\n- button "Too late"') == ()


class TestResolvingLinkDestinations:
    def test_a_relative_href_is_resolved_against_the_page(self) -> None:
        # Unresolved, `/records` has no origin at all, and an allowlist asked about it
        # can only refuse — which would stop every exploration at the front door.
        found = parse_affordances(
            '- link "Records":\n  - /url: /records', base_url="https://app.test/home"
        )

        assert found[0].url == "https://app.test/records"

    def test_an_absolute_href_is_left_alone(self) -> None:
        found = parse_affordances(
            '- link "Docs":\n  - /url: https://docs.test/start', base_url="https://app.test/"
        )

        assert found[0].url == "https://docs.test/start"

    def test_a_scheme_nobody_vetted_is_declined(self) -> None:
        # Left as a click, which the RunPolicy gates like any other state change,
        # rather than handed to a navigation.
        for href in ("javascript:alert(1)", "mailto:someone@example.test", "tel:+15551234"):
            found = parse_affordances(
                f'- link "Odd":\n  - /url: {href}', base_url="https://app.test/"
            )
            assert found[0].url is None, href

    def test_a_fragment_stays_on_the_same_page(self) -> None:
        found = parse_affordances(
            '- link "Skip to content":\n  - /url: #main', base_url="https://app.test/home"
        )

        assert found[0].url == "https://app.test/home#main"

    def test_a_url_line_belonging_to_something_else_is_not_borrowed(self) -> None:
        # Indentation is what says "this url is that link's". A line at the same level
        # is a sibling, and attaching it would point one affordance at another's page.
        found = parse_affordances('- link "First"\n- /url: /second', base_url="https://app.test/")

        assert found[0].url is None


class TestQuotedValues:
    """Playwright quotes a value that would otherwise read as syntax.

    Keeping the quotes turned every anchor link into a path no browser can open. Three
    of forty-one affordances on a real marketing page came out this way, and all three
    were the in-page navigation.
    """

    def test_an_anchor_href_resolves_to_a_navigable_url(self) -> None:
        found = parse_affordances(
            '- link "Contact":\n  - /url: "#contact"', base_url="https://app.test/home"
        )

        assert found[0].url == "https://app.test/home#contact"

    def test_a_bare_fragment_stays_on_the_page(self) -> None:
        found = parse_affordances(
            '- link "Services":\n  - /url: "#"', base_url="https://app.test/home"
        )

        assert found[0].url is not None
        assert '"' not in found[0].url

    def test_a_quoted_text_node_loses_its_quotes(self) -> None:
        # A criterion looking for `@2026 Acme` must match. A deterministic criterion
        # that fails is the one verdict that accuses the product.
        assert parse_text_content('- text: "@2026 Acme - All rights reserved"') == (
            "@2026 Acme - All rights reserved",
        )


class TestDisabledControls:
    def test_a_disabled_control_says_so(self) -> None:
        found = parse_affordances('- button "Sign in" [disabled]')

        assert found[0].disabled is True

    def test_an_enabled_control_is_the_default(self) -> None:
        found = parse_affordances('- button "Sign in"')

        assert found[0].disabled is False

    def test_a_disabled_control_is_not_takeable(self) -> None:
        # The frontier must not spend an action on something the page already refused.
        found = parse_affordances('- button "Sign in" [disabled]')

        assert found[0].is_clickable is False

    def test_attaching_a_url_does_not_re_enable_it(self) -> None:
        found = parse_affordances(
            '- link "Checkout" [disabled]:\n  - /url: /checkout', base_url="https://app.test/"
        )

        assert found[0].url == "https://app.test/checkout"
        assert found[0].disabled is True

    def test_other_attributes_do_not_disable_anything(self) -> None:
        found = parse_affordances('- checkbox "Remember me" [checked]')

        assert found[0].disabled is False

    def test_the_state_stays_out_of_the_key(self) -> None:
        # `key` feeds `state_signature`. Putting a transient state in it would give
        # every stored baseline and memory fingerprint a new meaning overnight, and
        # nothing would fail to say so. A control that greys out is the same control.
        enabled = parse_affordances('- button "Sign in"')[0]
        disabled = parse_affordances('- button "Sign in" [disabled]')[0]

        assert enabled.key == disabled.key


class TestPageText:
    """What the page says, which used to be discarded by the method that captured it."""

    def test_it_reads_headings_paragraphs_and_text(self) -> None:
        assert parse_text_content(SNAPSHOT) == ("Records", "Copyright 2026")

    def test_a_control_name_is_not_page_text(self) -> None:
        # The two readings answer different questions and stay in separate sections.
        assert "New record" not in parse_text_content(SNAPSHOT)

    def test_empty_nodes_are_layout_not_content(self) -> None:
        assert parse_text_content("- paragraph:\n- text: \n- paragraph: Real") == ("Real",)

    def test_repetition_is_collapsed(self) -> None:
        assert parse_text_content("- paragraph: Same\n- paragraph: Same") == ("Same",)

    def test_it_is_bounded_by_characters(self) -> None:
        snapshot = "\n".join(f"- paragraph: line number {index}" for index in range(500))

        content = parse_text_content(snapshot, max_chars=100)

        assert sum(len(line) for line in content) <= 100 + len("… [truncated]")

    def test_truncation_is_marked(self) -> None:
        # A planner told a partial page is complete concludes the page lacks what it
        # was looking for.
        snapshot = "\n".join(f"- paragraph: line number {index}" for index in range(500))

        assert parse_text_content(snapshot, max_chars=50)[-1] == "… [truncated]"

    def test_an_empty_snapshot_says_nothing(self) -> None:
        assert parse_text_content("") == ()
