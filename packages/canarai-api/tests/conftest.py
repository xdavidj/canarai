"""Test fixtures and configuration."""

import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from canarai.dependencies import get_db
from canarai.main import create_app
from canarai.models import Base
from canarai.routers.sites import _site_creation_limits


@pytest.fixture(autouse=True)
def _clear_rate_limiter():
    """Clear the site creation rate limiter before every test."""
    _site_creation_limits.clear()
    yield
    _site_creation_limits.clear()


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_engine():
    """Create an in-memory SQLite engine for tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session bound to the test engine."""
    factory = async_sessionmaker(
        bind=db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_engine) -> AsyncGenerator[AsyncClient, None]:
    """Create a test HTTP client with overridden DB dependency."""
    factory = async_sessionmaker(
        bind=db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def site_with_key(client: AsyncClient) -> dict:
    """Create a site via POST /v1/sites and return key material.

    Returns a dict with keys: ``site_key``, ``api_key``, ``site_id``.
    """
    response = await client.post(
        "/v1/sites",
        json={"domain": "fixture-site.example.com"},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    return {
        "site_key": data["site"]["site_key"],
        "api_key": data["api_key"],
        "site_id": data["site"]["id"],
    }


@pytest_asyncio.fixture
async def authenticated_client(
    client: AsyncClient, site_with_key: dict
) -> tuple[AsyncClient, dict]:
    """Return (client, site_data) where site_data contains site_key/api_key/site_id.

    The caller is responsible for attaching the Authorization header when
    needed; the client itself is the same shared test client.
    """
    return client, site_with_key
