"""Site management endpoints."""

import hashlib
import secrets
import uuid
from collections import defaultdict
from time import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from canarai.dependencies import get_db, verify_api_key
from canarai.models.api_key import ApiKey
from canarai.models.site import Site
from canarai.schemas.site import (
    SiteCreate,
    SiteCreateResponse,
    SiteResponse,
    SiteUpdate,
)

router = APIRouter(prefix="/v1/sites", tags=["sites"])

# In-memory rate limiter for unauthenticated site creation
_site_creation_limits: dict[str, list[float]] = defaultdict(list)
SITE_CREATION_LIMIT = 5
SITE_CREATION_WINDOW = 3600  # 1 hour in seconds


def _generate_site_key(environment: str) -> str:
    """Generate a unique site key like ca_live_XXXX or ca_test_XXXX."""
    suffix = secrets.token_hex(12)
    prefix = "ca_live" if environment == "live" else "ca_test"
    return f"{prefix}_{suffix}"


def _generate_api_key() -> str:
    """Generate a raw API key like ca_sk_XXXXXXXX."""
    return f"ca_sk_{secrets.token_hex(24)}"


def _hash_key(raw_key: str) -> str:
    """Hash an API key with SHA-256."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


@router.post(
    "",
    response_model=SiteCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_site(
    body: SiteCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SiteCreateResponse:
    """Create a new site and generate its site_key and API key.

    The raw API key is returned only once in this response.
    Rate limited to 5 creations per hour per client IP.
    """
    # Rate limit by client IP
    client_ip = request.client.host if request.client else "unknown"
    now = time()
    # Prune timestamps outside the window
    _site_creation_limits[client_ip] = [
        ts for ts in _site_creation_limits[client_ip] if now - ts < SITE_CREATION_WINDOW
    ]
    if len(_site_creation_limits[client_ip]) >= SITE_CREATION_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded: maximum 5 site creations per hour",
        )
    _site_creation_limits[client_ip].append(now)

    site_key = _generate_site_key(body.environment)
    site_id = str(uuid.uuid4())

    site = Site(
        id=site_id,
        site_key=site_key,
        domain=body.domain,
        config=body.config.model_dump(),
    )
    db.add(site)

    # Generate API key
    raw_api_key = _generate_api_key()
    api_key_prefix = raw_api_key[:11]  # ca_sk_XXXXX

    api_key = ApiKey(
        id=str(uuid.uuid4()),
        site_id=site_id,
        key_hash=_hash_key(raw_api_key),
        prefix=api_key_prefix,
        environment=body.environment,
    )
    db.add(api_key)

    await db.flush()

    return SiteCreateResponse(
        site=SiteResponse.model_validate(site),
        api_key=raw_api_key,
        api_key_prefix=api_key_prefix,
    )


@router.get("", response_model=list[SiteResponse])
async def list_sites(
    api_key: ApiKey = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> list[SiteResponse]:
    """List all sites accessible by the authenticated API key."""
    stmt = select(Site).where(Site.id == api_key.site_id).order_by(Site.created_at.desc())
    result = await db.execute(stmt)
    sites = result.scalars().all()
    return [SiteResponse.model_validate(s) for s in sites]


@router.patch("/{site_id}", response_model=SiteResponse)
async def update_site(
    site_id: str,
    body: SiteUpdate,
    api_key: ApiKey = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> SiteResponse:
    """Update a site's domain, config, or active status."""
    # Verify the API key belongs to this site
    if api_key.site_id != site_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key does not have access to this site",
        )

    stmt = select(Site).where(Site.id == site_id)
    result = await db.execute(stmt)
    site = result.scalar_one_or_none()

    if site is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )

    if body.domain is not None:
        site.domain = body.domain
    if body.config is not None:
        site.config = body.config.model_dump()
    if body.is_active is not None:
        site.is_active = body.is_active

    await db.flush()

    return SiteResponse.model_validate(site)
