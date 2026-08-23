"""What a token is, and what it must never be (ADR 0020).

The properties here are the ones an audit would ask about, so they are asserted rather
than argued: the value is unguessable, it is never in the record, two mints never collide,
and the comparison does not leak its prefix through timing.
"""

from datetime import UTC, datetime

import pytest

from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.domain.projects.api_token import (
    TOKEN_ENTROPY_BYTES,
    TOKEN_PREFIX,
    ApiToken,
    fingerprint,
    issue,
    matches,
    mint_secret,
)

NOW = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)


class TestTheValue:
    def test_it_carries_a_prefix_a_scanner_can_find(self) -> None:
        # A leaked token should be findable in a log that should not have had it, and
        # matchable by the secret scanning most forges run.
        assert mint_secret().startswith(TOKEN_PREFIX)

    def test_it_has_the_entropy_that_makes_a_fast_hash_correct(self) -> None:
        # The whole argument for SHA-256 over a password KDF rests on this number, so it
        # is checked rather than assumed. base64url of N bytes is ceil(4N/3) characters.
        body = mint_secret().removeprefix(TOKEN_PREFIX)

        assert len(body) >= (TOKEN_ENTROPY_BYTES * 4) // 3

    def test_two_mints_never_collide(self) -> None:
        minted = {mint_secret() for _ in range(500)}

        assert len(minted) == 500

    def test_the_fingerprint_is_not_the_value(self) -> None:
        secret = mint_secret()

        assert secret not in fingerprint(secret)

    def test_the_same_value_always_fingerprints_the_same(self) -> None:
        # Otherwise a token could not be looked up by its hash, which is the whole
        # storage design.
        secret = mint_secret()

        assert fingerprint(secret) == fingerprint(secret)

    def test_a_wrong_value_does_not_match(self) -> None:
        assert not matches(mint_secret(), fingerprint(mint_secret()))

    def test_the_right_value_matches(self) -> None:
        secret = mint_secret()

        assert matches(secret, fingerprint(secret))


class TestTheRecord:
    def test_it_has_nowhere_to_put_the_token(self) -> None:
        # Structural, like `EnvironmentSession` and its cookie. A record that could carry
        # the value is a record something could log.
        from dataclasses import fields

        assert {field.name for field in fields(ApiToken)} == {
            "token_id",
            "project_id",
            "label",
            "fingerprint",
            "issued_at",
            "issued_by",
        }

    def test_issuing_produces_a_record_that_finds_the_value(self) -> None:
        issued = issue(token_id="tok-1", project_id="proj-1", label="ci", now=NOW)

        assert matches(issued.secret, issued.record.fingerprint)

    def test_the_issued_pair_does_not_print_the_value(self) -> None:
        # One stray `logger.debug` is all it takes, and a dataclass prints its fields.
        issued = issue(token_id="tok-1", project_id="proj-1", label="ci", now=NOW)

        assert issued.secret not in repr(issued)

    def test_a_naive_timestamp_is_refused(self) -> None:
        with pytest.raises(InvalidEntityError, match="timezone-aware"):
            ApiToken(
                token_id="tok-1",
                project_id="proj-1",
                label="ci",
                fingerprint="abc",
                issued_at=datetime(2026, 8, 23, 12, 0),  # noqa: DTZ001 - the point
            )


class TestWhatATokenReaches:
    def test_it_covers_its_own_project(self) -> None:
        issued = issue(token_id="tok-1", project_id="proj-1", label="ci", now=NOW)

        assert issued.record.covers("proj-1")

    def test_it_covers_nothing_else(self) -> None:
        # The property the whole phase exists for: the CI of one repository cannot reach
        # another team's application.
        issued = issue(token_id="tok-1", project_id="proj-1", label="ci", now=NOW)

        assert not issued.record.covers("proj-2")

    def test_an_empty_project_is_not_a_wildcard(self) -> None:
        # A blank comparing equal to a blank would turn a malformed row into a key to
        # everything, which is exactly the super-credential this design does not have.
        issued = issue(token_id="tok-1", project_id="proj-1", label="ci", now=NOW)

        assert not issued.record.covers("")
