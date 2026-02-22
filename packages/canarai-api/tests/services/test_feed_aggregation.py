"""Tests for feed aggregation service."""

import pytest
from httpx import AsyncClient


class TestAgentFeedEndpoint:
    """Integration tests via the rewritten feed endpoints."""

    @pytest.mark.asyncio
    async def test_get_agents_returns_200(self, client: AsyncClient):
        resp = await client.get("/v1/feed/agents")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_agents_has_required_fields(self, client: AsyncClient):
        resp = await client.get("/v1/feed/agents")
        body = resp.json()
        assert "version" in body
        assert "generated_at" in body
        assert "period" in body
        assert "min_sample_threshold" in body
        assert "agents" in body
        assert isinstance(body["agents"], list)

    @pytest.mark.asyncio
    async def test_get_agents_default_period_is_30_days(self, client: AsyncClient):
        resp = await client.get("/v1/feed/agents")
        assert resp.json()["period"] == "last_30_days"

    @pytest.mark.asyncio
    async def test_get_agents_custom_period(self, client: AsyncClient):
        resp = await client.get("/v1/feed/agents?period=last_7_days")
        assert resp.status_code == 200
        assert resp.json()["period"] == "last_7_days"

    @pytest.mark.asyncio
    async def test_get_agents_invalid_period(self, client: AsyncClient):
        resp = await client.get("/v1/feed/agents?period=last_999_days")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_get_agents_empty_when_no_data(self, client: AsyncClient):
        resp = await client.get("/v1/feed/agents")
        body = resp.json()
        assert body["agents"] == []

    @pytest.mark.asyncio
    async def test_get_agents_caches_snapshot(self, client: AsyncClient):
        """Second call should return cached data (same generated_at)."""
        resp1 = await client.get("/v1/feed/agents")
        resp2 = await client.get("/v1/feed/agents")
        assert resp1.json()["generated_at"] == resp2.json()["generated_at"]


class TestTrendsFeedEndpoint:
    @pytest.mark.asyncio
    async def test_get_trends_returns_200(self, client: AsyncClient):
        resp = await client.get("/v1/feed/trends")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_trends_has_required_fields(self, client: AsyncClient):
        resp = await client.get("/v1/feed/trends")
        body = resp.json()
        assert "version" in body
        assert "trends" in body
        assert "delivery_methods" in body
        assert isinstance(body["delivery_methods"], list)

    @pytest.mark.asyncio
    async def test_get_trends_invalid_period(self, client: AsyncClient):
        resp = await client.get("/v1/feed/trends?period=invalid")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_get_trends_empty_when_no_data(self, client: AsyncClient):
        resp = await client.get("/v1/feed/trends")
        body = resp.json()
        assert body["trends"]["total_agent_visits"] == 0
        assert body["delivery_methods"] == []
