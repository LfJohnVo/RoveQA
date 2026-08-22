"""The durable log reconstructs a run, and cannot leak a credential doing it.

Twenty-five actions used to leave three events — `run.created` and two status changes —
so an operator diagnosing a stuck run had the verdict and a screenshot. One event per
action fixed that, and the event carries the one thing that makes a trace worth reading:
what the agent asked for, and what came back.

The second property is the delicate one. A `fill` carries what was typed, and what was
typed is the one part of an action that can be a password. This is not solved by
redacting it well; it is solved by the value never entering the record.
"""

from dataclasses import fields

from agentic_qa.application.ports.episodes import ActionRecord
from agentic_qa.domain.browser.urls import safe_url
from agentic_qa.domain.knowledge.redaction import REDACTED, redact_secrets

SECRET = "sk-live-9f2b41c7d8e6a5b3"


class TestATypedValueCannotBePublished:
    def test_the_record_has_nowhere_to_put_one(self) -> None:
        # Structural, not procedural. A redaction can be forgotten at one call site; a
        # field that does not exist cannot be published from any of them. If someone adds
        # `value` here, this test is the conversation about whether it may be logged.
        assert {field.name for field in fields(ActionRecord)} == {
            "index",
            "action",
            "intent",
            "succeeded",
            "url",
            "http_status",
            "detail",
        }

    def test_the_url_loses_its_query_string(self) -> None:
        # Where a token actually rides, and this url comes from a page nobody here
        # controls. The activity runs every action url through this before publishing.
        cleaned = safe_url(f"https://app.test/reset?session_token={SECRET}")

        assert SECRET not in cleaned
        assert cleaned.startswith("https://app.test/reset")

    def test_the_browser_s_own_sentence_is_cleaned_before_it_is_published(self) -> None:
        # `detail` is whatever Playwright said, and Playwright quotes what it was given.
        detail = f"Locator.fill: value '{SECRET}' rejected by the page"

        cleaned = redact_secrets(detail)

        assert SECRET not in cleaned
        assert REDACTED in cleaned
        # And the sentence survives, because the sentence is usually the whole diagnosis.
        assert "Locator.fill" in cleaned
