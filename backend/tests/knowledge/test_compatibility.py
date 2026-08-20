"""Whether old knowledge applies to the run happening now.

The three-way answer is the point of these tests. A two-way one forces every deploy to
choose between replaying stale playbooks and throwing memory away, and both choices
are wrong.
"""

from datetime import UTC, datetime, timedelta

from agentic_qa.domain.knowledge.compatibility import (
    Compatibility,
    MemoryScope,
    compatibility_of,
)
from agentic_qa.domain.knowledge.experience import (
    CandidateKind,
    CandidateStatus,
    KnowledgeExperienceCandidate,
    Provenance,
    Quality,
    Validity,
)

NOW = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)


def candidate(**validity: object) -> KnowledgeExperienceCandidate:
    fields: dict[str, object] = {
        "valid_from": NOW - timedelta(days=1),
        "origin": "https://app.test",
        "role": "admin",
        "app_version": "2.1.0",
        "page_fingerprint": "fp-abc",
        "policy_id": "pol-1",
    }
    status = validity.pop("status", CandidateStatus.PROMOTED)
    fields.update(validity)
    return KnowledgeExperienceCandidate(
        candidate_id="cand-1",
        project_id="proj-1",
        environment_id="staging",
        kind=CandidateKind.PLAYBOOK,
        observed=True,
        model_derived=False,
        created_at=NOW - timedelta(days=1),
        provenance=Provenance(source_run_id="run-1"),
        validity=Validity(**fields),  # type: ignore[arg-type]
        payload={"summary": "log in through the header form"},
        status=status,  # type: ignore[arg-type]
        quality=Quality(support_count=3, success_count=3),
    )


def scope(**overrides: object) -> MemoryScope:
    fields: dict[str, object] = {
        "project_id": "proj-1",
        "environment_id": "staging",
        "origin": "https://app.test",
        "role": "admin",
        "app_version": "2.1.0",
        "page_fingerprint": "fp-abc",
        "policy_id": "pol-1",
    }
    fields.update(overrides)
    return MemoryScope(**fields)  # type: ignore[arg-type]


def test_the_same_situation_confirmed_end_to_end_is_exact() -> None:
    # The strongest thing memory can say: learned here, in precisely this situation.
    assert compatibility_of(candidate(), scope(), now=NOW) is Compatibility.EXACT


def test_knowledge_recorded_with_less_context_is_compatible_but_not_exact() -> None:
    # Nothing mismatched, but it was not learned in this situation specifically —
    # which is what stops a vague memory outranking a precise one on reliability alone.
    vague = candidate(page_fingerprint=None)
    assert compatibility_of(vague, scope(), now=NOW) is Compatibility.COMPATIBLE


class TestADifferentSituationIsNotWeakerEvidence:
    def test_another_project_is_incompatible(self) -> None:
        assert (
            compatibility_of(candidate(), scope(project_id="proj-2"), now=NOW)
            is Compatibility.INCOMPATIBLE
        )

    def test_another_environment_is_incompatible(self) -> None:
        assert (
            compatibility_of(candidate(), scope(environment_id="production"), now=NOW)
            is Compatibility.INCOMPATIBLE
        )

    def test_another_origin_is_incompatible(self) -> None:
        # An origin is not a version of the app, it is a different app.
        assert (
            compatibility_of(candidate(), scope(origin="https://other.test"), now=NOW)
            is Compatibility.INCOMPATIBLE
        )

    def test_another_role_is_incompatible(self) -> None:
        # What an admin can do says nothing about what a guest can do.
        assert (
            compatibility_of(candidate(), scope(role="guest"), now=NOW)
            is Compatibility.INCOMPATIBLE
        )


class TestWithdrawnKnowledgeIsNeverOffered:
    def test_invalidated_is_incompatible(self) -> None:
        assert (
            compatibility_of(candidate(status=CandidateStatus.INVALIDATED), scope(), now=NOW)
            is Compatibility.INCOMPATIBLE
        )

    def test_rejected_is_incompatible(self) -> None:
        assert (
            compatibility_of(candidate(status=CandidateStatus.REJECTED), scope(), now=NOW)
            is Compatibility.INCOMPATIBLE
        )

    def test_expired_is_incompatible(self) -> None:
        expired = candidate(valid_to=NOW - timedelta(hours=1))
        assert compatibility_of(expired, scope(), now=NOW) is Compatibility.INCOMPATIBLE


class TestTheThirdAnswer:
    def test_a_new_app_version_asks_for_revalidation_rather_than_discarding(self) -> None:
        # Throwing memory away on every deploy leaves the system permanently cold.
        assert (
            compatibility_of(candidate(), scope(app_version="2.2.0"), now=NOW)
            is Compatibility.REVALIDATE
        )

    def test_a_changed_page_fingerprint_asks_for_revalidation(self) -> None:
        assert (
            compatibility_of(candidate(), scope(page_fingerprint="fp-xyz"), now=NOW)
            is Compatibility.REVALIDATE
        )

    def test_a_different_policy_asks_for_revalidation(self) -> None:
        # A stricter policy may still forbid the actions the playbook needs; that is
        # checked by verifying preconditions, not by assuming either way.
        assert (
            compatibility_of(candidate(), scope(policy_id="pol-readonly"), now=NOW)
            is Compatibility.REVALIDATE
        )

    def test_a_run_that_cannot_confirm_the_version_must_revalidate(self) -> None:
        # Not knowing whether the context matches is exactly the case to verify.
        assert (
            compatibility_of(candidate(), scope(app_version=None), now=NOW)
            is Compatibility.REVALIDATE
        )

    def test_a_run_that_cannot_confirm_the_role_must_revalidate(self) -> None:
        assert compatibility_of(candidate(), scope(role=None), now=NOW) is Compatibility.REVALIDATE


def test_knowledge_that_was_never_context_bound_stays_compatible() -> None:
    # A candidate that recorded no version imposes no version check; demanding one
    # would make every piece of context-free knowledge permanently unusable.
    unbound = candidate(app_version=None, page_fingerprint=None, policy_id=None)
    assert (
        compatibility_of(unbound, scope(app_version="9.9.9", page_fingerprint="fp-new"), now=NOW)
        is Compatibility.COMPATIBLE
    )
