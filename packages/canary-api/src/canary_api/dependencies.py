"""FastAPI dependency injection functions."""

import hashlib
import hmac
from collections.abc import AsyncGenerator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from canary_api.config import Settings, get_settings
from canary_api.db.engine import get_session
from canary_api.models.api_key import ApiKey
from canary_api.models.site import Site


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""
    async for session in get_session():
        yield session


def get_app_settings() -> Settings:
    """Return application settings."""
    return get_settings()


def _hash_key(raw_key: str) -> str:
    """Hash an API key with SHA-256."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def verify_api_key(
    authorization: str = Header(..., description="Bearer <api_key>"),
    db: AsyncSession = Depends(get_db),
) -> ApiKey:
    """Verify Bearer token auth for management endpoints.

    Extracts the API key from the Authorization header, hashes it,
    and looks up the matching active key in the database.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must use Bearer scheme",
        )

    raw_key = authorization[7:].strip()
    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required",
        )

    key_hash = _hash_key(raw_key)
    stmt = (
        select(ApiKey)
        .where(ApiKey.key_hash == key_hash)
        .where(ApiKey.is_active.is_(True))
    )
    result = await db.execute(stmt)
    api_key = result.scalar_one_or_none()

    # Timing-safe comparison to prevent timing side-channel attacks
    if api_key is None or not hmac.compare_digest(api_key.key_hash, key_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key",
        )

    return api_key


async def verify_site_key(
    site_key: str,
    db: AsyncSession = Depends(get_db),
) -> Site:
    """Validate a site key and return the associated Site.

    Used for public endpoints where the site_key comes from the
    request body or query parameters.
    """
    stmt = (
        select(Site)
        .where(Site.site_key == site_key)
        .where(Site.is_active.is_(True))
    )
    result = await db.execute(stmt)
    site = result.scalar_one_or_none()

    if site is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid site key",
        )

    return site
