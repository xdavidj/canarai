"""Webhook dispatch and alerting service.

Handles sending webhook payloads to registered endpoints with HMAC signing.
"""

import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from canarai.config import get_settings
from canarai.models.webhook import Webhook, WebhookDelivery

logger = logging.getLogger(__name__)


def sign_payload(payload: dict, secret: str) -> str:
    """Create HMAC-SHA256 signature for a webhook payload."""
    body = json.dumps(payload, sort_keys=True, default=str)
    return hmac.new(
        secret.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


async def get_webhooks_for_site(
    db: AsyncSession, site_id: str, event_type: str
) -> list[Webhook]:
    """Fetch all enabled webhooks for a site that are subscribed to the given event."""
    stmt = (
        select(Webhook)
        .where(Webhook.site_id == site_id)
        .where(Webhook.enabled.is_(True))
    )
    result = await db.execute(stmt)
    webhooks = list(result.scalars().all())

    # Filter by event type (stored as JSON list)
    return [w for w in webhooks if event_type in (w.events or [])]


async def dispatch_webhook(
    db: AsyncSession,
    webhook: Webhook,
    event_type: str,
    payload: dict,
) -> WebhookDelivery:
    """Send a webhook payload and record the delivery attempt."""
    settings = get_settings()
    signature = sign_payload(payload, webhook.secret)

    delivery = WebhookDelivery(
        id=str(uuid.uuid4()),
        webhook_id=webhook.id,
        event_type=event_type,
        payload=payload,
        attempt=1,
    )

    headers = {
        "Content-Type": "application/json",
        "X-Canarai-Signature": signature,
        "X-Canarai-Event": event_type,
        "X-Canarai-Delivery": delivery.id,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook.url,
                json=payload,
                headers=headers,
                timeout=settings.webhook_timeout_seconds,
            )
            delivery.status_code = response.status_code

            if response.status_code >= 400:
                logger.warning(
                    "Webhook delivery %s to %s returned %d",
                    delivery.id,
                    webhook.url,
                    response.status_code,
                )
                # Schedule retry
                delivery.next_retry_at = datetime.now(timezone.utc) + timedelta(
                    minutes=2**delivery.attempt
                )

    except httpx.TimeoutException:
        logger.error("Webhook delivery %s to %s timed out", delivery.id, webhook.url)
        delivery.status_code = None
        delivery.next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=2)

    except httpx.RequestError as exc:
        logger.error(
            "Webhook delivery %s to %s failed: %s", delivery.id, webhook.url, exc
        )
        delivery.status_code = None
        delivery.next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=2)

    db.add(delivery)
    return delivery


async def fire_webhooks_for_event(
    db: AsyncSession,
    site_id: str,
    event_type: str,
    payload: dict,
) -> list[WebhookDelivery]:
    """Find all relevant webhooks for a site/event and dispatch them."""
    webhooks = await get_webhooks_for_site(db, site_id, event_type)
    deliveries = []

    for webhook in webhooks:
        delivery = await dispatch_webhook(db, webhook, event_type, payload)
        deliveries.append(delivery)

    return deliveries


async def send_test_webhook(
    webhook: Webhook,
) -> tuple[bool, int | None, str | None]:
    """Send a test payload to a webhook URL.

    Returns (success, status_code, error_message).
    """
    settings = get_settings()
    test_payload = {
        "event": "webhook.test",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "message": "This is a test webhook delivery from canar.ai API.",
        },
    }

    signature = sign_payload(test_payload, webhook.secret)

    headers = {
        "Content-Type": "application/json",
        "X-Canarai-Signature": signature,
        "X-Canarai-Event": "webhook.test",
        "X-Canarai-Delivery": str(uuid.uuid4()),
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook.url,
                json=test_payload,
                headers=headers,
                timeout=settings.webhook_timeout_seconds,
            )
            success = response.status_code < 400
            return success, response.status_code, None

    except httpx.TimeoutException:
        return False, None, "Request timed out"

    except httpx.RequestError as exc:
        return False, None, str(exc)
