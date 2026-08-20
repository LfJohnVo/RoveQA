"""Drop and recreate the test database's schema.

The suite's database is disposable — it exists only for pytest and the suite already
truncates it between tests. Resetting it before the gate migrates it is what keeps the
gate reproducible: `pytest` falls back to `create_all` when the schema is missing, so a
developer who runs the suite before running the gate leaves tables behind that no
migration ever created, and the next `alembic upgrade head` then fails on a table it is
about to create.

Deliberately refuses any DSN that does not name a test database, because the difference
between this and a catastrophe is one environment variable.
"""

import asyncio
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

REQUIRED_MARKER = "test"


async def reset(dsn: str) -> None:
    engine = create_async_engine(dsn, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as connection:
            await connection.execute(text("DROP SCHEMA public CASCADE"))
            await connection.execute(text("CREATE SCHEMA public"))
    finally:
        await engine.dispose()


def main() -> int:
    dsn = os.environ.get("POSTGRES_TEST_DSN", "")
    if not dsn:
        print("POSTGRES_TEST_DSN is not set", file=sys.stderr)
        return 1

    database = dsn.rsplit("/", 1)[-1].split("?", 1)[0]
    if REQUIRED_MARKER not in database:
        # A guard, not a formality: this script drops everything it is pointed at.
        print(f"refusing to reset {database!r}: not a test database", file=sys.stderr)
        return 1

    asyncio.run(reset(dsn))
    print(f"reset schema of {database}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
