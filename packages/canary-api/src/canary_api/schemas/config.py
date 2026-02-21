"""Schemas for the /v1/config endpoint."""

from pydantic import BaseModel, Field


class TestConfig(BaseModel):
    """Configuration for an individual canary test."""

    test_id: str
    version: str = "1.0"
    delivery_methods: list[str]
    payload_template: str | None = None


class ConfigResponse(BaseModel):
    """Configuration payload returned to the canary script."""

    site_key: str
    enabled: bool
    detection_threshold: float
    tests: list[TestConfig]
    delivery_methods: list[str]
    ingest_url: str
    script_version: str = "0.1.0"
