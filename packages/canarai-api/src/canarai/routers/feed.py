"""Feed endpoints — real aggregate data replacing stubs."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from canarai.config import get_settings
from canarai.dependencies import get_db
from canarai.schemas.feed import AgentFeedResponse, TrendsFeedResponse
from canarai.services.feed_aggregation import get_or_compute_snapshot
from canarai.services.rate_limit import InMemoryRateLimiter

router = APIRouter(prefix="/v1/feed", tags=["feed"])

_feed_limiter = InMemoryRateLimiter(
    max_requests=get_settings().feed_rate_limit_per_minute,
    window_seconds=60,
)


def _check_rate_limit(request: Request) -> None:
    """Enforce per-IP rate limit on feed endpoints."""
    client_ip = request.client.host if request.client else "unknown"
    if not _feed_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later.",
        )


@router.get("/agents", response_model=AgentFeedResponse)
async def get_agent_feed(
    request: Request,
    period: str = "last_30_days",
    db: AsyncSession = Depends(get_db),
) -> AgentFeedResponse:
    """Hosted intelligence feed of known AI agent behaviors.

    Returns aggregate, privacy-safe data about AI agent families and their
    prompt injection resilience. Minimum sample thresholds enforced.
    """
    _check_rate_limit(request)

    if period not in ("last_7_days", "last_30_days", "last_90_days"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid period. Use: last_7_days, last_30_days, last_90_days",
        )

    data = await get_or_compute_snapshot(db, "agents", period)
    return AgentFeedResponse(**data)


@router.get("/trends", response_model=TrendsFeedResponse)
async def get_trends(
    request: Request,
    period: str = "last_30_days",
    db: AsyncSession = Depends(get_db),
) -> TrendsFeedResponse:
    """Trend data for AI agent activity across all monitored sites.

    Returns aggregated, anonymized trend data. No site-identifying
    information is ever included.
    """
    _check_rate_limit(request)

    if period not in ("last_7_days", "last_30_days", "last_90_days"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid period. Use: last_7_days, last_30_days, last_90_days",
        )

    data = await get_or_compute_snapshot(db, "trends", period)
    return TrendsFeedResponse(**data)
