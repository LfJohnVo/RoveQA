"""What memory is allowed to tell a planner, and in what order.

Order is behaviour here: the first items are the ones the agent acts on. So these
tests care as much about what is excluded and how ties break as about scoring.
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from agentic_qa.application.contracts.memory import to_document
from agentic_qa.domain.knowledge.compatibility import Compatibility, MemoryScope
from agentic_qa.domain.knowledge.experience import (
    CandidateKind,
    CandidateStatus,
    KnowledgeExperienceCandidate,
    Provenance,
    Quality,
    Validity,
)
from agentic_qa.domain.knowledge.memory_context import (
    MAX_CONTEXT_ITEMS,
    freshness_at,
    select,
)

NOW = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)


def contract_path() -> Path:
    for directory in Path(__file__).resolve().parents:
        candidate = directory / "contracts" / "memory-context.schema.json"
        if candidate.exists():
            return candidate
    raise AssertionError("contracts/memory-context.schema.json not found")


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    """The published schema, not a copy: drift shows up here, not at a consumer."""
    return Draft202012Validator(json.loads(contract_path().read_text(encoding="utf-8")))


def candidate(candidate_id: str = "cand-1", **overrides: Any) -> KnowledgeExperienceCandidate:
    validity_fields: dict[str, Any] = {
        "valid_from": NOW - timedelta(days=1),
        "origin": "https://app.test",
        "role": "admin",
        "app_version": "2.1.0",
        "page_fingerprint": "fp-abc",
        "policy_id": "pol-1",
    }
    validity_fields.update(overrides.pop("validity", {}))
    defaults: dict[str, Any] = {
        "project_id": "proj-1",
        "environment_id": "staging",
        "kind": CandidateKind.PLAYBOOK,
        "observed": True,
        "model_derived": False,
        "created_at": NOW - timedelta(days=1),
        "provenance": Provenance(source_run_id="run-1", evidence_set_id="ev-1"),
        "payload": {"summary": f"reach checkout via {candidate_id}"},
        "status": CandidateStatus.PROMOTED,
        "quality": Quality(support_count=3, success_count=3, last_verified_at=NOW),
    }
    defaults.update(overrides)
    return KnowledgeExperienceCandidate(
        candidate_id=candidate_id, validity=Validity(**validity_fields), **defaults
    )


def scope(**overrides: Any) -> MemoryScope:
    fields: dict[str, Any] = {
        "project_id": "proj-1",
        "environment_id": "staging",
        "origin": "https://app.test",
        "role": "admin",
        "app_version": "2.1.0",
        "page_fingerprint": "fp-abc",
        "policy_id": "pol-1",
    }
    fields.update(overrides)
    return MemoryScope(**fields)


class TestOnlyActionableKnowledgeIsOffered:
    def test_an_unpromoted_candidate_is_not_offered(self) -> None:
        # One run's observation is not advice. History in a prompt reads as advice.
        context = select(
            [candidate(status=CandidateStatus.CANDIDATE)], scope=scope(), query_id="q", now=NOW
        )
        assert context.is_cold

    def test_invalidated_knowledge_is_not_offered(self) -> None:
        context = select(
            [candidate(status=CandidateStatus.INVALIDATED)], scope=scope(), query_id="q", now=NOW
        )
        assert context.is_cold

    def test_rejected_knowledge_is_not_offered(self) -> None:
        context = select(
            [candidate(status=CandidateStatus.REJECTED)], scope=scope(), query_id="q", now=NOW
        )
        assert context.is_cold

    def test_another_project_is_dropped_even_if_it_was_handed_in(self) -> None:
        # The last gate: retrieval filters scope in SQL, but graph traversal and
        # rebuild paths converge here too, and one missing filter is a leak.
        foreign = candidate(project_id="proj-2")
        context = select([foreign], scope=scope(), query_id="q", now=NOW)
        assert context.is_cold


class TestOrderIsBehaviour:
    def test_knowledge_learned_in_this_exact_situation_outranks_vaguer_knowledge(self) -> None:
        exact = candidate("cand-exact")
        vague = candidate("cand-vague", validity={"page_fingerprint": None, "app_version": None})

        context = select([vague, exact], scope=scope(), query_id="q", now=NOW)

        assert [item.candidate_id for item in context.items] == ["cand-exact", "cand-vague"]
        assert context.items[0].compatibility is Compatibility.EXACT
        assert context.items[1].compatibility is Compatibility.COMPATIBLE

    def test_something_needing_revalidation_ranks_below_something_that_does_not(self) -> None:
        settled = candidate("cand-settled")
        needs_check = candidate("cand-stale-version", validity={"app_version": "1.0.0"})

        context = select([needs_check, settled], scope=scope(), query_id="q", now=NOW)

        assert [item.candidate_id for item in context.items] == [
            "cand-settled",
            "cand-stale-version",
        ]
        assert context.items[1].requires_revalidation

    def test_an_observation_outranks_a_hypothesis_of_equal_reliability(self) -> None:
        observed = candidate("cand-observed")
        guessed = candidate("cand-guessed", observed=False, model_derived=True)

        context = select([guessed, observed], scope=scope(), query_id="q", now=NOW)

        assert [item.candidate_id for item in context.items] == ["cand-observed", "cand-guessed"]
        # Both offered, both labelled: the planner is told which is which regardless.
        assert context.items[1].model_derived

    def test_recently_verified_knowledge_outranks_the_same_thing_verified_long_ago(self) -> None:
        recent = candidate(
            "cand-recent", quality=Quality(support_count=3, success_count=3, last_verified_at=NOW)
        )
        old = candidate(
            "cand-old",
            quality=Quality(
                support_count=3, success_count=3, last_verified_at=NOW - timedelta(days=180)
            ),
        )

        context = select([old, recent], scope=scope(), query_id="q", now=NOW)
        assert [item.candidate_id for item in context.items] == ["cand-recent", "cand-old"]

    def test_the_same_inputs_always_produce_the_same_order(self) -> None:
        # A warm-vs-cold benchmark must measure memory, not dictionary ordering.
        twins = [candidate("cand-b"), candidate("cand-a")]
        first = select(twins, scope=scope(), query_id="q", now=NOW)
        second = select(list(reversed(twins)), scope=scope(), query_id="q", now=NOW)
        assert [item.candidate_id for item in first.items] == [
            item.candidate_id for item in second.items
        ]


class TestTheContextIsBounded:
    def test_it_is_cut_to_the_requested_size(self) -> None:
        many = [candidate(f"cand-{index:02d}") for index in range(30)]
        context = select(many, scope=scope(), query_id="q", now=NOW, limit=3)
        assert len(context.items) == 3

    def test_a_caller_cannot_ask_for_more_than_the_contract_allows(self) -> None:
        # Memory that fills the context window has spent the budget it was saving.
        many = [candidate(f"cand-{index:03d}") for index in range(120)]
        context = select(many, scope=scope(), query_id="q", now=NOW, limit=1000)
        assert len(context.items) == MAX_CONTEXT_ITEMS


class TestEveryItemCanBeWeighedRatherThanBelieved:
    def test_each_item_carries_provenance_reliability_and_a_reason(self) -> None:
        context = select([candidate()], scope=scope(), query_id="q", now=NOW)
        item = context.items[0]

        assert item.source_run_id == "run-1"
        assert item.evidence_set_id == "ev-1"
        assert item.reliability == 1.0
        assert "observed" in item.selection_reason
        assert "3 support" in item.selection_reason

    def test_an_item_needing_revalidation_says_so_in_its_reason(self) -> None:
        context = select(
            [candidate(validity={"app_version": "1.0.0"})], scope=scope(), query_id="q", now=NOW
        )
        assert "preconditions must be verified" in context.items[0].selection_reason


class TestFreshness:
    def test_never_verified_is_zero(self) -> None:
        assert freshness_at(NOW, last_verified_at=None) == 0.0

    def test_just_verified_is_one(self) -> None:
        assert freshness_at(NOW, last_verified_at=NOW) == 1.0

    def test_it_halves_over_the_half_life(self) -> None:
        assert freshness_at(NOW, last_verified_at=NOW - timedelta(days=30)) == pytest.approx(
            0.5, abs=1e-4
        )

    def test_age_lowers_priority_but_never_removes_a_reliable_item(self) -> None:
        # An old fact is not wrong, only less recently checked — so decay must not be
        # able to score it out of existence on its own.
        ancient = candidate(
            "cand-ancient",
            quality=Quality(
                support_count=9, success_count=9, last_verified_at=NOW - timedelta(days=3650)
            ),
        )
        context = select([ancient], scope=scope(), query_id="q", now=NOW)

        assert context.items[0].freshness == 0.0
        assert context.items[0].score > 0.0


class TestTheDocument:
    def test_a_context_validates_against_the_published_schema(
        self, validator: Draft202012Validator
    ) -> None:
        context = select(
            [candidate("cand-1"), candidate("cand-2", observed=False, model_derived=True)],
            scope=scope(),
            query_id="q-1",
            now=NOW,
        )
        validator.validate(to_document(context))

    def test_an_empty_context_is_a_valid_document(self, validator: Draft202012Validator) -> None:
        # A cold run must still produce a well-formed answer, not an absent one.
        validator.validate(to_document(select([], scope=scope(), query_id="q-1", now=NOW)))

    def test_the_hypothesis_label_survives_serialization(
        self, validator: Draft202012Validator
    ) -> None:
        context = select(
            [candidate("cand-1", observed=False, model_derived=True)],
            scope=scope(),
            query_id="q-1",
            now=NOW,
        )
        document = to_document(context)
        validator.validate(document)

        item = document["items"][0]
        assert item["model_derived"] is True
        assert item["observed"] is False
        # And it can still be traced back to the run that produced it.
        assert item["provenance"]["source_run_id"] == "run-1"
