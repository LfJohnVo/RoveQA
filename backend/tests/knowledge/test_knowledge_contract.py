"""The portable knowledge document against its published schema.

`contracts/knowledge-experience.schema.json` is a public, versioned contract: a graph
projection, an export and an admin API all read it. These tests check the real file,
not a copy, so drift between code and contract fails here rather than at a consumer.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from agentic_qa.application.contracts.knowledge import from_document, to_document
from agentic_qa.domain.errors import InvalidEntityError
from agentic_qa.domain.knowledge.experience import (
    CandidateKind,
    CandidateStatus,
    KnowledgeExperienceCandidate,
    Provenance,
    Quality,
    Validity,
)

NOW = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)


def contract_path() -> Path:
    """Mounted at /app/contracts in the gates container, at the repository root from a
    checkout. Searching upward beats a hard-coded depth that is right in only one."""
    for directory in Path(__file__).resolve().parents:
        candidate = directory / "contracts" / "knowledge-experience.schema.json"
        if candidate.exists():
            return candidate
    raise AssertionError("contracts/knowledge-experience.schema.json not found")


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    return Draft202012Validator(json.loads(contract_path().read_text(encoding="utf-8")))


def candidate(**overrides: Any) -> KnowledgeExperienceCandidate:
    defaults: dict[str, Any] = {
        "candidate_id": "cand-1",
        "project_id": "proj-1",
        "environment_id": "staging",
        "kind": CandidateKind.ACCEPTANCE_FACT,
        "observed": True,
        "model_derived": False,
        "created_at": NOW,
        "provenance": Provenance(
            source_run_id="run-1", evidence_set_id="ev-1", source_episode_id="ep-0"
        ),
        "validity": Validity(valid_from=NOW, origin="https://app.test", role="admin"),
        "payload": {"criterion_id": "ac-1", "summary": "checkout reaches confirmation"},
        "quality": Quality(support_count=3, success_count=3, last_verified_at=NOW),
    }
    defaults.update(overrides)
    return KnowledgeExperienceCandidate(**defaults)


def test_a_candidate_validates_against_the_published_schema(
    validator: Draft202012Validator,
) -> None:
    validator.validate(to_document(candidate()))


def test_a_minimal_candidate_still_validates(validator: Draft202012Validator) -> None:
    # Absent optionals are emitted as nulls, which the schema requires as keys: a
    # consumer must be able to tell "not recorded" from "not sent".
    validator.validate(
        to_document(
            candidate(
                provenance=Provenance(source_run_id="run-1"),
                validity=Validity(valid_from=NOW),
                quality=Quality(),
            )
        )
    )


def test_a_document_round_trips_unchanged() -> None:
    original = candidate()
    restored = from_document(to_document(original))
    assert restored == original


def test_reliability_travels_with_the_counts(validator: Draft202012Validator) -> None:
    # A consumer ranks by this number, so it must ship — and it must be the one the
    # counts imply, not an independently stored value that can drift from them.
    document = to_document(
        candidate(quality=Quality(support_count=4, success_count=3, failure_count=1))
    )
    validator.validate(document)
    assert document["quality"]["reliability"] == 0.75


class TestADocumentIsAnAssertionNotAFact:
    def test_a_trusted_hypothesis_is_refused_on_import(self) -> None:
        # The one claim an attacker with write access to an export would most want to
        # make: my guess is established knowledge, act on it.
        document = to_document(candidate())
        document["model_derived"] = True
        document["observed"] = False
        document["status"] = CandidateStatus.TRUSTED.value

        with pytest.raises(InvalidEntityError):
            from_document(document)

    def test_a_candidate_without_a_source_run_is_refused(self) -> None:
        document = to_document(candidate())
        document["provenance"]["source_run_id"] = ""

        with pytest.raises(InvalidEntityError):
            from_document(document)

    def test_an_unknown_schema_version_is_refused(self) -> None:
        document = to_document(candidate())
        document["schema_version"] = "roveqa.knowledge-experience.v2"

        with pytest.raises(InvalidEntityError, match="unsupported knowledge schema_version"):
            from_document(document)

    def test_an_unknown_kind_is_refused(self) -> None:
        document = to_document(candidate())
        document["kind"] = "whatever-the-sender-invented"

        with pytest.raises(InvalidEntityError, match="unknown kind"):
            from_document(document)

    def test_a_malformed_timestamp_is_refused(self) -> None:
        document = to_document(candidate())
        document["created_at"] = "yesterday"

        with pytest.raises(InvalidEntityError, match="created_at"):
            from_document(document)
