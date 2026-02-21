"""Results query endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from canary_api.dependencies import get_db, verify_api_key
from canary_api.models.api_key import ApiKey
from canary_api.models.test_result import TestResult
from canary_api.models.visit import Visit
from canary_api.schemas.results import (
    ResultsSummary,
    TestResultResponse,
    VisitWithResults,
)
from canary_api.services.scoring import (
    aggregate_outcome_counts,
    calculate_critical_failure_rate,
    calculate_resilience_score,
)

router = APIRouter(prefix="/v1/results", tags=["results"])


@router.get("", response_model=list[VisitWithResults])
async def get_results(
    api_key: ApiKey = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
    site_id: str | None = Query(default=None),
    test_id: str | None = Query(default=None),
    classification: str | None = Query(default=None),
    outcome: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[VisitWithResults]:
    """Query visits and their test results with optional filters."""
    # Enforce tenant scoping: reject cross-tenant access attempts
    if site_id and site_id != api_key.site_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key does not have access to this site",
        )
    effective_site_id = api_key.site_id

    stmt = (
        select(Visit)
        .options(selectinload(Visit.test_results))
        .where(Visit.site_id == effective_site_id)
        .order_by(Visit.timestamp.desc())
    )

    if classification:
        stmt = stmt.where(Visit.classification == classification)
    if date_from:
        stmt = stmt.where(Visit.timestamp >= date_from)
    if date_to:
        stmt = stmt.where(Visit.timestamp <= date_to)

    # If filtering by test_id or outcome, join on test_results
    if test_id or outcome:
        stmt = stmt.join(Visit.test_results)
        if test_id:
            stmt = stmt.where(TestResult.test_id == test_id)
        if outcome:
            stmt = stmt.where(TestResult.outcome == outcome)

    stmt = stmt.offset(offset).limit(limit)

    result = await db.execute(stmt)
    visits = result.unique().scalars().all()

    return [
        VisitWithResults(
            id=v.id,
            visit_id=v.visit_id,
            site_id=v.site_id,
            page_url=v.page_url,
            timestamp=v.timestamp,
            user_agent=v.user_agent,
            classification=v.classification,
            agent_family=v.agent_family,
            test_results=[
                TestResultResponse.model_validate(tr) for tr in v.test_results
            ],
            created_at=v.created_at,
        )
        for v in visits
    ]


@router.get("/summary", response_model=ResultsSummary)
async def get_results_summary(
    api_key: ApiKey = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
    site_id: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
) -> ResultsSummary:
    """Get aggregate statistics across test results."""
    # Enforce tenant scoping: reject cross-tenant access attempts
    if site_id and site_id != api_key.site_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key does not have access to this site",
        )
    effective_site_id = api_key.site_id

    # Base visit query
    visit_filter = Visit.site_id == effective_site_id
    if date_from:
        visit_filter = visit_filter & (Visit.timestamp >= date_from)
    if date_to:
        visit_filter = visit_filter & (Visit.timestamp <= date_to)

    # Total visits
    total_stmt = select(func.count(Visit.id)).where(visit_filter)
    total_result = await db.execute(total_stmt)
    total_visits = total_result.scalar() or 0

    # Agent visits (not human)
    agent_stmt = (
        select(func.count(Visit.id))
        .where(visit_filter)
        .where(Visit.classification != "human")
    )
    agent_result = await db.execute(agent_stmt)
    agent_visits = agent_result.scalar() or 0

    human_visits = total_visits - agent_visits

    # Test results for this site
    tr_stmt = (
        select(TestResult)
        .join(Visit, TestResult.visit_id == Visit.visit_id)
        .where(visit_filter)
    )
    tr_result = await db.execute(tr_stmt)
    test_results = list(tr_result.scalars().all())

    total_tests = len(test_results)
    scores = [tr.score for tr in test_results]
    outcomes = [tr.outcome for tr in test_results]

    resilience_score = calculate_resilience_score(scores)
    critical_failure_rate = calculate_critical_failure_rate(outcomes)
    outcome_counts = aggregate_outcome_counts(outcomes)

    # Top agent families
    family_stmt = (
        select(Visit.agent_family, func.count(Visit.id).label("count"))
        .where(visit_filter)
        .where(Visit.agent_family.isnot(None))
        .group_by(Visit.agent_family)
        .order_by(func.count(Visit.id).desc())
        .limit(10)
    )
    family_result = await db.execute(family_stmt)
    top_families = [
        {"family": row.agent_family, "count": row.count}
        for row in family_result.all()
    ]

    return ResultsSummary(
        total_visits=total_visits,
        agent_visits=agent_visits,
        human_visits=human_visits,
        total_tests=total_tests,
        resilience_score=resilience_score,
        critical_failure_rate=critical_failure_rate,
        outcomes=outcome_counts,
        top_agent_families=top_families,
    )
