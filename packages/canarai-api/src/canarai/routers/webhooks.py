"""Webhook management endpoints."""

import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from canarai.dependencies import get_db, verify_api_key
from canarai.models.api_key import ApiKey
from canarai.models.webhook import Webhook
from canarai.schemas.webhook import (
    WebhookCreate,
    WebhookResponse,
    WebhookTestResponse,
)
from canarai.services.alerting import send_test_webhook

router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])


@router.post(
    "",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_webhook(
    body: WebhookCreate,
    api_key: ApiKey = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> WebhookResponse:
    """Register a new webhook for a site."""
    # Verify API key has access to this site
    if api_key.site_id != body.site_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key does not have access to this site",
        )

    webhook = Webhook(
        id=str(uuid.uuid4()),
        site_id=body.site_id,
        url=body.url,
        events=body.events,
        secret=secrets.token_hex(32),
    )
    db.add(webhook)
    await db.flush()

    return WebhookResponse.model_validate(webhook)


@router.post("/{webhook_id}/test", response_model=WebhookTestResponse)
async def test_webhook(
    webhook_id: str,
    api_key: ApiKey = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> WebhookTestResponse:
    """Send a test payload to a webhook URL."""
    stmt = select(Webhook).where(Webhook.id == webhook_id)
    result = await db.execute(stmt)
    webhook = result.scalar_one_or_none()

    if webhook is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    if api_key.site_id != webhook.site_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key does not have access to this webhook",
        )

    success, status_code, error = await send_test_webhook(webhook)

    return WebhookTestResponse(
        success=success,
        status_code=status_code,
        error=error,
    )
