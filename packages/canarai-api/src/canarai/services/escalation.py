"""Escalation service — progressive escalation and zero-day push logic."""

import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from canarai.models.agent_session import AgentSession
from canarai.models.zero_day_push import ZeroDayPush


def compute_fingerprint(ip: str, ua: str, site_id: str) -> str:
    """Compute a fingerprint hash from IP + User-Agent + site_id.

    Agents don't keep cookies but present consistent IP/UA within a crawl.
    Returns the first 16 hex chars of SHA256(ip + ua + site_id).
    """
    raw = f"{ip}{ua}{site_id}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


async def get_or_create_agent_session(
    db: AsyncSession,
    site_id: str,
    fingerprint: str,
    surface: str = "web",
) -> AgentSession:
    """Get or create an agent session, incrementing visit_count on retrieval."""
    stmt = (
        select(AgentSession)
        .where(AgentSession.site_id == site_id)
        .where(AgentSession.fingerprint_hash == fingerprint)
        .where(AgentSession.surface == surface)
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if session is not None:
        session.visit_count += 1
        session.last_seen_at = datetime.now(timezone.utc)
        await db.flush()
        return session

    # Create new session
    session = AgentSession(
        site_id=site_id,
        fingerprint_hash=fingerprint,
        surface=surface,
        vectors_seen=[],
        visit_count=1,
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    db.add(session)
    await db.flush()
    return session


async def get_active_zero_days(
    db: AsyncSession,
    site_id: str | None = None,
    surface: str = "web",
) -> list[ZeroDayPush]:
    """Get active zero-day pushes, filtering out expired/fulfilled ones."""
    stmt = (
        select(ZeroDayPush)
        .where(ZeroDayPush.is_active.is_(True))
        .where(ZeroDayPush.surface == surface)
    )
    if site_id:
        # Include global (null site_id) and site-specific
        stmt = stmt.where(
            (ZeroDayPush.site_id == site_id) | (ZeroDayPush.site_id.is_(None))
        )

    result = await db.execute(stmt)
    zero_days = list(result.scalars().all())

    # Filter out expired and fulfilled zero-days
    now = datetime.now(timezone.utc)
    valid = []
    for zd in zero_days:
        if zd.expires_at and zd.expires_at < now:
            continue
        if zd.sample_count >= zd.sample_target:
            continue
        valid.append(zd)

    return valid


async def check_zero_day_expiry(db: AsyncSession) -> int:
    """Auto-deprioritize expired or fulfilled zero-days. Returns count of deprioritized."""
    now = datetime.now(timezone.utc)

    # Find active zero-days that are expired or fulfilled
    stmt = (
        select(ZeroDayPush)
        .where(ZeroDayPush.is_active.is_(True))
    )
    result = await db.execute(stmt)
    active = result.scalars().all()

    count = 0
    for zd in active:
        should_deprioritize = False
        if zd.expires_at and zd.expires_at < now:
            should_deprioritize = True
        if zd.sample_count >= zd.sample_target:
            should_deprioritize = True

        if should_deprioritize:
            zd.is_active = False
            zd.deprioritized_at = now
            count += 1

    if count > 0:
        await db.flush()

    return count


async def increment_zero_day_sample(db: AsyncSession, push_id: str) -> None:
    """Increment the sample count for a zero-day push."""
    stmt = (
        update(ZeroDayPush)
        .where(ZeroDayPush.id == push_id)
        .values(sample_count=ZeroDayPush.sample_count + 1)
    )
    await db.execute(stmt)


async def update_session_vectors(
    db: AsyncSession,
    session: AgentSession,
    test_ids: list[str],
) -> None:
    """Update the vectors_seen list on an agent session."""
    current = session.vectors_seen if isinstance(session.vectors_seen, list) else []
    merged = list(set(current + test_ids))
    session.vectors_seen = merged
    await db.flush()
