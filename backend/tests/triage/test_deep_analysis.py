"""What a large model is allowed to change about a failure cluster: nothing.

Two Phase 11 gates live here. The browser loop and the run report have to survive a
deep endpoint that is missing, slow or wrong — so "no analyst" is a normal outcome and
never an error. And a hypothesis is an addition beside the evidence, never a rewrite of
it: the members, the run ids and the grouping reason of a cluster read the same whether
a model was asked or not.
"""

from dataclasses import fields

import pytest

from agentic_qa.application.ports.deep_analysis import (
    ClusterAnalysisRequest,
    ClusterHypothesis,
    HypothesisConfidence,
)
from agentic_qa.application.services.deep_analysis import DeepAnalysisService
from agentic_qa.domain.qa.verification import CriterionOutcome, CriterionResult, FailureKind
from agentic_qa.domain.triage.clustering import TriageResult, triage
from agentic_qa.domain.triage.signals import FailureSignal, signal_from


def signal(
    run_id: str,
    criterion_id: str = "ac-checkout",
    *,
    observation: str = "no confirmation appeared",
    kind: FailureKind = FailureKind.PRODUCT,
) -> FailureSignal:
    built = signal_from(
        CriterionResult(
            criterion_id=criterion_id,
            outcome=CriterionOutcome.NOT_MET,
            observation=observation,
            failure_kind=kind,
            evidence_refs=("run-artifacts/video.webm", "run-artifacts/trace.zip"),
        ),
        run_id=run_id,
        observed_url="https://app.test/checkout?token=abc",
    )
    assert built is not None
    return built


class RecordingAnalyst:
    """Answers every cluster, and remembers exactly what it was shown."""

    def __init__(self, *, fails: bool = False) -> None:
        self.seen: list[ClusterAnalysisRequest] = []
        self._fails = fails

    async def analyze(self, request: ClusterAnalysisRequest) -> ClusterHypothesis:
        self.seen.append(request)
        if self._fails:
            return ClusterHypothesis(cluster_id=request.cluster_id, failure="deep model down")
        return ClusterHypothesis(
            cluster_id=request.cluster_id,
            probable_cause="the payment service is rejecting the order",
            recommended_check="replay one order against the payment service directly",
            confidence=HypothesisConfidence.MEDIUM,
        )


class TestARunReportsWithoutADeepModel:
    async def test_no_analyst_still_returns_every_cluster(self) -> None:
        result = await DeepAnalysisService().analyze(triage([signal("run-1"), signal("run-2")]))

        assert len(result) == 1
        assert result[0].hypothesis is None
        assert result[0].cluster.run_ids == ("run-1", "run-2")

    async def test_a_deep_endpoint_that_failed_leaves_the_cluster_intact(self) -> None:
        analyzed = await DeepAnalysisService(RecordingAnalyst(fails=True)).analyze(
            triage([signal("run-1")])
        )

        hypothesis = analyzed[0].hypothesis
        assert hypothesis is not None
        assert hypothesis.failure == "deep model down"
        assert hypothesis.probable_cause == ""
        assert analyzed[0].cluster.reason.startswith("1 failure matching")

    async def test_nothing_to_triage_asks_nothing(self) -> None:
        analyst = RecordingAnalyst()

        assert await DeepAnalysisService(analyst).analyze(TriageResult(clusters=())) == ()
        assert analyst.seen == []


class TestOnlyWhatIsWorthAskingIsAsked:
    async def test_a_cascade_is_not_sent_to_the_model(self) -> None:
        # Triage already explained it: the run had failed setup. Paying minutes of deep
        # inference to be told the same thing is the cost this ordering exists to avoid.
        analyst = RecordingAnalyst()
        analyzed = await DeepAnalysisService(analyst).analyze(
            triage(
                [
                    signal("run-1", "ac-login", kind=FailureKind.ENVIRONMENT),
                    signal("run-1", "ac-checkout"),
                ]
            )
        )

        assert [request.criterion_id for request in analyst.seen] == ["ac-login"]
        blocked = next(item for item in analyzed if item.cluster.blocked_by is not None)
        assert blocked.hypothesis is None

    async def test_the_number_of_deep_calls_is_bounded(self) -> None:
        # A run that fell apart into many distinct problems must not become one deep
        # call per problem; each costs minutes.
        analyst = RecordingAnalyst()
        signals = [signal(f"run-{index}", f"ac-{index}") for index in range(8)]

        analyzed = await DeepAnalysisService(analyst, max_clusters=3).analyze(triage(signals))

        assert len(analyst.seen) == 3
        assert len(analyzed) == 8
        assert sum(1 for item in analyzed if item.hypothesis is not None) == 3

    async def test_the_clusters_the_most_runs_hit_are_the_ones_analysed(self) -> None:
        analyst = RecordingAnalyst()
        signals = [signal("run-1", "ac-rare"), signal("run-2"), signal("run-3")]

        await DeepAnalysisService(analyst, max_clusters=1).analyze(triage(signals))

        assert [request.criterion_id for request in analyst.seen] == ["ac-checkout"]
        assert analyst.seen[0].affected_runs == 2


class TestTheModelSeesASummaryNotTheArchive:
    def test_a_request_has_nowhere_to_put_evidence(self) -> None:
        # Structural, not a policy someone has to remember: with no field for them,
        # no prompt change can start shipping every video and trace in a cluster.
        names = {field.name for field in fields(ClusterAnalysisRequest)}

        assert "evidence_refs" not in names
        assert not names & {"artifacts", "trace", "video", "screenshot", "members"}

    def test_it_carries_the_aggregate_and_the_representative_only(self) -> None:
        cluster = triage([signal("run-1"), signal("run-2"), signal("run-3")]).clusters[0]

        request = ClusterAnalysisRequest.from_cluster(cluster)

        assert request.affected_runs == 3
        assert request.observation == "no confirmation appeared"
        assert request.route == "/checkout"
        assert request.grouping_reason == cluster.reason

    def test_the_route_is_sent_without_its_query_string(self) -> None:
        # A token in a URL is a credential, and prompts travel further than runs do.
        request = ClusterAnalysisRequest.from_cluster(triage([signal("run-1")]).clusters[0])

        assert "token" not in str(request)


class TestAHypothesisNeverBecomesEvidence:
    async def test_the_members_survive_the_interpretation(self) -> None:
        analyzed = await DeepAnalysisService(RecordingAnalyst()).analyze(
            triage([signal("run-1"), signal("run-2")])
        )

        item = analyzed[0]
        assert item.hypothesis is not None
        assert item.cluster.run_ids == ("run-1", "run-2")
        assert item.cluster.members[0].evidence_refs == (
            "run-artifacts/video.webm",
            "run-artifacts/trace.zip",
        )

    def test_a_hypothesis_cannot_claim_to_be_an_observation(self) -> None:
        with pytest.raises(ValueError, match="model-derived"):
            ClusterHypothesis(cluster_id="c-1", model_derived=False)

    def test_a_failed_analysis_cannot_also_carry_a_cause(self) -> None:
        with pytest.raises(ValueError, match="cannot also carry a cause"):
            ClusterHypothesis(cluster_id="c-1", probable_cause="something", failure="down")
