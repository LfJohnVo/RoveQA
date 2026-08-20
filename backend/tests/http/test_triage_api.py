"""Reading a project's failure triage over HTTP.

The gate this endpoint has to hold up in public: a cluster's members and the reason it
was grouped are one thing, and a model's guess about it is another. The payload keeps
them in separate objects, and the defect count counts only what triage called
independent — a cascade that reported one bug per criterion would be the exact failure
this phase exists to prevent.
"""

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx
import pytest

from agentic_qa.application.commands.analyze_failures import (
    AnalyzeFailuresCommand,
    analyze_failures,
)
from agentic_qa.application.ports.deep_analysis import (
    ClusterAnalysisRequest,
    ClusterHypothesis,
    HypothesisConfidence,
)
from agentic_qa.bootstrap.container import Container
from agentic_qa.domain.projects.project import Project
from agentic_qa.domain.qa.verification import CriterionOutcome, CriterionResult, FailureKind
from agentic_qa.domain.runs.run import Run, RunStatus, Verdict
from agentic_qa.interfaces.http.app import create_app
from tests.fakes.repositories import InMemoryStore
from tests.fakes.unit_of_work import InMemoryUnitOfWork

NOW = datetime(2026, 8, 20, 9, 0, tzinfo=UTC)
CLUSTERS = "/api/v1/projects/proj-1/failure-clusters"


class StubAnalyst:
    async def analyze(self, request: ClusterAnalysisRequest) -> ClusterHypothesis:
        return ClusterHypothesis(
            cluster_id=request.cluster_id,
            probable_cause="the payment service rejects the order",
            recommended_check="post one order directly to the payment service",
            confidence=HypothesisConfidence.MEDIUM,
        )


def failure(
    criterion_id: str,
    *,
    observation: str = "no confirmation appeared",
    kind: FailureKind = FailureKind.PRODUCT,
) -> CriterionResult:
    return CriterionResult(
        criterion_id=criterion_id,
        outcome=CriterionOutcome.NOT_MET,
        observation=observation,
        failure_kind=kind,
    )


@pytest.fixture
async def store() -> InMemoryStore:
    store = InMemoryStore()
    async with InMemoryUnitOfWork(store) as uow:
        await uow.projects.add(Project(project_id="proj-1", name="Checkout"))
        for run_id in ("run-1", "run-2"):
            await uow.runs.add(
                Run(
                    run_id=run_id,
                    project_id="proj-1",
                    status=RunStatus.COMPLETED,
                    verdict=Verdict.FAILED,
                )
            )
        await uow.commit()
    return store


@pytest.fixture
async def client(store: InMemoryStore) -> AsyncIterator[httpx.AsyncClient]:
    container = Container(unit_of_work=lambda: InMemoryUnitOfWork(store))
    transport = httpx.ASGITransport(app=create_app(container), raise_app_exceptions=True)
    async with httpx.AsyncClient(transport=transport, base_url="http://api") as client:
        yield client


async def record(store: InMemoryStore, failures: dict[str, list[CriterionResult]]) -> None:
    async with InMemoryUnitOfWork(store) as uow:
        for run_id, results in failures.items():
            await uow.criterion_results.record(run_id, results)
        await uow.commit()
    await analyze_failures(
        lambda: InMemoryUnitOfWork(store),
        AnalyzeFailuresCommand(run_id=next(reversed(failures))),
        analyst=StubAnalyst(),
        now=NOW,
    )


async def test_a_project_with_no_failures_answers_with_an_empty_page(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get(CLUSTERS)

    assert response.status_code == 200
    assert response.json() == {"project_id": "proj-1", "clusters": [], "counted_as_defects": 0}


async def test_a_cluster_names_the_runs_that_hit_it(
    client: httpx.AsyncClient, store: InMemoryStore
) -> None:
    await record(store, {"run-1": [failure("ac-checkout")], "run-2": [failure("ac-checkout")]})

    body = (await client.get(CLUSTERS)).json()

    cluster = body["clusters"][0]
    assert cluster["size"] == 2
    assert {member["run_id"] for member in cluster["members"]} == {"run-1", "run-2"}
    assert cluster["status"] == "independent"


async def test_the_hypothesis_arrives_in_its_own_object(
    client: httpx.AsyncClient, store: InMemoryStore
) -> None:
    await record(store, {"run-1": [failure("ac-checkout")]})

    cluster = (await client.get(CLUSTERS)).json()["clusters"][0]

    assert cluster["hypothesis"]["model_derived"] is True
    assert cluster["hypothesis"]["confidence"] == "medium"
    # The observed half is not overwritten by it, and does not live inside it.
    assert "probable_cause" not in cluster
    assert cluster["reason"].startswith("1 failure matching")


async def test_a_cascade_is_visible_but_not_counted(
    client: httpx.AsyncClient, store: InMemoryStore
) -> None:
    await record(
        store,
        {
            "run-1": [
                failure("ac-login", kind=FailureKind.ENVIRONMENT, observation="unreachable"),
                failure("ac-cart"),
                failure("ac-checkout"),
            ]
        },
    )

    body = (await client.get(CLUSTERS)).json()

    assert len(body["clusters"]) == 3
    assert body["counted_as_defects"] == 1
    blocked = [item for item in body["clusters"] if item["status"] == "blocked_downstream"]
    assert {item["blocked_by"] for item in blocked} == {"ac-login"}


async def test_the_page_size_is_bounded(client: httpx.AsyncClient) -> None:
    assert (await client.get(CLUSTERS, params={"limit": 500})).status_code == 422
