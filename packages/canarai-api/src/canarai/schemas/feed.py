"""Schemas for feed endpoints."""

from datetime import datetime

from pydantic import BaseModel


class OutcomeCounts(BaseModel):
    """Outcome breakdown for an agent family."""

    exfiltration_attempted: int = 0
    full_compliance: int = 0
    partial_compliance: int = 0
    acknowledged: int = 0
    ignored: int = 0


class AgentFamilyScore(BaseModel):
    """Aggregate scores for a single agent family."""

    family: str
    visit_count: int
    test_count: int
    resilience_score: float
    critical_failure_rate: float
    outcomes: OutcomeCounts
    contributing_sites: int | None = None


class AgentFeedResponse(BaseModel):
    """Response for GET /v1/feed/agents."""

    version: str
    generated_at: str
    period: str
    min_sample_threshold: int
    agents: list[AgentFamilyScore]


class DeliveryMethodStats(BaseModel):
    """Stats for a delivery method in trends."""

    method: str
    test_count: int
    exfiltration_count: int


class TrendsData(BaseModel):
    """Aggregate trend data."""

    total_agent_visits: int = 0
    unique_agent_families: int = 0
    average_resilience_score: float = 0.0
    critical_failure_rate: float = 0.0


class TrendsFeedResponse(BaseModel):
    """Response for GET /v1/feed/trends."""

    version: str
    generated_at: str
    period: str
    trends: TrendsData
    delivery_methods: list[DeliveryMethodStats]
