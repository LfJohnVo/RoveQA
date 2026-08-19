"""Transaction boundary port.

Repositories are reached *through* a unit of work so a use case cannot accidentally
mix repositories bound to different transactions — the failure mode that silently
breaks atomicity. Leaving the block without `commit()` rolls back: forgetting to
commit must lose the write, never persist half of it.
"""

from types import TracebackType
from typing import Protocol, Self

from agentic_qa.application.ports.artifacts import ArtifactIndex
from agentic_qa.application.ports.checkpoints import RecoveryPointRepository
from agentic_qa.application.ports.events import RunEventLog
from agentic_qa.application.ports.idempotency import IdempotencyRepository
from agentic_qa.application.ports.plans import TestPlanRepository
from agentic_qa.application.ports.policies import EnvironmentRepository, RunPolicyRepository
from agentic_qa.application.ports.repositories import (
    ProjectRepository,
    RunRepository,
    StoryRepository,
)
from agentic_qa.application.ports.results import CriterionResultRepository


class UnitOfWork(Protocol):
    @property
    def projects(self) -> ProjectRepository: ...

    @property
    def stories(self) -> StoryRepository: ...

    @property
    def runs(self) -> RunRepository: ...

    @property
    def idempotency(self) -> IdempotencyRepository: ...

    @property
    def events(self) -> RunEventLog: ...

    @property
    def policies(self) -> RunPolicyRepository: ...

    @property
    def environments(self) -> EnvironmentRepository: ...

    @property
    def recovery_points(self) -> RecoveryPointRepository: ...

    @property
    def plans(self) -> TestPlanRepository: ...

    @property
    def criterion_results(self) -> CriterionResultRepository: ...

    @property
    def artifacts(self) -> ArtifactIndex: ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Roll back unless commit() already ran."""
        ...

    async def commit(self) -> None: ...
