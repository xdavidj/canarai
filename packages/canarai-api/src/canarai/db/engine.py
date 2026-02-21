"""Async database engine and session factory."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from canarai.config import get_settings

_engine = None
_session_factory = None


def _get_engine():
    """Create or return the cached async engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        url = settings.database_url

        connect_args = {}
        if url.startswith("sqlite"):
            connect_args["check_same_thread"] = False

        _engine = create_async_engine(
            url,
            echo=(settings.environment == "development"),
            connect_args=connect_args,
        )
    return _engine


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Create or return the cached session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=_get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def init_db() -> None:
    """Create all tables from metadata. Used for development/testing."""
    from canarai.models import Base  # noqa: F811

    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for FastAPI dependency injection."""
    factory = _get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    """Dispose of the engine. Called on app shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
