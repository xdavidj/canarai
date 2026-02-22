"""Feed aggregation service — computes and caches aggregate feed data.

Privacy constraint: Public data is aggregate-only. Never SELECT site_id,
page_url, ip_hash, or visit-level data in any public output. site_count
is used for threshold checks only and suppressed if below minimum.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from canarai.config import get_settings
from canarai.models.feed_snapshot import AgentFeedSnapshot
from canarai.models.test_result import TestResult
from canarai.models.visit import Visit

logger = logging.getLogger(__name__)

# Per-snapshot-type locks to prevent thundering herd
_compute_locks: dict[str, asyncio.Lock] = {}


def _get_lock(snapshot_type: str) -> asyncio.Lock:
    if snapshot_type not in _compute_locks:
        _compute_locks[snapshot_type] = asyncio.Lock()
    return _compute_locks[snapshot_type]


async def get_or_compute_snapshot(
    db: AsyncSession,
    snapshot_type: str,
    period: str = "last_30_days",
) -> dict:
    """Return a fresh feed snapshot, recomputing if stale.

    Uses asyncio.Lock per snapshot_type so only one coroutine computes
    at a time (thundering herd protection).
    """
    settings = get_settings()
    staleness = timedelta(seconds=settings.feed_snapshot_staleness_seconds)
    cutoff = datetime.now(timezone.utc) - staleness

    # Check for fresh cached snapshot
    stmt = (
        select(AgentFeedSnapshot)
        .where(AgentFeedSnapshot.snapshot_type == snapshot_type)
        .where(AgentFeedSnapshot.period == period)
        .where(AgentFeedSnapshot.computed_at >= cutoff)
        .order_by(AgentFeedSnapshot.computed_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    snapshot = result.scalar_one_or_none()

    if snapshot is not None:
        return snapshot.data

    # Acquire lock to prevent concurrent recomputation
    lock = _get_lock(f"{snapshot_type}:{period}")
    async with lock:
        # Double-check after acquiring lock (another coroutine may have computed)
        result = await db.execute(stmt)
        snapshot = result.scalar_one_or_none()
        if snapshot is not None:
            return snapshot.data

        # Compute fresh data
        if snapshot_type == "agents":
            data = await _compute_agents_snapshot(db, period)
        elif snapshot_type == "trends":
            data = await _compute_trends_snapshot(db, period)
        else:
            data = {}

        # Save snapshot
        new_snapshot = AgentFeedSnapshot(
            snapshot_type=snapshot_type,
            period=period,
            data=data,
        )
        db.add(new_snapshot)
        await db.flush()

        return data


def _period_to_days(period: str) -> int:
    """Convert period string to days."""
    mapping = {
        "last_7_days": 7,
        "last_30_days": 30,
        "last_90_days": 90,
    }
    return mapping.get(period, 30)


async def _compute_agents_snapshot(db: AsyncSession, period: str) -> dict:
    """Compute aggregate agent family data.

    Privacy-safe: never returns site_id, page_url, ip_hash.
    site_count used for threshold check only, suppressed if < 5.
    """
    settings = get_settings()
    days = _period_to_days(period)
    time_cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Aggregate query — privacy-safe (no site_id, page_url, ip_hash in output)
    stmt = (
        select(
            Visit.agent_family,
            func.count(Visit.id.distinct()).label("visit_count"),
            func.count(Visit.site_id.distinct()).label("site_count"),
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
        .where(Visit.agent_family.isnot(None))
        .where(Visit.classification.in_(["confirmed_agent", "likely_agent"]))
        .where(Visit.timestamp >= time_cutoff)
        .group_by(Visit.agent_family)
        .having(func.count(Visit.id.distinct()) >= settings.feed_min_visits)
        .having(func.count(Visit.site_id.distinct()) >= settings.feed_min_sites)
    )

    result = await db.execute(stmt)
    rows = result.all()

    agents = []
    for row in rows:
        test_count = row.test_count or 0
        exfil = row.exfiltration_count or 0
        critical_failure_rate = round(exfil / test_count, 4) if test_count > 0 else 0.0

        agents.append({
            "family": row.agent_family,
            "visit_count": row.visit_count,
            "test_count": test_count,
            "resilience_score": float(row.resilience_score or 0),
            "critical_failure_rate": critical_failure_rate,
            "outcomes": {
                "exfiltration_attempted": exfil,
                "full_compliance": row.full_compliance_count or 0,
                "partial_compliance": row.partial_compliance_count or 0,
                "acknowledged": row.acknowledged_count or 0,
                "ignored": row.ignored_count or 0,
            },
            # Suppress site_count if fewer than 5 (privacy)
            "contributing_sites": row.site_count if row.site_count >= 5 else None,
        })

    return {
        "version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period": period,
        "min_sample_threshold": settings.feed_min_visits,
        "agents": agents,
    }


async def _compute_trends_snapshot(db: AsyncSession, period: str) -> dict:
    """Compute aggregate trend data across all monitored sites."""
    settings = get_settings()
    days = _period_to_days(period)
    time_cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Total agent visits
    visit_stmt = (
        select(
            func.count(Visit.id).label("total_agent_visits"),
            func.count(Visit.agent_family.distinct()).label("unique_families"),
        )
        .where(Visit.classification.in_(["confirmed_agent", "likely_agent"]))
        .where(Visit.timestamp >= time_cutoff)
    )
    visit_result = await db.execute(visit_stmt)
    visit_row = visit_result.one()

    # Overall resilience
    score_stmt = (
        select(
            func.round(func.avg(TestResult.score), 2).label("avg_score"),
        )
        .select_from(Visit)
        .join(TestResult, TestResult.visit_id == Visit.visit_id)
        .where(Visit.classification.in_(["confirmed_agent", "likely_agent"]))
        .where(Visit.timestamp >= time_cutoff)
    )
    score_result = await db.execute(score_stmt)
    score_row = score_result.one()

    # Most common delivery methods with failures
    dm_stmt = (
        select(
            TestResult.delivery_method,
            func.count(TestResult.id).label("count"),
            func.sum(case((TestResult.outcome == "exfiltration_attempted", 1), else_=0)).label("exfil_count"),
        )
        .select_from(Visit)
        .join(TestResult, TestResult.visit_id == Visit.visit_id)
        .where(Visit.classification.in_(["confirmed_agent", "likely_agent"]))
        .where(Visit.timestamp >= time_cutoff)
        .group_by(TestResult.delivery_method)
        .order_by(func.count(TestResult.id).desc())
        .limit(10)
    )
    dm_result = await db.execute(dm_stmt)
    dm_rows = dm_result.all()

    delivery_methods = [
        {
            "method": row.delivery_method,
            "test_count": row.count,
            "exfiltration_count": row.exfil_count or 0,
        }
        for row in dm_rows
    ]

    total_tests = sum(dm["test_count"] for dm in delivery_methods)
    total_exfil = sum(dm["exfiltration_count"] for dm in delivery_methods)
    critical_rate = round(total_exfil / total_tests, 4) if total_tests > 0 else 0.0

    return {
        "version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period": period,
        "trends": {
            "total_agent_visits": visit_row.total_agent_visits or 0,
            "unique_agent_families": visit_row.unique_families or 0,
            "average_resilience_score": float(score_row.avg_score or 0),
            "critical_failure_rate": critical_rate,
        },
        "delivery_methods": delivery_methods,
    }
