"""Schemas for webhook management endpoints."""

import ipaddress
from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, Field, HttpUrl, field_validator


class WebhookCreate(BaseModel):
    """Request body for creating a webhook."""

    site_id: str
    url: str = Field(min_length=1, max_length=2048)
    events: list[str] = Field(
        default_factory=lambda: ["visit.agent_detected", "test.critical_failure"]
    )

    @field_validator("url")
    @classmethod
    def validate_webhook_url(cls, v: str) -> str:
        """Block private IPs, cloud metadata endpoints, and non-HTTP schemes (SSRF prevention)."""
        parsed = urlparse(v)
        if parsed.scheme not in ("https", "http"):
            raise ValueError("Webhook URL must use http:// or https://")
        hostname = parsed.hostname
        if not hostname:
            raise ValueError("Webhook URL must have a valid hostname")
        # Block private/internal IP addresses
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise ValueError("Webhook URL must not point to private/internal addresses")
        except ValueError as e:
            # If it's not an IP address, that's fine (it's a hostname) - re-raise other errors
            if "does not appear to be an IPv4 or IPv6 address" not in str(e):
                raise
        # Block cloud metadata endpoints
        blocked = {"169.254.169.254", "metadata.google.internal", "100.100.100.200"}
        if hostname in blocked:
            raise ValueError("Webhook URL points to a blocked metadata endpoint")
        return v


class WebhookResponse(BaseModel):
    """Response for a single webhook."""

    id: str
    site_id: str
    url: str
    events: list
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class WebhookTestResponse(BaseModel):
    """Response from testing a webhook."""

    success: bool
    status_code: int | None = None
    error: str | None = None


class WebhookDeliveryResponse(BaseModel):
    """Response for a webhook delivery record."""

    id: str
    webhook_id: str
    event_type: str
    payload: dict
    status_code: int | None
    attempt: int
    next_retry_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
