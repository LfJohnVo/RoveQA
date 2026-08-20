"""Operational questions, answered from durable rows.

Why SQL and not a metrics backend: the numbers an operator actually needs here are
already in PostgreSQL, written by the runs themselves. Counters in a worker process
answer the same questions worse — they reset when the worker restarts, they say nothing
about the run that finished yesterday, and reading them requires the process that holds
them to still be alive. A deployment that has to be running to explain what happened is
not observable.

The in-process counters (`InferenceMetrics`, `MemoryMetrics`) stay for what they are good
at: per-call latency and token accounting that no table records. They log a line per
call, so their history lives in the log, not in a scrape endpoint nobody has yet.

Every query here is executed by `tests/integration/test_operational_queries.py` against
the real schema. That is the point of keeping them as code rather than as snippets in a
document: a query that silently stopped matching the schema would be worse than none,
because somebody would read its empty result as "no failures".

None of these return page content, prompts, or anything a credential can hide in.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class OperationalQuery:
    name: str
    question: str
    """What an operator is actually asking. The name is a handle; this is the meaning."""

    sql: str


OPERATIONAL_QUERIES: tuple[OperationalQuery, ...] = (
    OperationalQuery(
        name="runs_by_status",
        question="How many runs are queued, running or finished right now?",
        sql="""
            SELECT status, count(*) AS runs
            FROM runs
            GROUP BY status
            ORDER BY runs DESC
        """,
    ),
    OperationalQuery(
        name="verdicts_last_7_days",
        question="What did the last week of runs conclude?",
        sql="""
            SELECT coalesce(verdict, 'none') AS verdict, count(*) AS runs
            FROM runs
            WHERE created_at >= now() - interval '7 days'
            GROUP BY verdict
            ORDER BY runs DESC
        """,
    ),
    OperationalQuery(
        name="run_duration_percentiles",
        question="How long do runs take, from first status change to last?",
        sql="""
            WITH span AS (
                SELECT run_id,
                       extract(epoch FROM max(occurred_at) - min(occurred_at)) AS seconds
                FROM run_events
                GROUP BY run_id
                HAVING count(*) > 1
            )
            SELECT
                percentile_disc(0.5) WITHIN GROUP (ORDER BY seconds) AS p50_seconds,
                percentile_disc(0.95) WITHIN GROUP (ORDER BY seconds) AS p95_seconds,
                max(seconds) AS max_seconds
            FROM span
        """,
    ),
    OperationalQuery(
        name="failure_kinds",
        question=(
            "Which kinds of failure are we producing? A rising share of anything other "
            "than `product` means the system is failing to test, not finding defects."
        ),
        sql="""
            SELECT failure_kind, count(*) AS results
            FROM criterion_results
            WHERE outcome = 'not_met'
            GROUP BY failure_kind
            ORDER BY results DESC
        """,
    ),
    OperationalQuery(
        name="model_derived_share",
        question=(
            "How much of what we report rests on a model's opinion rather than a "
            "deterministic check?"
        ),
        sql="""
            SELECT
                count(*) FILTER (WHERE model_derived) AS model_derived,
                count(*) FILTER (WHERE NOT model_derived) AS deterministic
            FROM criterion_results
        """,
    ),
    OperationalQuery(
        name="triage_reduction",
        question=(
            "How much smaller did triage make the investigation? Raw failures against "
            "the clusters they collapsed into, and how many count as defects."
        ),
        sql="""
            SELECT
                (SELECT count(*) FROM failure_cluster_members) AS raw_failures,
                (SELECT count(*) FROM failure_clusters) AS clusters,
                (SELECT count(*) FROM failure_clusters WHERE status = 'independent')
                    AS counted_as_defects
        """,
    ),
    OperationalQuery(
        name="clusters_without_an_explanation",
        question=(
            "Which independent clusters nobody explained? A cluster whose deep analysis "
            "failed is different from one nobody asked about, and both are here."
        ),
        sql="""
            SELECT c.cluster_id, c.criterion_id, c.last_seen_at,
                   count(h.id) AS hypotheses,
                   count(h.id) FILTER (WHERE h.failure IS NOT NULL) AS failed_attempts
            FROM failure_clusters c
            LEFT JOIN cluster_hypotheses h ON h.cluster_pk = c.id
            WHERE c.status = 'independent'
            GROUP BY c.cluster_id, c.criterion_id, c.last_seen_at
            HAVING count(h.id) FILTER (WHERE h.failure IS NULL) = 0
            ORDER BY c.last_seen_at DESC
        """,
    ),
    OperationalQuery(
        name="checkpoint_age",
        question=(
            "How stale is the newest recovery point of each unfinished run? A run whose "
            "safe point stopped advancing is a run that would restart from far back."
        ),
        sql="""
            SELECT r.run_id,
                   max(p.created_at) AS last_safe_point,
                   extract(epoch FROM now() - max(p.created_at)) AS age_seconds
            FROM runs r
            LEFT JOIN recovery_points p ON p.run_id = r.run_id
            WHERE r.status IN ('queued', 'running', 'pausing', 'paused')
            GROUP BY r.run_id
            ORDER BY age_seconds DESC NULLS FIRST
        """,
    ),
    OperationalQuery(
        name="idempotency_traffic",
        question=(
            "How often is each idempotent operation being asked for? A scope whose count "
            "grows faster than its resources means retries are landing."
        ),
        sql="""
            SELECT scope, count(*) AS records, max(created_at) AS latest
            FROM idempotency_records
            GROUP BY scope
            ORDER BY records DESC
        """,
    ),
    OperationalQuery(
        name="graph_sync_backlog",
        question=(
            "Is the learned-memory projection keeping up? Pending work is normal; a "
            "backlog that only grows means the graph is down or a candidate is stuck."
        ),
        sql="""
            SELECT state, count(*) AS candidates, max(attempts) AS worst_attempts
            FROM graph_sync_state
            GROUP BY state
            ORDER BY candidates DESC
        """,
    ),
    OperationalQuery(
        name="knowledge_by_status",
        question="How much has been learned, and how much of it is trusted enough to act on?",
        sql="""
            SELECT status, count(*) AS candidates,
                   count(*) FILTER (WHERE model_derived) AS model_derived
            FROM knowledge_candidates
            GROUP BY status
            ORDER BY candidates DESC
        """,
    ),
    OperationalQuery(
        name="exploration_coverage",
        question=(
            "What did the explorations map, and why did they stop? A rising share of "
            "budget stops means the maps are getting less complete, not the app smaller."
        ),
        sql="""
            SELECT stop_reason,
                   count(*) AS runs,
                   sum(states_discovered) AS states,
                   sum(declined) AS controls_not_taken
            FROM exploration_runs
            GROUP BY stop_reason
            ORDER BY runs DESC
        """,
    ),
    OperationalQuery(
        name="artifact_footprint",
        question="How much evidence is on disk, per project?",
        sql="""
            SELECT r.project_id,
                   count(a.artifact_id) AS artifacts,
                   coalesce(sum(a.size_bytes), 0) AS bytes
            FROM artifacts a
            JOIN runs r ON r.run_id = a.run_id
            GROUP BY r.project_id
            ORDER BY bytes DESC
        """,
    ),
)


def query_named(name: str) -> OperationalQuery:
    for query in OPERATIONAL_QUERIES:
        if query.name == name:
            return query
    raise KeyError(name)
