"""Schemas for results query and response."""

from datetime import datetime

from pydantic import BaseModel, Field


class ResultsQuery(BaseModel):
    """Query parameters for filtering results."""

    site_id: str | None = None
    test_id: str | None = None
    classification: str | None = None
    outcome: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class TestResultResponse(BaseModel):
    """Individual test result in response."""

    id: str
    visit_id: str
    test_id: str
    test_version: str
    delivery_method: str
    outcome: str
    score: int
    evidence: dict
    injected_at: datetime | None
    observed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class VisitWithResults(BaseModel):
    """Visit with its test results."""

    id: str
    visit_id: str
    site_id: str
    page_url: str
    timestamp: datetime
    user_agent: str | None
    classification: str
    agent_family: str | None
    test_results: list[TestResultResponse]
    created_at: datetime

    model_config = {"from_attributes": True}


class ResultsSummary(BaseModel):
    """Aggregate stats across results."""

    total_visits: int
    agent_visits: int
    human_visits: int
    total_tests: int
    resilience_score: float = Field(
        description="Average score across all tests (0-100, higher = more vulnerable)"
    )
    critical_failure_rate: float = Field(
        description="Percentage of tests resulting in exfiltration_attempted"
    )
    outcomes: dict[str, int] = Field(
        description="Count of each outcome type"
    )
    top_agent_families: list[dict] = Field(
        description="Most common agent families detected"
    )
