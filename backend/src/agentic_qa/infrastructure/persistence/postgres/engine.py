"""Async engine/session factory for PostgreSQL."""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

DEFAULT_CONNECT_TIMEOUT_SECONDS = 10


def create_engine(dsn: str, *, echo: bool = False) -> AsyncEngine:
    return create_async_engine(
        dsn,
        echo=echo,
        pool_pre_ping=True,
        connect_args={"timeout": DEFAULT_CONNECT_TIMEOUT_SECONDS},
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    # expire_on_commit=False keeps mapped instances readable after commit, so callers
    # never trigger lazy IO outside the transaction they think they closed.
    return async_sessionmaker(engine, expire_on_commit=False)
