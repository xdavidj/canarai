"""Schemas for the /v1/config endpoint."""

from pydantic import BaseModel, Field


class TestConfig(BaseModel):
    """Configuration for an individual canary test."""

    test_id: str
    version: str = "1.0"
    delivery_methods: list[str]
    payload_template: str | None = None
    priority: int = Field(default=50, description="Priority for escalation (lower = higher priority). Zero-days use 0.")
    is_zero_day: bool = Field(default=False, description="Whether this test was pushed as a zero-day vector.")


class ConfigResponse(BaseModel):
    """Configuration payload returned to the canary script."""

    site_key: str
    enabled: bool
    detection_threshold: float
    tests: list[TestConfig]
    delivery_methods: list[str]
    ingest_url: str
    script_version: str = "0.1.0"
    escalation_level: int = Field(default=0, description="Current escalation level (visit count) for this agent session.")
    agent_session_id: str | None = Field(default=None, description="Agent session ID for tracking escalation state.")
