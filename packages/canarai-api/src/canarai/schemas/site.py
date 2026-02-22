"""Schemas for site management endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class SiteConfig(BaseModel):
    """Site configuration object."""

    enabled_tests: list[str] = Field(
        default_factory=lambda: ["CAN-0001", "CAN-0002", "CAN-0003"]
    )
    detection_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    delivery_methods: list[str] = Field(
        default_factory=lambda: ["html_comment", "meta_tag", "http_header"]
    )


class SiteCreate(BaseModel):
    """Request body for creating a new site."""

    domain: str = Field(min_length=1, max_length=255)
    config: SiteConfig = Field(default_factory=SiteConfig)
    environment: str = Field(default="live", pattern=r"^(live|test)$")


class SiteUpdate(BaseModel):
    """Request body for updating a site."""

    domain: str | None = Field(default=None, min_length=1, max_length=255)
    config: SiteConfig | None = None
    is_active: bool | None = None


class SiteResponse(BaseModel):
    """Response for a single site."""

    id: str
    site_key: str
    domain: str
    config: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SiteCreateResponse(BaseModel):
    """Response after creating a site, includes the raw API key (only shown once)."""

    site: SiteResponse
    api_key: str
    api_key_prefix: str
