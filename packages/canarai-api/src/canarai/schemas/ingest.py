"""Schemas for the /v1/ingest endpoint."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DetectionData(BaseModel):
    """Client-side detection results."""

    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    signals: dict = Field(default_factory=dict)
    classification: Literal[
        "human", "suspected_agent", "likely_agent", "confirmed_agent"
    ] = "human"
    agent_family: str | None = None


class TestResultData(BaseModel):
    """Individual test result from client-side execution."""

    test_id: str = Field(pattern=r"^CAN-\d{4}$")
    test_version: str = "1.0"
    delivery_method: str = Field(max_length=64)
    outcome: Literal[
        "exfiltration_attempted",
        "full_compliance",
        "partial_compliance",
        "acknowledged",
        "ignored",
    ]
    evidence: dict = Field(default_factory=dict)
    injected_at: datetime | None = None
    observed_at: datetime | None = None


class IngestPayload(BaseModel):
    """Payload sent by the canary script to the ingest endpoint."""

    v: int = 1
    site_key: str = Field(max_length=64)
    visit_id: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    timestamp: str = Field(max_length=64)
    page_url: str = Field(max_length=2048)
    detection: DetectionData
    test_results: list[TestResultData] = Field(default_factory=list, max_length=50)
    agent_session_id: str | None = Field(default=None, max_length=36, description="Agent session ID from escalation tracking.")


class IngestResponse(BaseModel):
    """Response returned from the ingest endpoint."""

    status: str = "accepted"
    visit_id: str
    results_recorded: int
