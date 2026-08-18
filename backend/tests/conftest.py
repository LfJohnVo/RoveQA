"""Shared fixtures.

`repositories` is parametrized over every repository implementation so the contract
suite in tests/contracts runs unchanged against fakes and real adapters.
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass

import pytest

from agentic_qa.application.ports.repositories import (
    ProjectRepository,
    RunRepository,
    StoryRepository,
)
from tests.fakes.repositories import (
    InMemoryProjectRepository,
    InMemoryRunRepository,
    InMemoryStoryRepository,
)


@dataclass
class Repositories:
    projects: ProjectRepository
    stories: StoryRepository
    runs: RunRepository


@pytest.fixture(params=["memory"])
async def repositories(request: pytest.FixtureRequest) -> AsyncIterator[Repositories]:
    if request.param == "memory":
        yield Repositories(
            projects=InMemoryProjectRepository(),
            stories=InMemoryStoryRepository(),
            runs=InMemoryRunRepository(),
        )
        return
    raise AssertionError(f"unknown repository implementation: {request.param}")
