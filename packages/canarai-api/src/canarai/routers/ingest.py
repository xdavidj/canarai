"""Ingest endpoint - hot path for receiving script results."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from canarai.dependencies import get_db, verify_site_key
from canarai.models.site import Site
from canarai.models.test_result import TestResult
from canarai.models.visit import Visit
from canarai.schemas.ingest import IngestPayload, IngestResponse
from canarai.services.alerting import fire_webhooks_for_event
from canarai.services.detection import classify_visit, hash_ip
from canarai.services.provider_alerting import fire_provider_webhook
from canarai.services.scoring import score_outcome

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["ingest"])


async def fire_webhooks_background(
    site_id: str,
    classification: str,
    agent_family: str | None,
    visit_id: str,
    page_url: str,
    confidence: float,
    has_critical_failure: bool,
    exfiltration_test_ids: list[str],
) -> None:
    """Dispatch webhooks in the background after the response has been sent."""
    from canarai.db.engine import get_session

    async for db in get_session():
        try:
            if classification in ("confirmed_agent", "likely_agent"):
                await fire_webhooks_for_event(
                    db,
                    site_id,
                    "visit.agent_detected",
                    {
                        "event": "visit.agent_detected",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "data": {
                            "visit_id": visit_id,
                            "classification": classification,
                            "agent_family": agent_family,
                            "page_url": page_url,
                            "confidence": confidence,
                        },
                    },
                )

            if has_critical_failure:
                await fire_webhooks_for_event(
                    db,
                    site_id,
                    "test.critical_failure",
                    {
                        "event": "test.critical_failure",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "data": {
                            "visit_id": visit_id,
                            "classification": classification,
                            "agent_family": agent_family,
                            "page_url": page_url,
                            "tests_with_exfiltration": exfiltration_test_ids,
                        },
                    },
                )

            # Fire provider webhook on critical failures (privacy-safe: no site info)
            if agent_family and has_critical_failure:
                await fire_provider_webhook(
                    db,
                    agent_family,
                    "agent.critical_failure",
                    {
                        "event": "agent.critical_failure",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "data": {
                            "agent_family": agent_family,
                            "classification": classification,
                            "tests_failed": exfiltration_test_ids,
                            "total_critical_failures": len(exfiltration_test_ids),
                        },
                    },
                )

            await db.commit()
        except Exception:
            logger.exception("Background webhook dispatch failed for visit %s", visit_id)
            await db.rollback()


@router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest(
    payload: IngestPayload,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> IngestResponse:
    """Receive detection and test result data from the canary script.

    This is the hot path - called on every monitored page visit.
    """
    # 1. Validate site_key
    site = await verify_site_key(payload.site_key, db)

    # 2. Extract server-side signals
    user_agent = request.headers.get("user-agent")
    client_ip = request.client.host if request.client else None
    ip_hashed = hash_ip(client_ip) if client_ip else None

    headers_dict = dict(request.headers)

    # 3. Server-side classification
    classification, agent_family, confidence = classify_visit(
        client_detection=payload.detection,
        user_agent=user_agent,
        headers=headers_dict,
        ip=client_ip,
    )

    # 4. Create Visit record
    visit = Visit(
        visit_id=payload.visit_id,
        site_id=site.id,
        page_url=payload.page_url,
        timestamp=datetime.fromisoformat(payload.timestamp),
        user_agent=user_agent,
        detection={
            "client": payload.detection.model_dump(),
            "server_confidence": confidence,
        },
        classification=classification,
        agent_family=agent_family,
        ip_hash=ip_hashed,
    )
    db.add(visit)

    # 5. Create TestResult records with scores
    results_recorded = 0
    has_critical_failure = False

    for tr in payload.test_results:
        outcome_score = score_outcome(tr.outcome)

        test_result = TestResult(
            visit_id=payload.visit_id,
            test_id=tr.test_id,
            test_version=tr.test_version,
            delivery_method=tr.delivery_method,
            outcome=tr.outcome,
            score=outcome_score,
            evidence=tr.evidence,
            injected_at=tr.injected_at,
            observed_at=tr.observed_at,
        )
        db.add(test_result)
        results_recorded += 1

        if tr.outcome == "exfiltration_attempted":
            has_critical_failure = True

    # Flush to ensure records are persisted before webhook dispatch
    await db.flush()

    # 6. Fire webhooks in background (non-blocking) if thresholds are met
    if classification in ("confirmed_agent", "likely_agent") or has_critical_failure:
        exfiltration_test_ids = [
            tr.test_id
            for tr in payload.test_results
            if tr.outcome == "exfiltration_attempted"
        ]
        background_tasks.add_task(
            fire_webhooks_background,
            site_id=site.id,
            classification=classification,
            agent_family=agent_family,
            visit_id=payload.visit_id,
            page_url=payload.page_url,
            confidence=confidence,
            has_critical_failure=has_critical_failure,
            exfiltration_test_ids=exfiltration_test_ids,
        )

    # Build response with X-Canarai-* headers
    response_data = IngestResponse(
        status="accepted",
        visit_id=payload.visit_id,
        results_recorded=results_recorded,
    )

    headers = {
        "X-Canarai-Tested": "true",
        "X-Canarai-Classification": classification,
        "X-Canarai-Tests-Run": str(results_recorded),
    }
    if has_critical_failure:
        headers["X-Canarai-Critical-Failure"] = "true"
    if agent_family:
        headers["X-Canarai-Agent-Family"] = agent_family

    return JSONResponse(
        content=response_data.model_dump(),
        status_code=status.HTTP_202_ACCEPTED,
        headers=headers,
    )
