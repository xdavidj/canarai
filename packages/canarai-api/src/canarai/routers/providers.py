"""Provider registry endpoints — agent providers can register and monitor their agents."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from canarai.config import get_settings
from canarai.dependencies import get_db, verify_provider_key
from canarai.models.agent_provider import AgentProvider, ProviderApiKey
from canarai.models.test_result import TestResult
from canarai.models.visit import Visit
from canarai.schemas.provider import (
    ProviderCreateResponse,
    ProviderDashboard,
    ProviderDashboardOutcomes,
    ProviderRegister,
    ProviderResponse,
    ProviderUpdate,
)
from canarai.services.provider_alerting import get_provider_for_family
from canarai.services.rate_limit import InMemoryRateLimiter

router = APIRouter(prefix="/v1/providers", tags=["providers"])

_registration_limiter = InMemoryRateLimiter(
    max_requests=get_settings().provider_rate_limit_per_hour,
    window_seconds=3600,
)


def _generate_provider_key() -> str:
    """Generate a provider API key with ca_pk_ prefix."""
    return f"ca_pk_{secrets.token_hex(24)}"


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


@router.post("", status_code=status.HTTP_201_CREATED)
async def register_provider(
    body: ProviderRegister,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ProviderCreateResponse:
    """Register as a provider for an agent family.

    Rate limited. Returns a provider API key (shown only once).
    """
    client_ip = request.client.host if request.client else "unknown"
    if not _registration_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later.",
        )

    # Check if family is already registered
    existing = await get_provider_for_family(db, body.family)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Agent family '{body.family}' is already registered",
        )

    # Check inactive/unverified providers too
    stmt = select(AgentProvider).where(AgentProvider.family == body.family)
    result = await db.execute(stmt)
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Agent family '{body.family}' is already registered",
        )

    # Generate webhook secret if webhook_url provided
    webhook_secret = secrets.token_hex(32) if body.webhook_url else None

    provider = AgentProvider(
        family=body.family,
        name=body.name,
        contact_email=body.contact_email,
        webhook_url=body.webhook_url,
        webhook_secret=webhook_secret,
        webhook_events=body.webhook_events,
    )
    db.add(provider)
    await db.flush()

    # Generate API key
    raw_key = _generate_provider_key()
    key_hash = _hash_key(raw_key)
    prefix = raw_key[:10]

    provider_key = ProviderApiKey(
        provider_id=provider.id,
        key_hash=key_hash,
        prefix=prefix,
    )
    db.add(provider_key)
    await db.flush()

    return ProviderCreateResponse(
        provider=ProviderResponse.model_validate(provider),
        api_key=raw_key,
        api_key_prefix=prefix,
    )


@router.get("/me", response_model=ProviderResponse)
async def get_own_profile(
    provider: AgentProvider = Depends(verify_provider_key),
) -> ProviderResponse:
    """Get your own provider profile."""
    return ProviderResponse.model_validate(provider)


@router.patch("/me", response_model=ProviderResponse)
async def update_provider(
    body: ProviderUpdate,
    provider: AgentProvider = Depends(verify_provider_key),
    db: AsyncSession = Depends(get_db),
) -> ProviderResponse:
    """Update your webhook settings and profile."""
    if body.name is not None:
        provider.name = body.name
    if body.contact_email is not None:
        provider.contact_email = body.contact_email
    if body.webhook_url is not None:
        provider.webhook_url = body.webhook_url
        # Generate new webhook secret when URL changes
        if not provider.webhook_secret:
            provider.webhook_secret = secrets.token_hex(32)
    if body.webhook_events is not None:
        provider.webhook_events = body.webhook_events

    await db.flush()
    return ProviderResponse.model_validate(provider)


@router.get("/me/dashboard", response_model=ProviderDashboard)
async def get_dashboard(
    period: str = "last_30_days",
    provider: AgentProvider = Depends(verify_provider_key),
    db: AsyncSession = Depends(get_db),
) -> ProviderDashboard:
    """Aggregate stats for your agent family.

    Privacy: never returns site_id, page_url, ip_hash, or visit_id.
    Scoped to the provider's own agent family only.
    """
    if period not in ("last_7_days", "last_30_days", "last_90_days"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid period. Use: last_7_days, last_30_days, last_90_days",
        )

    days_map = {"last_7_days": 7, "last_30_days": 30, "last_90_days": 90}
    time_cutoff = datetime.now(timezone.utc) - timedelta(days=days_map[period])

    # Aggregate query scoped to provider's family
    stmt = (
        select(
            func.count(Visit.id.distinct()).label("visit_count"),
            func.count(TestResult.id).label("test_count"),
            func.round(func.avg(TestResult.score), 2).label("resilience_score"),
            func.sum(case((TestResult.outcome == "exfiltration_attempted", 1), else_=0)).label("exfiltration_count"),
            func.sum(case((TestResult.outcome == "full_compliance", 1), else_=0)).label("full_compliance_count"),
            func.sum(case((TestResult.outcome == "partial_compliance", 1), else_=0)).label("partial_compliance_count"),
            func.sum(case((TestResult.outcome == "acknowledged", 1), else_=0)).label("acknowledged_count"),
            func.sum(case((TestResult.outcome == "ignored", 1), else_=0)).label("ignored_count"),
        )
        .select_from(Visit)
        .join(TestResult, TestResult.visit_id == Visit.visit_id)
        .where(Visit.agent_family == provider.family)
        .where(Visit.classification.in_(["confirmed_agent", "likely_agent"]))
        .where(Visit.timestamp >= time_cutoff)
    )

    result = await db.execute(stmt)
    row = result.one()

    test_count = row.test_count or 0
    exfil = row.exfiltration_count or 0
    critical_rate = round(exfil / test_count, 4) if test_count > 0 else 0.0

    return ProviderDashboard(
        family=provider.family,
        period=period,
        total_visits=row.visit_count or 0,
        total_tests=test_count,
        resilience_score=float(row.resilience_score or 0),
        critical_failure_rate=critical_rate,
        outcomes=ProviderDashboardOutcomes(
            exfiltration_attempted=exfil,
            full_compliance=row.full_compliance_count or 0,
            partial_compliance=row.partial_compliance_count or 0,
            acknowledged=row.acknowledged_count or 0,
            ignored=row.ignored_count or 0,
        ),
    )


@router.post("/me/webhook/test")
async def test_webhook(
    provider: AgentProvider = Depends(verify_provider_key),
) -> dict:
    """Test webhook delivery to your registered URL."""
    if not provider.webhook_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No webhook URL configured",
        )

    import httpx
    from canarai.services.alerting import sign_payload

    settings = get_settings()
    test_payload = {
        "event": "webhook.test",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "message": "This is a test webhook delivery from canar.ai provider API.",
            "family": provider.family,
        },
    }

    signature = sign_payload(test_payload, provider.webhook_secret)
    headers = {
        "Content-Type": "application/json",
        "X-Canarai-Signature": signature,
        "X-Canarai-Event": "webhook.test",
        "X-Canarai-Delivery": str(uuid.uuid4()),
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                provider.webhook_url,
                json=test_payload,
                headers=headers,
                timeout=settings.webhook_timeout_seconds,
            )
            return {
                "success": response.status_code < 400,
                "status_code": response.status_code,
                "error": None,
            }
    except httpx.TimeoutException:
        return {"success": False, "status_code": None, "error": "Request timed out"}
    except httpx.RequestError as exc:
        return {"success": False, "status_code": None, "error": str(exc)}
