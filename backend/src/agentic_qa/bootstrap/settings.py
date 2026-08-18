"""Runtime configuration read from the environment.

Secrets never live in code or in version-controlled config (docs/13); `.env.example`
documents the schema.
"""

import os
from dataclasses import dataclass

DEFAULT_POSTGRES_DSN = "postgresql+asyncpg://agentic:agentic@localhost:5432/agentic_qa"


@dataclass(frozen=True)
class Settings:
    postgres_dsn: str
    sql_echo: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            postgres_dsn=os.environ.get("POSTGRES_DSN", DEFAULT_POSTGRES_DSN),
            sql_echo=os.environ.get("SQL_ECHO", "").lower() in {"1", "true", "yes"},
        )
