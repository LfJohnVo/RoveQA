"""Origin allowlist semantics.

Ambiguous matching is how allowlists get bypassed, so the rules are exact and tested:
RFC 6454 origins only, no implicit subdomains, no path prefixes, scheme-sensitive
(docs/13).
"""

import pytest

from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.domain.projects.run_policy import RunPolicy, normalize_origin


def policy(*origins: str) -> RunPolicy:
    return RunPolicy(
        policy_id="pol-1",
        project_id="p-1",
        allowed_origins=origins or ("https://app.example.com",),
        max_duration_seconds=600,
        max_actions=100,
        max_model_calls=10,
    )


class TestNormalizeOrigin:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("https://app.example.com", "https://app.example.com"),
            ("https://APP.Example.COM", "https://app.example.com"),
            ("http://localhost:3000", "http://localhost:3000"),
            ("https://app.example.com/", "https://app.example.com"),
        ],
    )
    def test_accepts_and_normalizes_origins(self, raw: str, expected: str) -> None:
        assert normalize_origin(raw) == expected

    @pytest.mark.parametrize(
        "raw",
        [
            "https://app.example.com/admin",  # path
            "https://app.example.com?x=1",  # query
            "ftp://files.example.com",  # scheme
            "file:///etc/passwd",
            "app.example.com",  # no scheme
            "https://",  # no host
            "https://user:pw@app.example.com",  # credentials
        ],
    )
    def test_rejects_anything_that_is_not_a_bare_origin(self, raw: str) -> None:
        with pytest.raises(InvalidEntityError):
            normalize_origin(raw)


class TestAllowsOrigin:
    def test_allows_an_exact_origin(self) -> None:
        assert policy().allows_origin("https://app.example.com/checkout?step=2") is True

    def test_rejects_a_subdomain(self) -> None:
        """No implicit subdomains: evil.app.example.com is a different origin."""
        assert policy().allows_origin("https://evil.app.example.com/") is False

    def test_rejects_a_different_scheme(self) -> None:
        assert policy().allows_origin("http://app.example.com/") is False

    def test_rejects_a_different_port(self) -> None:
        assert policy("http://localhost:3000").allows_origin("http://localhost:9999/") is False

    def test_rejects_a_lookalike_host(self) -> None:
        assert policy().allows_origin("https://app.example.com.evil.test/") is False

    def test_rejects_garbage(self) -> None:
        assert policy().allows_origin("not a url") is False
        assert policy().allows_origin("") is False


class TestPolicyInvariants:
    def test_requires_at_least_one_origin(self) -> None:
        """There is no safe empty allowlist, so there is no default."""
        with pytest.raises(InvalidEntityError):
            policy_without_origins = RunPolicy(
                policy_id="pol-1",
                project_id="p-1",
                allowed_origins=(),
                max_duration_seconds=600,
                max_actions=100,
                max_model_calls=10,
            )
            assert policy_without_origins is None

    @pytest.mark.parametrize(
        ("duration", "actions", "model_calls"),
        [(0, 100, 10), (600, 0, 10), (600, 100, -1)],
    )
    def test_rejects_unbounded_budgets(self, duration: int, actions: int, model_calls: int) -> None:
        with pytest.raises(InvalidEntityError):
            RunPolicy(
                policy_id="pol-1",
                project_id="p-1",
                allowed_origins=("https://app.example.com",),
                max_duration_seconds=duration,
                max_actions=actions,
                max_model_calls=model_calls,
            )
