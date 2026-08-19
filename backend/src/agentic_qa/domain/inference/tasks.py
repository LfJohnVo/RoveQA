"""Inference task types and capabilities (docs/08).

The domain names *what kind of thinking* it needs, never which model provides it.
That is what lets the router send fast decisions to vLLM and deep analysis to AirLLM
without a single model name leaking into a use case.
"""

from dataclasses import dataclass
from enum import StrEnum


class TaskType(StrEnum):
    GUI_ACTION = "gui_action"
    STRUCTURED_EXTRACTION = "structured_extraction"
    SHORT_PLANNING = "short_planning"
    SEMANTIC_VERIFICATION = "semantic_verification"
    DEEP_PLAN = "deep_plan"
    RUN_CRITIQUE = "run_critique"
    ROOT_CAUSE_ANALYSIS = "root_cause_analysis"
    FAILURE_CLUSTER_SUMMARY = "failure_cluster_summary"
    MEMORY_CONSOLIDATION = "memory_consolidation"
    MEMORY_ENTITY_EXTRACTION = "memory_entity_extraction"
    EMBEDDING = "embedding"


class ModelCapability(StrEnum):
    """What a task needs, not who provides it."""

    FAST = "fast"
    """Short, frequent decisions. Latency matters more than depth."""

    DEEP = "deep"
    """Cold-path reasoning. Never on the per-action loop (docs/08)."""

    POOLING = "pooling"
    """Embeddings only, no generation."""


# Fixed here rather than configured: this mapping is a design decision about how the
# product thinks, while *which model* serves a capability is deployment configuration.
CAPABILITY_BY_TASK: dict[TaskType, ModelCapability] = {
    TaskType.GUI_ACTION: ModelCapability.FAST,
    TaskType.STRUCTURED_EXTRACTION: ModelCapability.FAST,
    TaskType.SHORT_PLANNING: ModelCapability.FAST,
    TaskType.SEMANTIC_VERIFICATION: ModelCapability.FAST,
    TaskType.DEEP_PLAN: ModelCapability.DEEP,
    TaskType.RUN_CRITIQUE: ModelCapability.DEEP,
    TaskType.ROOT_CAUSE_ANALYSIS: ModelCapability.DEEP,
    TaskType.FAILURE_CLUSTER_SUMMARY: ModelCapability.DEEP,
    TaskType.MEMORY_CONSOLIDATION: ModelCapability.DEEP,
    TaskType.MEMORY_ENTITY_EXTRACTION: ModelCapability.FAST,
    TaskType.EMBEDDING: ModelCapability.POOLING,
}


def capability_for(task: TaskType) -> ModelCapability:
    return CAPABILITY_BY_TASK[task]


@dataclass(frozen=True)
class InferenceBudget:
    """Bounds every call carries. An unbounded model call is an unbounded run."""

    timeout_seconds: float = 30.0
    max_output_tokens: int = 512
    max_attempts: int = 2
    """Transport retries only; a model that answered badly is not retried blindly."""
