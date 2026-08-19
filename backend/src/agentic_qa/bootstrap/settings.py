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
    artifact_root: str = "/data/runs"
    """Where artifact bytes live. References are in PostgreSQL; blobs are not."""

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
            artifact_root=os.environ.get("ARTIFACT_ROOT", "/data/runs"),
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


def _positive_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if not raw:
        return default
    value = float(raw)
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero, got {value}")
    return value
