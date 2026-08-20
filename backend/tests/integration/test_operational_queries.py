"""Every operational query, executed against the real schema.

The reason these live as code instead of as snippets in a document: a query that
silently stopped matching the schema would be worse than no query at all, because
somebody would read its empty result as "no failures" rather than as "this has been
broken since the column was renamed".

So the suite runs all of them, twice over: against an empty database, where each must
still answer rather than error, and against a database with a run in it, where the ones
that count things must count.
"""

from collections.abc import AsyncIterator, Callable
from uuid import uuid4

import psycopg
import pytest
from sqlalchemy import text

from agentic_qa.application.ports.unit_of_work import UnitOfWork
from agentic_qa.domain.qa.verification import CriterionOutcome, CriterionResult, FailureKind
from agentic_qa.domain.runs.run import Run, RunStatus, Verdict
from agentic_qa.infrastructure.observability.queries import (
    OPERATIONAL_QUERIES,
    OperationalQuery,
    query_named,
)
from agentic_qa.infrastructure.persistence.postgres.engine import create_engine
from tests.conftest import (
    postgres_test_dsn,
    postgres_unit_of_work_scope,
    seed_project_with_default_policy,
)

Factory = Callable[[], UnitOfWork]


@pytest.fixture
async def factory() -> AsyncIterator[Factory]:
    try:
        async with postgres_unit_of_work_scope() as real:
            yield real
    except (OSError, psycopg.OperationalError) as error:  # pragma: no cover - env guard
        pytest.skip(f"PostgreSQL not reachable: {error}")


async def rows(query: OperationalQuery) -> list[dict[str, object]]:
    """Run one query the way an operator would: a connection, the SQL, the rows.

    Deliberately not through a unit of work. These are read-only questions asked from
    outside the application, and going through the write path would prove they work in
    a context nobody uses them from.
    """
    engine = create_engine(postgres_test_dsn())
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text(query.sql))
            return [dict(row) for row in result.mappings()]
    finally:
        await engine.dispose()


@pytest.mark.parametrize("query", OPERATIONAL_QUERIES, ids=lambda item: item.name)
async def test_every_query_runs_against_an_empty_database(
    factory: Factory, query: OperationalQuery
) -> None:
    """An empty deployment is the first one anybody points these at.

    A query that only works once there is data is a query nobody trusts the first time
    they need it.
    """
    await rows(query)


@pytest.mark.parametrize("query", OPERATIONAL_QUERIES, ids=lambda item: item.name)
def test_every_query_explains_what_it_answers(query: OperationalQuery) -> None:
    # The name is a handle; the question is the meaning. One without the other leaves a
    # reader guessing what an empty result means.
    assert query.question.strip()
    assert query.name == query.name.lower().replace(" ", "_")


async def test_the_counting_queries_count(factory: Factory) -> None:
    project_id = await seed_project_with_default_policy(factory, name="Observed")
    run_id = f"r-{uuid4()}"
    async with factory() as uow:
        run = Run(run_id=run_id, project_id=project_id)
        # Through the state machine, like production: reaching past it would let this
        # test pass against a status the domain would refuse.
        run.transition_to(RunStatus.QUEUED)
        run.transition_to(RunStatus.RUNNING)
        run.transition_to(RunStatus.COMPLETED, Verdict.FAILED)
        await uow.runs.add(run)
        await uow.criterion_results.record(
            run_id,
            [
                CriterionResult(
                    criterion_id="ac-checkout",
                    outcome=CriterionOutcome.NOT_MET,
                    observation="no confirmation appeared",
                    failure_kind=FailureKind.PRODUCT,
                ),
                CriterionResult(
                    criterion_id="ac-budget",
                    outcome=CriterionOutcome.NOT_MET,
                    observation="the run reached its limit of 3 action(s)",
                    failure_kind=FailureKind.AGENT_BUDGET,
                ),
            ],
        )
        await uow.commit()

    kinds = {
        str(row["failure_kind"]): row["results"] for row in await rows(query_named("failure_kinds"))
    }
    assert kinds["product"] == 1
    assert kinds["agent_budget"] == 1

    statuses = {
        str(row["status"]): row["runs"] for row in await rows(query_named("runs_by_status"))
    }
    assert statuses["completed"] == 1

    derived = (await rows(query_named("model_derived_share")))[0]
    assert derived["deterministic"] == 2
    assert derived["model_derived"] == 0


async def test_the_triage_query_reports_zero_rather_than_nothing(factory: Factory) -> None:
    """An aggregate over no rows must still return a row.

    "No clusters" and "the query returned nothing" look the same to a dashboard, and
    only one of them is a fact about the system.
    """
    result = await rows(query_named("triage_reduction"))

    assert len(result) == 1
    assert result[0]["raw_failures"] == 0
    assert result[0]["clusters"] == 0


def test_a_query_that_does_not_exist_is_a_typed_absence() -> None:
    with pytest.raises(KeyError):
        query_named("no-such-question")


def test_no_query_reaches_for_page_content() -> None:
    """Telemetry must not carry what a page said.

    An observation or a summary can contain fixture credentials and untrusted text; a
    dashboard is one of the places that text travels furthest (docs/13, docs/14).
    """
    forbidden = ("observation", "summary", "payload", "extracted", "prompt", "completion")
    for query in OPERATIONAL_QUERIES:
        lowered = query.sql.lower()
        assert not any(word in lowered for word in forbidden), query.name
