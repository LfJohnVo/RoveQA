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


@dataclass(frozen=True)
class Settings:
    postgres_dsn: str
    redis_url: str = DEFAULT_REDIS_URL
    temporal_address: str = DEFAULT_TEMPORAL_ADDRESS
    temporal_namespace: str = DEFAULT_TEMPORAL_NAMESPACE
    temporal_task_queue: str = DEFAULT_TEMPORAL_TASK_QUEUE
    sql_echo: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            postgres_dsn=os.environ.get("POSTGRES_DSN", DEFAULT_POSTGRES_DSN),
            redis_url=os.environ.get("REDIS_URL", DEFAULT_REDIS_URL),
            temporal_address=os.environ.get("TEMPORAL_ADDRESS", DEFAULT_TEMPORAL_ADDRESS),
            temporal_namespace=os.environ.get("TEMPORAL_NAMESPACE", DEFAULT_TEMPORAL_NAMESPACE),
            temporal_task_queue=os.environ.get("TEMPORAL_TASK_QUEUE", DEFAULT_TEMPORAL_TASK_QUEUE),
            sql_echo=os.environ.get("SQL_ECHO", "").lower() in {"1", "true", "yes"},
        )
