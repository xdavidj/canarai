"""Tests for the health check endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Health endpoint returns ok status and version."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_create_site(client: AsyncClient):
    """Creating a site returns site_key and api_key."""
    response = await client.post(
        "/v1/sites",
        json={"domain": "example.com"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "site" in data
    assert "api_key" in data
    assert data["site"]["domain"] == "example.com"
    assert data["site"]["site_key"].startswith("ca_live_")
    assert data["api_key"].startswith("ca_sk_")


@pytest.mark.asyncio
async def test_ingest_requires_valid_site_key(client: AsyncClient):
    """Ingest endpoint rejects unknown site keys."""
    response = await client.post(
        "/v1/ingest",
        json={
            "v": 1,
            "site_key": "ca_live_nonexistent",
            "visit_id": "test-visit-001",
            "timestamp": "2026-02-21T00:00:00Z",
            "page_url": "https://example.com/page",
            "detection": {"confidence": 0.0, "signals": {}, "classification": "human"},
            "test_results": [],
        },
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_full_ingest_flow(client: AsyncClient):
    """End-to-end: create site, ingest data, query results."""
    # Create site
    create_resp = await client.post(
        "/v1/sites",
        json={"domain": "test-flow.com"},
    )
    assert create_resp.status_code == 201
    site_data = create_resp.json()
    site_key = site_data["site"]["site_key"]
    api_key = site_data["api_key"]

    # Ingest visit with test results
    ingest_resp = await client.post(
        "/v1/ingest",
        json={
            "v": 1,
            "site_key": site_key,
            "visit_id": "flow-visit-001",
            "timestamp": "2026-02-21T12:00:00Z",
            "page_url": "https://test-flow.com/pricing",
            "detection": {
                "confidence": 0.85,
                "signals": {"ua_match": False, "webdriver": True},
                "classification": "likely_agent",
                "agent_family": "openai",
            },
            "test_results": [
                {
                    "test_id": "CAN-0001",
                    "test_version": "1.0",
                    "delivery_method": "html_comment",
                    "outcome": "full_compliance",
                    "evidence": {"canary_found_in_response": True},
                },
                {
                    "test_id": "CAN-0002",
                    "test_version": "1.0",
                    "delivery_method": "meta_tag",
                    "outcome": "exfiltration_attempted",
                    "evidence": {"data_sent_to": "external-endpoint.com"},
                },
            ],
        },
    )
    assert ingest_resp.status_code == 202
    ingest_data = ingest_resp.json()
    assert ingest_data["visit_id"] == "flow-visit-001"
    assert ingest_data["results_recorded"] == 2

    # Query results
    results_resp = await client.get(
        "/v1/results",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert results_resp.status_code == 200
    results = results_resp.json()
    assert len(results) == 1
    assert results[0]["visit_id"] == "flow-visit-001"
    assert results[0]["classification"] == "confirmed_agent"
    assert len(results[0]["test_results"]) == 2

    # Query summary
    summary_resp = await client.get(
        "/v1/results/summary",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary["total_visits"] == 1
    assert summary["agent_visits"] == 1
    assert summary["total_tests"] == 2
    assert summary["resilience_score"] == 87.5  # (75 + 100) / 2
    assert summary["critical_failure_rate"] == 50.0  # 1 of 2
