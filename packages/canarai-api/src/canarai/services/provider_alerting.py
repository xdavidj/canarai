"""Provider webhook alerting service.

Dispatches webhooks to agent providers when their agents fail tests.
Webhook payloads contain ZERO site-identifying information.
"""

import logging
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from canarai.config import get_settings
from canarai.models.agent_provider import AgentProvider
from canarai.services.alerting import sign_payload

logger = logging.getLogger(__name__)


async def get_provider_for_family(
    db: AsyncSession, agent_family: str
) -> AgentProvider | None:
    """Look up the registered provider for an agent family."""
    stmt = (
        select(AgentProvider)
        .where(AgentProvider.family == agent_family)
        .where(AgentProvider.is_active.is_(True))
        .where(AgentProvider.is_verified.is_(True))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def fire_provider_webhook(
    db: AsyncSession,
    agent_family: str,
    event_type: str,
    payload: dict,
) -> bool:
    """Dispatch a webhook to the provider for the given agent family.

    Returns True if sent successfully, False otherwise.
    Privacy: payload must contain ZERO site-identifying info (no site_id,
    page_url, ip_hash, visit_id).
    """
    provider = await get_provider_for_family(db, agent_family)
    if provider is None:
        return False

    if not provider.webhook_url or not provider.webhook_secret:
        return False

    # Check event subscription
    if provider.webhook_events and event_type not in provider.webhook_events:
        return False

    settings = get_settings()
    signature = sign_payload(payload, provider.webhook_secret)
    delivery_id = str(uuid.uuid4())

    headers = {
        "Content-Type": "application/json",
        "X-Canarai-Signature": signature,
        "X-Canarai-Event": event_type,
        "X-Canarai-Delivery": delivery_id,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                provider.webhook_url,
                json=payload,
                headers=headers,
                timeout=settings.webhook_timeout_seconds,
            )
            if response.status_code >= 400:
                logger.warning(
                    "Provider webhook %s to %s returned %d",
                    delivery_id,
                    provider.webhook_url,
                    response.status_code,
                )
                return False
            return True

    except httpx.TimeoutException:
        logger.error(
            "Provider webhook %s to %s timed out", delivery_id, provider.webhook_url
        )
        return False

    except httpx.RequestError as exc:
        logger.error(
            "Provider webhook %s to %s failed: %s",
            delivery_id,
            provider.webhook_url,
            exc,
        )
        return False
