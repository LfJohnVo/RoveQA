"""Runtime configuration read from the environment.

Secrets never live in code or in version-controlled config (docs/13); `.env.example`
documents the schema.
"""

import os
from dataclasses import dataclass

DEFAULT_POSTGRES_DSN = "postgresql+asyncpg://agentic:agentic@localhost:5432/agentic_qa"
DEFAULT_REDIS_URL = "redis://localhost:6379/0"
DEFAULT_TEMPORAL_ADDRESS = "localhost:7233"
DEFAULT_TEMPORAL_NAMESPACE = "default"
DEFAULT_TEMPORAL_TASK_QUEUE = "agentic-qa"
DEFAULT_MODEL_CONCURRENCY = 2
DEFAULT_MODEL_TIMEOUT_SECONDS = 60.0
DEFAULT_GRAPH_DATABASE = "roveqa"
DEFAULT_DEEP_TIMEOUT_SECONDS = 900.0


@dataclass(frozen=True)
class Settings:
    postgres_dsn: str
    redis_url: str = DEFAULT_REDIS_URL
    temporal_address: str = DEFAULT_TEMPORAL_ADDRESS
    temporal_namespace: str = DEFAULT_TEMPORAL_NAMESPACE
    temporal_task_queue: str = DEFAULT_TEMPORAL_TASK_QUEUE
    sql_echo: bool = False

    vllm_base_url: str | None = None
    """Absent means no agent runtime is configured; the worker says so rather than
    pretending to plan (docs/08)."""

    vllm_model: str = ""
    model_max_concurrency: int = DEFAULT_MODEL_CONCURRENCY
    """Parallel calls the model server can actually serve. It is a property of the
    box, so it is configuration, not a constant."""

    model_timeout_seconds: float = DEFAULT_MODEL_TIMEOUT_SECONDS
    browser_headless: bool = True
    browser_navigation_timeout_ms: int | None = None
    """How long a navigation may take, or None for the browser adapter's own default.

    Deliberately not a second copy of that number: a navigation budget is a browser
    concern and the adapter owns it, so settings carries an override rather than a
    duplicate that could drift. It is separate from the element timeout because a public
    site can spend twenty seconds on images the agent never reads, and one constant for
    both jobs is what stopped every run against the real web."""
    artifact_root: str = "/data/runs"
    """Where artifact bytes live. References are in PostgreSQL; blobs are not."""

    falkordb_url: str | None = None
    """Absent means no learned-memory projection. Runs still read their memory from
    PostgreSQL, so this being unset costs retrieval breadth and nothing else."""

    graph_database: str = DEFAULT_GRAPH_DATABASE

    embedding_base_url: str | None = None
    """A vLLM pooling endpoint, separate from the generation one (ADR 0008). Absent
    means no semantic search: the graph still answers by traversal, and the
    deterministic ranking in PostgreSQL is unaffected."""

    embedding_model: str = ""

    deep_base_url: str | None = None
    """An OpenAI-compatible endpoint serving the deep-analysis model — AirLLM, or a
    second vLLM with a larger model. Absent means no deep analysis: triage still groups
    failures and the run still reports them, with no hypothesis attached (docs/08)."""

    deep_model: str = ""
    deep_timeout_seconds: float = DEFAULT_DEEP_TIMEOUT_SECONDS
    """Minutes, not seconds. A model streamed layer by layer answers slowly by design,
    and a timeout borrowed from the fast path would cancel every deep call."""

    deep_max_output_tokens: int = 800

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            postgres_dsn=os.environ.get("POSTGRES_DSN", DEFAULT_POSTGRES_DSN),
            redis_url=os.environ.get("REDIS_URL", DEFAULT_REDIS_URL),
            temporal_address=os.environ.get("TEMPORAL_ADDRESS", DEFAULT_TEMPORAL_ADDRESS),
            temporal_namespace=os.environ.get("TEMPORAL_NAMESPACE", DEFAULT_TEMPORAL_NAMESPACE),
            temporal_task_queue=os.environ.get("TEMPORAL_TASK_QUEUE", DEFAULT_TEMPORAL_TASK_QUEUE),
            sql_echo=_flag("SQL_ECHO"),
            vllm_base_url=os.environ.get("VLLM_BASE_URL") or None,
            vllm_model=os.environ.get("VLLM_MODEL", ""),
            model_max_concurrency=_positive_int("MODEL_MAX_CONCURRENCY", DEFAULT_MODEL_CONCURRENCY),
            model_timeout_seconds=_positive_float(
                "MODEL_TIMEOUT_SECONDS", DEFAULT_MODEL_TIMEOUT_SECONDS
            ),
            browser_headless=not _flag("BROWSER_HEADED"),
            browser_navigation_timeout_ms=_optional_positive_int("BROWSER_NAVIGATION_TIMEOUT_MS"),
            artifact_root=os.environ.get("ARTIFACT_ROOT", "/data/runs"),
            falkordb_url=os.environ.get("FALKORDB_URL") or None,
            graph_database=os.environ.get("GRAPH_DATABASE", DEFAULT_GRAPH_DATABASE),
            embedding_base_url=os.environ.get("EMBEDDING_BASE_URL") or None,
            embedding_model=os.environ.get("EMBEDDING_MODEL", ""),
            deep_base_url=os.environ.get("DEEP_BASE_URL") or None,
            deep_model=os.environ.get("DEEP_MODEL", ""),
            deep_timeout_seconds=_positive_float(
                "DEEP_TIMEOUT_SECONDS", DEFAULT_DEEP_TIMEOUT_SECONDS
            ),
            deep_max_output_tokens=_positive_int("DEEP_MAX_OUTPUT_TOKENS", 800),
        )


def _flag(name: str) -> bool:
    return os.environ.get(name, "").lower() in {"1", "true", "yes"}


def _positive_int(name: str, default: int) -> int:
    """A misconfigured limit fails at startup, not as strange behaviour under load."""
    raw = os.environ.get(name)
    if not raw:
        return default
    value = int(raw)
    if value < 1:
        raise ValueError(f"{name} must be at least 1, got {value}")
    return value


def _optional_positive_int(name: str) -> int | None:
    """None when unset, so the adapter's own default stays the single source of truth."""
    raw = os.environ.get(name)
    if not raw:
        return None
    value = int(raw)
    if value < 1:
        raise ValueError(f"{name} must be at least 1, got {value}")
    return value


def _positive_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if not raw:
        return default
    value = float(raw)
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero, got {value}")
    return value
