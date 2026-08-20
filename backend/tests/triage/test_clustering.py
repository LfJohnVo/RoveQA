"""Deterministic failure triage.

Three of the five Phase 11 gates live here, and all three are about what happens with
**no model at all**: a batch of duplicates reduces to clusters, a cascade does not
become a pile of separate defects, and the grouping stays reproducible.

The rule every test below is really defending: what is in a cluster is decided by
evidence, and only *why* it happened is ever left to a model.
"""

from agentic_qa.domain.qa.verification import CriterionOutcome, CriterionResult, FailureKind
from agentic_qa.domain.triage.clustering import ClusterStatus, triage
from agentic_qa.domain.triage.signals import FailureSignal, normalize, signal_from


def failure(
    criterion_id: str = "ac-checkout",
    *,
    observation: str = "no confirmation appeared",
    kind: FailureKind = FailureKind.PRODUCT,
    outcome: CriterionOutcome = CriterionOutcome.NOT_MET,
    model_derived: bool = False,
) -> CriterionResult:
    return CriterionResult(
        criterion_id=criterion_id,
        outcome=outcome,
        observation=observation,
        failure_kind=kind if outcome is CriterionOutcome.NOT_MET else None,
        model_derived=model_derived,
        model_invocation_id="inv-1" if model_derived else None,
        model_name="qwen" if model_derived else None,
    )


def signal(
    run_id: str,
    criterion_id: str = "ac-checkout",
    *,
    observation: str = "no confirmation appeared",
    kind: FailureKind = FailureKind.PRODUCT,
    url: str | None = "https://app.test/checkout",
) -> FailureSignal:
    built = signal_from(
        failure(criterion_id, observation=observation, kind=kind), run_id=run_id, observed_url=url
    )
    assert built is not None
    return built


class TestOnlyVerifiedFailuresAreTriaged:
    def test_a_met_criterion_has_nothing_to_group(self) -> None:
        assert signal_from(failure(outcome=CriterionOutcome.MET), run_id="run-1") is None

    def test_a_model_judgement_is_not_a_grouping_signal(self) -> None:
        # Clustering on an opinion would build groups whose membership nobody could
        # defend afterwards.
        assert signal_from(failure(model_derived=True), run_id="run-1") is None


class TestDuplicatesBecomeOneProblem:
    def test_twenty_runs_hitting_one_wall_are_one_cluster(self) -> None:
        result = triage(signal(f"run-{index}") for index in range(20))

        assert len(result.clusters) == 1
        assert result.clusters[0].size == 20
        assert result.reduction == 0.95

    def test_the_cluster_names_every_run_that_hit_it(self) -> None:
        # A summary that cannot list its members is one nobody can check.
        result = triage([signal("run-1"), signal("run-2"), signal("run-1")])

        assert result.clusters[0].run_ids == ("run-1", "run-2")

    def test_the_representative_is_a_real_failure_not_a_summary(self) -> None:
        first = signal("run-1")
        result = triage([first, signal("run-2")])

        assert result.clusters[0].representative == first

    def test_ids_that_differ_per_run_do_not_split_a_cluster(self) -> None:
        # "order 8821 was not confirmed" and "order 8822 was not confirmed" are one
        # problem. Without normalisation they are two clusters of one, which is exactly
        # the duplication triage exists to remove.
        result = triage(
            [
                signal("run-1", observation="order 8821 was not confirmed"),
                signal("run-2", observation="order 9007 was not confirmed"),
            ]
        )

        assert len(result.clusters) == 1

    def test_genuinely_different_failures_stay_apart(self) -> None:
        result = triage(
            [
                signal("run-1", "ac-checkout"),
                signal("run-2", "ac-login", observation="the sign-in form never loaded"),
            ]
        )

        assert len(result.clusters) == 2

    def test_the_same_criterion_failing_differently_stays_apart(self) -> None:
        # Same criterion, different wall. Merging them would hide one of the two.
        result = triage(
            [
                signal("run-1", observation="no confirmation appeared"),
                signal("run-2", observation="HTTP 503 from the payment service"),
            ]
        )

        assert len(result.clusters) == 2


class TestCascadeIsNotTwelveBugs:
    def test_failures_after_a_broken_environment_are_not_counted(self) -> None:
        # One environment that went down must not become a report claiming three bugs.
        signals = [
            signal(
                "run-1", "ac-login", kind=FailureKind.ENVIRONMENT, observation="target unreachable"
            ),
            signal("run-1", "ac-cart"),
            signal("run-1", "ac-checkout"),
        ]

        result = triage(signals)

        assert len(result.independent) == 1
        assert result.independent[0].representative.criterion_id == "ac-login"
        assert {cluster.representative.criterion_id for cluster in result.blocked} == {
            "ac-cart",
            "ac-checkout",
        }

    def test_a_blocked_cluster_names_what_blocked_it(self) -> None:
        result = triage(
            [
                signal("run-1", "ac-login", kind=FailureKind.POLICY, observation="policy refused"),
                signal("run-1", "ac-checkout"),
            ]
        )

        blocked = result.blocked[0]
        assert blocked.status is ClusterStatus.BLOCKED_DOWNSTREAM
        assert blocked.blocked_by == "ac-login"
        assert "already failed setup" in blocked.reason

    def test_the_setup_failure_is_not_blocked_by_itself(self) -> None:
        # Marking it downstream would hide the one thing worth fixing.
        result = triage([signal("run-1", "ac-login", kind=FailureKind.ENVIRONMENT)])

        assert result.independent[0].representative.criterion_id == "ac-login"

    def test_a_run_that_reached_the_product_still_reports_its_defect(self) -> None:
        # Only the runs that were blocked are discounted. A defect seen in a healthy
        # run is still a defect.
        result = triage(
            [
                signal("run-1", "ac-login", kind=FailureKind.ENVIRONMENT),
                signal("run-1", "ac-checkout"),
                signal("run-2", "ac-checkout"),
            ]
        )

        checkout = next(
            cluster
            for cluster in result.clusters
            if cluster.representative.criterion_id == "ac-checkout"
        )
        assert checkout.status is ClusterStatus.INDEPENDENT
        assert checkout.run_ids == ("run-1", "run-2")

    def test_running_out_of_budget_does_not_blame_the_environment(self) -> None:
        # A budget failure is a consequence of everything before it, not a cause of
        # what came after — so it must not silence other findings.
        result = triage(
            [
                signal(
                    "run-1",
                    "ac-budget",
                    kind=FailureKind.AGENT_BUDGET,
                    observation="out of actions",
                ),
                signal("run-1", "ac-checkout"),
            ]
        )

        assert len(result.independent) == 2


class TestTriageIsReproducible:
    def test_the_same_failures_produce_the_same_clusters(self) -> None:
        signals = [signal("run-1"), signal("run-2", "ac-login"), signal("run-3")]

        first = triage(signals)
        second = triage(list(reversed(signals)))

        assert [cluster.cluster_id for cluster in first.clusters] == [
            cluster.cluster_id for cluster in second.clusters
        ]

    def test_the_biggest_problem_comes_first(self) -> None:
        result = triage([signal("run-1", "ac-login"), signal("run-2"), signal("run-3")])

        assert result.clusters[0].representative.criterion_id == "ac-checkout"
        assert result.clusters[0].size == 2

    def test_a_cluster_says_what_it_matched_on(self) -> None:
        # A cluster nobody can disagree with is one nobody can trust either.
        result = triage([signal("run-1", observation="HTTP 503 from checkout")])

        reason = result.clusters[0].reason
        assert "product on ac-checkout" in reason
        assert "HTTP 503" in reason
        assert "route /checkout" in reason

    def test_nothing_to_triage_is_not_an_error(self) -> None:
        empty = triage([])
        assert empty.clusters == ()
        assert empty.reduction == 0.0


class TestWhatIsWorthAModel:
    def test_only_independent_clusters_are_offered(self) -> None:
        # Asking a large model for the root cause of a failure the deterministic pass
        # already explained is money spent on an answer we have.
        result = triage(
            [
                signal("run-1", "ac-login", kind=FailureKind.ENVIRONMENT),
                signal("run-1", "ac-checkout"),
            ]
        )

        assert [item.criterion_id for item in result.representatives()] == ["ac-login"]

    def test_one_representative_per_problem_not_per_failure(self) -> None:
        result = triage(signal(f"run-{index}") for index in range(12))

        assert len(result.representatives()) == 1


class TestNormalisation:
    def test_it_removes_what_differs_between_runs(self) -> None:
        assert normalize("Order 88213 was not confirmed") == "order <n> was not confirmed"

    def test_it_removes_uuids(self) -> None:
        normalized = normalize("run 3f2504e0-4f89-11d3-9a0c-0305e82c3301 failed")
        assert normalized == "run <id> failed"

    def test_it_removes_quoted_values(self) -> None:
        assert normalize('expected "Order 12" on the page') == "expected <value> on the page"

    def test_it_is_bounded(self) -> None:
        # An observation is capped at 4000 characters; a grouping key built from all of
        # it would make every long failure its own cluster.
        assert len(normalize("x" * 5000)) <= 300
