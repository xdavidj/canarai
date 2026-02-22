"""Schemas for provider registration and management endpoints."""

import ipaddress
from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator


class ProviderRegister(BaseModel):
    """Request body for registering a new provider."""

    family: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=255)
    contact_email: str = Field(min_length=5, max_length=320)
    webhook_url: str | None = Field(default=None, max_length=2048)
    webhook_events: list[str] | None = Field(
        default_factory=lambda: ["agent.critical_failure"]
    )

    @field_validator("webhook_url")
    @classmethod
    def validate_webhook_url(cls, v: str | None) -> str | None:
        """Block private IPs, cloud metadata endpoints, and non-HTTP schemes (SSRF prevention)."""
        if v is None:
            return v
        parsed = urlparse(v)
        if parsed.scheme not in ("https", "http"):
            raise ValueError("Webhook URL must use http:// or https://")
        hostname = parsed.hostname
        if not hostname:
            raise ValueError("Webhook URL must have a valid hostname")
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise ValueError("Webhook URL must not point to private/internal addresses")
        except ValueError as e:
            if "does not appear to be an IPv4 or IPv6 address" not in str(e):
                raise
        blocked = {"169.254.169.254", "metadata.google.internal", "100.100.100.200"}
        if hostname in blocked:
            raise ValueError("Webhook URL points to a blocked metadata endpoint")
        return v


class ProviderUpdate(BaseModel):
    """Request body for updating provider settings."""

    name: str | None = Field(default=None, max_length=255)
    contact_email: str | None = Field(default=None, max_length=320)
    webhook_url: str | None = Field(default=None, max_length=2048)
    webhook_events: list[str] | None = None

    @field_validator("webhook_url")
    @classmethod
    def validate_webhook_url(cls, v: str | None) -> str | None:
        """Same SSRF validation as registration."""
        if v is None:
            return v
        parsed = urlparse(v)
        if parsed.scheme not in ("https", "http"):
            raise ValueError("Webhook URL must use http:// or https://")
        hostname = parsed.hostname
        if not hostname:
            raise ValueError("Webhook URL must have a valid hostname")
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise ValueError("Webhook URL must not point to private/internal addresses")
        except ValueError as e:
            if "does not appear to be an IPv4 or IPv6 address" not in str(e):
                raise
        blocked = {"169.254.169.254", "metadata.google.internal", "100.100.100.200"}
        if hostname in blocked:
            raise ValueError("Webhook URL points to a blocked metadata endpoint")
        return v


class ProviderResponse(BaseModel):
    """Public provider profile response."""

    id: str
    family: str
    name: str
    contact_email: str
    webhook_url: str | None
    webhook_events: list | None
    is_verified: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProviderCreateResponse(BaseModel):
    """Response from provider registration (includes raw API key)."""

    provider: ProviderResponse
    api_key: str
    api_key_prefix: str


class ProviderDashboardOutcomes(BaseModel):
    """Outcome counts for the provider dashboard."""

    exfiltration_attempted: int = 0
    full_compliance: int = 0
    partial_compliance: int = 0
    acknowledged: int = 0
    ignored: int = 0


class ProviderDashboard(BaseModel):
    """Aggregate stats for a provider's agent family."""

    family: str
    period: str
    total_visits: int
    total_tests: int
    resilience_score: float
    critical_failure_rate: float
    outcomes: ProviderDashboardOutcomes
