"""What the counters have to be able to tell an operator.

A run's verdict looks identical whether memory helped, did nothing, or filled the
prompt with guesses. These numbers are the only place that difference is visible, so
they have to distinguish the cases rather than aggregate them away.
"""

from agentic_qa.infrastructure.knowledge.metrics import MemoryMetrics


class TestHitRate:
    def test_no_retrievals_is_zero_not_undefined(self) -> None:
        assert MemoryMetrics().hit_rate == 0.0

    def test_a_retrieval_that_returned_nothing_counts_as_a_miss(self) -> None:
        # A cold run is a real outcome, not an absence of data. Counting only warm
        # retrievals would make the hit rate permanently 1.0.
        metrics = MemoryMetrics()
        metrics.record_retrieval(project_id="p", items=0, revalidate=0, model_derived=0)
        metrics.record_retrieval(project_id="p", items=3, revalidate=0, model_derived=0)

        assert metrics.retrievals == 2
        assert metrics.warm_retrievals == 1
        assert metrics.hit_rate == 0.5


def test_hypotheses_are_counted_separately_from_facts() -> None:
    # A context filling up with guesses means promotion has stalled — invisible in a
    # total item count, and it is exactly the state where memory starts hurting.
    metrics = MemoryMetrics()
    metrics.record_retrieval(project_id="p", items=5, revalidate=1, model_derived=4)

    assert metrics.items_offered == 5
    assert metrics.model_derived_offered == 4
    assert metrics.items_needing_revalidation == 1


def test_what_was_learned_and_what_was_withdrawn_are_both_visible() -> None:
    metrics = MemoryMetrics()
    metrics.record_consolidation(run_id="run-1", learned=3, contradicted=1)
    metrics.record_consolidation(run_id="run-2", learned=2, contradicted=0)

    assert metrics.candidates_learned == 5
    # Growth alone would look healthy while memory quietly went stale.
    assert metrics.candidates_contradicted == 1


def test_a_projection_that_never_catches_up_is_countable() -> None:
    metrics = MemoryMetrics()
    metrics.record_sync(materialized=0, forgotten=0, failed=4)
    metrics.record_sync(materialized=2, forgotten=1, failed=0)

    assert metrics.graph_failures == 4
    assert metrics.graph_writes == 2
    assert metrics.graph_removals == 1


def test_nothing_derived_from_page_content_is_recorded() -> None:
    """Summaries and payloads never reach the log line.

    They derive from page content, which is untrusted data and may carry fixture
    credentials — and a metrics log is the last place anyone looks for a leak.
    """
    import logging

    records: list[logging.LogRecord] = []

    class Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    logger = logging.getLogger("agentic_qa.infrastructure.knowledge.metrics")
    handler = Capture()
    logger.addHandler(handler)
    previous = logger.level
    logger.setLevel(logging.INFO)
    try:
        MemoryMetrics().record_retrieval(
            project_id="proj-1", items=2, revalidate=0, model_derived=0
        )
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous)

    assert records
    recorded = {key: value for key, value in records[0].__dict__.items()}
    assert "summary" not in recorded
    assert "payload" not in recorded
    assert recorded["project_id"] == "proj-1"
