"""Admin endpoints for zero-day vector management."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from canarai.dependencies import get_db, verify_api_key
from canarai.models.agent_session import AgentSession
from canarai.models.zero_day_push import ZeroDayPush

router = APIRouter(prefix="/v1/admin", tags=["admin"])


# ── Request/Response Schemas ─────────────────────────────────────────


class ZeroDayCreateRequest(BaseModel):
    """Request body for creating a zero-day push."""

    test_id: str = Field(max_length=16, pattern=r"^CAN-\d{4}$")
    surface: str = Field(default="web", max_length=16)
    description: str = Field(max_length=512)
    expires_hours: int | None = Field(default=None, ge=1, le=720)
    site_id: str | None = Field(default=None, max_length=36)


class ZeroDayResponse(BaseModel):
    """Response body for a zero-day push."""

    id: str
    test_id: str
    surface: str
    description: str
    is_active: bool
    agents_reached: int
    expires_at: str | None
    activated_at: str
    deactivated_at: str | None


class EscalationStatsResponse(BaseModel):
    """Escalation funnel statistics."""

    total_sessions: int
    funnel: list[dict]


# ── Endpoints ────────────────────────────────────────────────────────


@router.post("/zero-day", response_model=ZeroDayResponse, status_code=status.HTTP_201_CREATED)
async def create_zero_day(
    body: ZeroDayCreateRequest,
    db: AsyncSession = Depends(get_db),
    _api_key=Depends(verify_api_key),
) -> ZeroDayResponse:
    """Push a new zero-day vector. It will be served at highest priority to all agents."""
    expires_at = None
    if body.expires_hours:
        expires_at = datetime.now(timezone.utc) + timedelta(hours=body.expires_hours)

    push = ZeroDayPush(
        test_id=body.test_id,
        surface=body.surface,
        description=body.description,
        site_id=body.site_id,
        expires_at=expires_at,
        is_active=True,
        agents_reached=0,
        activated_at=datetime.now(timezone.utc),
    )
    db.add(push)
    await db.flush()

    return ZeroDayResponse(
        id=push.id,
        test_id=push.test_id,
        surface=push.surface,
        description=push.description,
        is_active=push.is_active,
        agents_reached=push.agents_reached,
        expires_at=push.expires_at.isoformat() if push.expires_at else None,
        activated_at=push.activated_at.isoformat(),
        deactivated_at=None,
    )


@router.get("/zero-day", response_model=list[ZeroDayResponse])
async def list_zero_days(
    db: AsyncSession = Depends(get_db),
    _api_key=Depends(verify_api_key),
) -> list[ZeroDayResponse]:
    """List all zero-day pushes (active and inactive)."""
    stmt = select(ZeroDayPush).order_by(ZeroDayPush.activated_at.desc())
    result = await db.execute(stmt)
    pushes = result.scalars().all()

    return [
        ZeroDayResponse(
            id=p.id,
            test_id=p.test_id,
            surface=p.surface,
            description=p.description,
            is_active=p.is_active,
            agents_reached=p.agents_reached,
            expires_at=p.expires_at.isoformat() if p.expires_at else None,
            activated_at=p.activated_at.isoformat(),
            deactivated_at=p.deactivated_at.isoformat() if p.deactivated_at else None,
        )
        for p in pushes
    ]


@router.delete("/zero-day/{push_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_zero_day(
    push_id: str,
    db: AsyncSession = Depends(get_db),
    _api_key=Depends(verify_api_key),
) -> None:
    """Manually deactivate a zero-day push."""
    stmt = select(ZeroDayPush).where(ZeroDayPush.id == push_id)
    result = await db.execute(stmt)
    push = result.scalar_one_or_none()

    if push is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zero-day push not found",
        )

    push.is_active = False
    push.deactivated_at = datetime.now(timezone.utc)
    await db.flush()
