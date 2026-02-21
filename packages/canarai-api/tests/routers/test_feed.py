"""Tests for the /v1/feed endpoints."""

import pytest
from httpx import AsyncClient


class TestAgentFeed:
    @pytest.mark.asyncio
    async def test_get_agents_returns_200(self, client: AsyncClient):
        resp = await client.get("/v1/feed/agents")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_agents_contains_agents_list(self, client: AsyncClient):
        resp = await client.get("/v1/feed/agents")
        body = resp.json()
        assert "agents" in body
        assert isinstance(body["agents"], list)
        assert len(body["agents"]) > 0

    @pytest.mark.asyncio
    async def test_get_agents_contains_expected_families(self, client: AsyncClient):
        resp = await client.get("/v1/feed/agents")
        families = {a["family"] for a in resp.json()["agents"]}
        assert "openai" in families
        assert "anthropic" in families

    @pytest.mark.asyncio
    async def test_get_agents_has_version_field(self, client: AsyncClient):
        resp = await client.get("/v1/feed/agents")
        assert "version" in resp.json()


class TestTrendsFeed:
    @pytest.mark.asyncio
    async def test_get_trends_returns_200(self, client: AsyncClient):
        resp = await client.get("/v1/feed/trends")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_trends_contains_trends_dict(self, client: AsyncClient):
        resp = await client.get("/v1/feed/trends")
        body = resp.json()
        assert "trends" in body
        assert isinstance(body["trends"], dict)

    @pytest.mark.asyncio
    async def test_get_trends_has_version_field(self, client: AsyncClient):
        resp = await client.get("/v1/feed/trends")
        assert "version" in resp.json()

    @pytest.mark.asyncio
    async def test_get_trends_has_period_field(self, client: AsyncClient):
        resp = await client.get("/v1/feed/trends")
        assert "period" in resp.json()
