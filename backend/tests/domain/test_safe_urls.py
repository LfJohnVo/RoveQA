"""Which parts of a URL are safe to keep.

The rule this function encodes: a URL to *act on* keeps everything, because
`/records?status=open` is a different page from `/records`; a URL to *keep* is stripped,
because a state map is compared night after night and an observation travels into a
prompt. Applications put session tokens in query strings, and a token stored in a table
nobody thinks of as holding credentials outlives the session that issued it.
"""

import pytest

from agentic_qa.domain.browser.urls import safe_url


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://app.test/records", "https://app.test/records"),
        ("https://app.test/records?session_token=sk-live-1", "https://app.test/records"),
        ("https://app.test/records#section", "https://app.test/records"),
        ("https://app.test:8443/records?a=1#b", "https://app.test:8443/records"),
        ("https://app.test/", "https://app.test/"),
        ("HTTPS://APP.TEST/Records", "https://app.test/Records"),
    ],
)
def test_it_keeps_where_and_drops_what_rides_along(raw: str, expected: str) -> None:
    assert safe_url(raw) == expected


def test_credentials_in_the_authority_are_dropped() -> None:
    # `user:password@host` is a credential in the URL itself, and one that a naive
    # "strip the query" would keep.
    assert safe_url("https://qa:hunter2@app.test/admin") == "https://app.test/admin"


def test_a_reset_link_keeps_nothing_of_its_token() -> None:
    cleaned = safe_url("https://app.test/reset?token=abc123&user=qa@example.test")

    assert cleaned == "https://app.test/reset"
    assert "abc123" not in cleaned
    assert "qa@example.test" not in cleaned


def test_something_that_is_not_a_url_is_left_alone_when_it_is_harmless() -> None:
    assert safe_url("about:blank") == "about:blank"
    assert safe_url("") == ""


def test_something_unparseable_that_could_hide_a_secret_comes_back_empty() -> None:
    # Half-sanitised is the worst of both: it looks cleaned and is not.
    assert safe_url("not a url?token=abc123") == ""
    assert safe_url("garbage://qa:hunter2@") == ""
