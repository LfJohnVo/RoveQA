"""The run-boundary pass: group, ask, store — and survive being interrupted.

Parametrized over the in-memory double and PostgreSQL, because the properties being
checked are the ones a double is most likely to fake: that a cluster accumulates
members instead of duplicating, that a hypothesis lands in its own row without touching
the evidence, and that a retried pass writes nothing and asks nothing.

The two Phase 11 durability gates live here. A pass that is retried must not re-spend
minutes of deep inference or leave a second answer, and one that dies partway must
leave the deterministic grouping behind — that half is useful on its own.
"""

from collections.abc import Callable
from datetime import UTC, datetime

import pytest

from agentic_qa.application.commands.analyze_failures import (
    AnalyzeFailuresCommand,
    analyze_failures,
)
from agentic_qa.application.errors import NotFoundError
from agentic_qa.application.ports.deep_analysis import (
    ClusterAnalysisRequest,
    ClusterHypothesis,
    HypothesisConfidence,
)
from agentic_qa.application.ports.idempotency import FAILURE_ANALYSIS_SCOPE
from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.domain.qa.verification import CriterionOutcome, CriterionResult, FailureKind
from agentic_qa.domain.runs.run import Run, RunStatus, Verdict
from tests.conftest import seed_project_with_default_policy

NOW = datetime(2026, 8, 20, 9, 0, tzinfo=UTC)
LATER = datetime(2026, 8, 20, 10, 0, tzinfo=UTC)

Factory = Callable[[], UnitOfWork]


class CountingAnalyst:
    """A deep analyst that answers instantly and counts how often it was consulted.

    The count is the point of several tests below: deep inference is the expensive part,
    and "was it asked again" is the question a retry has to answer with no.
    """

    def __init__(self, *, fails: bool = False) -> None:
        self.calls = 0
        self._fails = fails

    async def analyze(self, request: ClusterAnalysisRequest) -> ClusterHypothesis:
        self.calls += 1
        if self._fails:
            return ClusterHypothesis(cluster_id=request.cluster_id, failure="deep model down")
        return ClusterHypothesis(
            cluster_id=request.cluster_id,
            probable_cause="the payment service rejects the order",
            recommended_check="post one order directly to the payment service",
            confidence=HypothesisConfidence.HIGH,
        )


def failure(
    criterion_id: str = "ac-checkout",
    *,
    observation: str = "no confirmation appeared",
    kind: FailureKind = FailureKind.PRODUCT,
    model_derived: bool = False,
) -> CriterionResult:
    return CriterionResult(
        criterion_id=criterion_id,
        outcome=CriterionOutcome.NOT_MET,
        observation=observation,
        failure_kind=kind,
        model_derived=model_derived,
        model_invocation_id="inv-1" if model_derived else None,
        model_name="qwen" if model_derived else None,
        evidence_refs=("run-artifacts/trace.zip",),
    )


async def seed_runs(
    factory: Factory, project_id: str, failures: dict[str, list[CriterionResult]]
) -> None:
    """One finished run per entry, each carrying the criteria it failed."""
    async with factory() as uow:
        for run_id, results in failures.items():
            await uow.runs.add(
                Run(
                    run_id=run_id,
                    project_id=project_id,
                    status=RunStatus.COMPLETED,
                    verdict=Verdict.FAILED,
                )
            )
            if results:
                await uow.criterion_results.record(run_id, results)
        await uow.commit()


async def stored_clusters(factory: Factory, project_id: str) -> list[object]:
    async with factory() as uow:
        return list(await uow.failure_clusters.list_for_project(project_id, limit=50))


class TestTheGroupingIsDurableBeforeAnythingSlowHappens:
    async def test_clusters_are_stored_with_their_members(
        self, unit_of_work_factory: Factory
    ) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        await seed_runs(
            unit_of_work_factory,
            project_id,
            {"run-1": [failure()], "run-2": [failure()], "run-3": [failure()]},
        )

        result = await analyze_failures(
            unit_of_work_factory, AnalyzeFailuresCommand(run_id="run-3"), now=NOW
        )

        assert len(result.clusters) == 1
        stored = result.clusters[0]
        assert stored.size == 3
        assert set(stored.run_ids) == {"run-1", "run-2", "run-3"}
        assert stored.reason.startswith("3 failures matching")

    async def test_with_no_deep_model_the_clusters_still_land(
        self, unit_of_work_factory: Factory
    ) -> None:
        # The gate: nothing about this pass requires a large model to be reachable.
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        await seed_runs(unit_of_work_factory, project_id, {"run-1": [failure()]})

        result = await analyze_failures(
            unit_of_work_factory,
            AnalyzeFailuresCommand(run_id="run-1"),
            analyst=None,
            now=NOW,
        )

        assert result.hypotheses_recorded == 0
        assert result.clusters[0].hypothesis is None
        assert await stored_clusters(unit_of_work_factory, project_id)

    async def test_a_run_with_no_failures_stores_nothing(
        self, unit_of_work_factory: Factory
    ) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        await seed_runs(unit_of_work_factory, project_id, {"run-1": []})

        result = await analyze_failures(
            unit_of_work_factory, AnalyzeFailuresCommand(run_id="run-1"), now=NOW
        )

        assert result.clusters == ()
        assert await stored_clusters(unit_of_work_factory, project_id) == []

    async def test_a_model_judgement_is_not_grouped(self, unit_of_work_factory: Factory) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        await seed_runs(
            unit_of_work_factory, project_id, {"run-1": [failure("ac-vague", model_derived=True)]}
        )

        result = await analyze_failures(
            unit_of_work_factory, AnalyzeFailuresCommand(run_id="run-1"), now=NOW
        )

        assert result.clusters == ()

    async def test_an_unknown_run_is_a_typed_error(self, unit_of_work_factory: Factory) -> None:
        with pytest.raises(NotFoundError):
            await analyze_failures(
                unit_of_work_factory, AnalyzeFailuresCommand(run_id="ghost"), now=NOW
            )


class TestClustersAccumulateAcrossRuns:
    async def test_a_second_pass_adds_members_instead_of_a_second_cluster(
        self, unit_of_work_factory: Factory
    ) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        await seed_runs(unit_of_work_factory, project_id, {"run-1": [failure()]})
        await analyze_failures(
            unit_of_work_factory, AnalyzeFailuresCommand(run_id="run-1"), now=NOW
        )

        await seed_runs(unit_of_work_factory, project_id, {"run-2": [failure()]})
        result = await analyze_failures(
            unit_of_work_factory, AnalyzeFailuresCommand(run_id="run-2"), now=LATER
        )

        assert len(result.clusters) == 1
        assert result.clusters[0].size == 2

    async def test_when_a_problem_first_appeared_does_not_change(
        self, unit_of_work_factory: Factory
    ) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        await seed_runs(unit_of_work_factory, project_id, {"run-1": [failure()]})
        await analyze_failures(
            unit_of_work_factory, AnalyzeFailuresCommand(run_id="run-1"), now=NOW
        )

        await seed_runs(unit_of_work_factory, project_id, {"run-2": [failure()]})
        result = await analyze_failures(
            unit_of_work_factory, AnalyzeFailuresCommand(run_id="run-2"), now=LATER
        )

        assert result.clusters[0].first_seen_at == NOW
        assert result.clusters[0].last_seen_at == LATER


class TestAnExplanationIsBoughtOnce:
    """Every finished run triggers a pass, so what stops a project with one standing
    wall from buying the same explanation once per run is the freshness rule."""

    async def test_a_cluster_nobody_learned_anything_new_about_is_not_re_asked(
        self, unit_of_work_factory: Factory
    ) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        analyst = CountingAnalyst()
        await seed_runs(unit_of_work_factory, project_id, {"run-1": [failure("ac-checkout")]})
        await analyze_failures(
            unit_of_work_factory,
            AnalyzeFailuresCommand(run_id="run-1"),
            analyst=analyst,
            now=NOW,
        )

        # A different criterion, so the first cluster gains nothing and a second appears.
        await seed_runs(
            unit_of_work_factory,
            project_id,
            {"run-2": [failure("ac-login", observation="the sign-in form never loaded")]},
        )
        await analyze_failures(
            unit_of_work_factory,
            AnalyzeFailuresCommand(run_id="run-2"),
            analyst=analyst,
            now=LATER,
        )

        assert analyst.calls == 2

    async def test_a_cluster_that_doubled_is_asked_about_again(
        self, unit_of_work_factory: Factory
    ) -> None:
        # Growth is the one thing that can make an earlier explanation stop fitting.
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        analyst = CountingAnalyst()
        await seed_runs(unit_of_work_factory, project_id, {"run-1": [failure()]})
        await analyze_failures(
            unit_of_work_factory,
            AnalyzeFailuresCommand(run_id="run-1"),
            analyst=analyst,
            now=NOW,
        )

        await seed_runs(unit_of_work_factory, project_id, {"run-2": [failure()]})
        await analyze_failures(
            unit_of_work_factory,
            AnalyzeFailuresCommand(run_id="run-2"),
            analyst=analyst,
            now=LATER,
        )

        assert analyst.calls == 2

    async def test_a_cluster_the_model_failed_to_explain_is_asked_again(
        self, unit_of_work_factory: Factory
    ) -> None:
        # "The deep endpoint was down" is not an explanation, and must not be treated
        # as one once the endpoint comes back.
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        await seed_runs(unit_of_work_factory, project_id, {"run-1": [failure("ac-checkout")]})
        await analyze_failures(
            unit_of_work_factory,
            AnalyzeFailuresCommand(run_id="run-1"),
            analyst=CountingAnalyst(fails=True),
            now=NOW,
        )

        recovered = CountingAnalyst()
        await seed_runs(
            unit_of_work_factory,
            project_id,
            {"run-2": [failure("ac-login", observation="the sign-in form never loaded")]},
        )
        result = await analyze_failures(
            unit_of_work_factory,
            AnalyzeFailuresCommand(run_id="run-2"),
            analyst=recovered,
            now=LATER,
        )

        assert recovered.calls == 2
        checkout = next(item for item in result.clusters if item.criterion_id == "ac-checkout")
        assert checkout.hypothesis is not None
        assert checkout.hypothesis.failure is None


class TestRetryingCostsNothing:
    async def test_a_second_pass_over_the_same_run_asks_the_model_nothing(
        self, unit_of_work_factory: Factory
    ) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        analyst = CountingAnalyst()
        await seed_runs(unit_of_work_factory, project_id, {"run-1": [failure()]})

        first = await analyze_failures(
            unit_of_work_factory,
            AnalyzeFailuresCommand(run_id="run-1"),
            analyst=analyst,
            now=NOW,
        )
        second = await analyze_failures(
            unit_of_work_factory,
            AnalyzeFailuresCommand(run_id="run-1"),
            analyst=analyst,
            now=LATER,
        )

        assert first.hypotheses_recorded == 1
        assert second.replayed is True
        assert second.hypotheses_recorded == 0
        assert analyst.calls == 1

    async def test_the_replay_still_returns_what_was_stored(
        self, unit_of_work_factory: Factory
    ) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        await seed_runs(unit_of_work_factory, project_id, {"run-1": [failure()]})
        await analyze_failures(
            unit_of_work_factory,
            AnalyzeFailuresCommand(run_id="run-1"),
            analyst=CountingAnalyst(),
            now=NOW,
        )

        replay = await analyze_failures(
            unit_of_work_factory, AnalyzeFailuresCommand(run_id="run-1"), now=LATER
        )

        assert replay.replayed is True
        hypothesis = replay.clusters[0].hypothesis
        assert hypothesis is not None
        assert hypothesis.confidence is HypothesisConfidence.HIGH
        assert hypothesis.probable_cause.startswith("the payment service")

    async def test_the_pass_is_recorded_under_its_own_scope(
        self, unit_of_work_factory: Factory
    ) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        await seed_runs(unit_of_work_factory, project_id, {"run-1": [failure()]})

        await analyze_failures(
            unit_of_work_factory, AnalyzeFailuresCommand(run_id="run-1"), now=NOW
        )

        async with unit_of_work_factory() as uow:
            assert await uow.idempotency.get(FAILURE_ANALYSIS_SCOPE, "run-1") is not None


class TestTheModelHalfIsAdditive:
    async def test_a_hypothesis_is_stored_beside_the_members_not_over_them(
        self, unit_of_work_factory: Factory
    ) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        await seed_runs(
            unit_of_work_factory, project_id, {"run-1": [failure()], "run-2": [failure()]}
        )

        result = await analyze_failures(
            unit_of_work_factory,
            AnalyzeFailuresCommand(run_id="run-2"),
            analyst=CountingAnalyst(),
            now=NOW,
        )

        stored = result.clusters[0]
        assert stored.hypothesis is not None
        assert stored.hypothesis.model_derived is True
        assert stored.size == 2
        assert stored.reason.startswith("2 failures matching")
        assert {member.criterion_id for member in stored.members} == {"ac-checkout"}

    async def test_a_deep_model_that_failed_is_recorded_as_having_failed(
        self, unit_of_work_factory: Factory
    ) -> None:
        # Kept rather than dropped: "nobody could explain this" and "nobody asked" are
        # different states, and only one of them is worth retrying later.
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        await seed_runs(unit_of_work_factory, project_id, {"run-1": [failure()]})

        result = await analyze_failures(
            unit_of_work_factory,
            AnalyzeFailuresCommand(run_id="run-1"),
            analyst=CountingAnalyst(fails=True),
            now=NOW,
        )

        hypothesis = result.clusters[0].hypothesis
        assert hypothesis is not None
        assert hypothesis.failure == "deep model down"
        assert hypothesis.probable_cause == ""

    async def test_a_cascade_is_stored_as_blocked_and_never_analysed(
        self, unit_of_work_factory: Factory
    ) -> None:
        project_id = await seed_project_with_default_policy(unit_of_work_factory)
        analyst = CountingAnalyst()
        await seed_runs(
            unit_of_work_factory,
            project_id,
            {
                "run-1": [
                    failure("ac-login", kind=FailureKind.ENVIRONMENT, observation="unreachable"),
                    failure("ac-checkout"),
                ]
            },
        )

        result = await analyze_failures(
            unit_of_work_factory,
            AnalyzeFailuresCommand(run_id="run-1"),
            analyst=analyst,
            now=NOW,
        )

        blocked = next(item for item in result.clusters if item.blocked_by is not None)
        assert blocked.status == "blocked_downstream"
        assert blocked.blocked_by == "ac-login"
        assert blocked.hypothesis is None
        assert analyst.calls == 1
