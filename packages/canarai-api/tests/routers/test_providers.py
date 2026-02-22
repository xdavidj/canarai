"""Tests for the /v1/providers endpoints."""

import pytest
from httpx import AsyncClient


async def _register_provider(
    client: AsyncClient,
    family: str = "testbot",
    name: str = "Test Bot Inc",
    contact_email: str = "security@testbot.ai",
    webhook_url: str | None = None,
) -> dict:
    """Register a provider and return the full response JSON."""
    body = {
        "family": family,
        "name": name,
        "contact_email": contact_email,
    }
    if webhook_url is not None:
        body["webhook_url"] = webhook_url
    resp = await client.post("/v1/providers", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestProviderRegistration:
    @pytest.mark.asyncio
    async def test_register_returns_201(self, client: AsyncClient):
        resp = await client.post(
            "/v1/providers",
            json={
                "family": "myagent",
                "name": "My Agent Corp",
                "contact_email": "team@myagent.ai",
            },
        )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_register_returns_api_key(self, client: AsyncClient):
        data = await _register_provider(client, family="keytest")
        assert "api_key" in data
        assert data["api_key"].startswith("ca_pk_")
        assert "api_key_prefix" in data

    @pytest.mark.asyncio
    async def test_register_returns_provider_profile(self, client: AsyncClient):
        data = await _register_provider(client, family="profiletest")
        provider = data["provider"]
        assert provider["family"] == "profiletest"
        assert provider["name"] == "Test Bot Inc"
        assert provider["is_verified"] is False
        assert provider["is_active"] is True

    @pytest.mark.asyncio
    async def test_duplicate_family_returns_409(self, client: AsyncClient):
        await _register_provider(client, family="dupfamily")
        resp = await client.post(
            "/v1/providers",
            json={
                "family": "dupfamily",
                "name": "Another Corp",
                "contact_email": "other@test.ai",
            },
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_invalid_family_format_returns_422(self, client: AsyncClient):
        resp = await client.post(
            "/v1/providers",
            json={
                "family": "Invalid Family!",
                "name": "Bad Corp",
                "contact_email": "bad@test.ai",
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_webhook_url_ssrf_blocked(self, client: AsyncClient):
        resp = await client.post(
            "/v1/providers",
            json={
                "family": "ssrftest",
                "name": "SSRF Corp",
                "contact_email": "ssrf@test.ai",
                "webhook_url": "http://169.254.169.254/latest/meta-data/",
            },
        )
        assert resp.status_code == 422


class TestProviderAuth:
    @pytest.mark.asyncio
    async def test_get_me_without_auth_returns_401(self, client: AsyncClient):
        resp = await client.get("/v1/providers/me")
        assert resp.status_code in (401, 422)

    @pytest.mark.asyncio
    async def test_get_me_with_valid_key(self, client: AsyncClient):
        data = await _register_provider(client, family="authtest")
        api_key = data["api_key"]
        resp = await client.get(
            "/v1/providers/me",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert resp.status_code == 200
        assert resp.json()["family"] == "authtest"

    @pytest.mark.asyncio
    async def test_get_me_with_invalid_key_returns_401(self, client: AsyncClient):
        resp = await client.get(
            "/v1/providers/me",
            headers={"Authorization": "Bearer ca_pk_invalid_key_here"},
        )
        assert resp.status_code == 401


class TestProviderUpdate:
    @pytest.mark.asyncio
    async def test_patch_name(self, client: AsyncClient):
        data = await _register_provider(client, family="patchtest")
        api_key = data["api_key"]
        resp = await client.patch(
            "/v1/providers/me",
            json={"name": "Updated Name"},
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_patch_webhook_url(self, client: AsyncClient):
        data = await _register_provider(client, family="webhookpatch")
        api_key = data["api_key"]
        resp = await client.patch(
            "/v1/providers/me",
            json={"webhook_url": "https://hooks.example.com/canarai"},
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert resp.status_code == 200
        assert resp.json()["webhook_url"] == "https://hooks.example.com/canarai"


class TestProviderDashboard:
    @pytest.mark.asyncio
    async def test_dashboard_returns_200(self, client: AsyncClient):
        data = await _register_provider(client, family="dashtest")
        api_key = data["api_key"]
        resp = await client.get(
            "/v1/providers/me/dashboard",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_dashboard_returns_correct_family(self, client: AsyncClient):
        data = await _register_provider(client, family="dashfamily")
        api_key = data["api_key"]
        resp = await client.get(
            "/v1/providers/me/dashboard",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        body = resp.json()
        assert body["family"] == "dashfamily"
        assert body["period"] == "last_30_days"

    @pytest.mark.asyncio
    async def test_dashboard_empty_when_no_data(self, client: AsyncClient):
        data = await _register_provider(client, family="emptydata")
        api_key = data["api_key"]
        resp = await client.get(
            "/v1/providers/me/dashboard",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        body = resp.json()
        assert body["total_visits"] == 0
        assert body["total_tests"] == 0

    @pytest.mark.asyncio
    async def test_dashboard_invalid_period(self, client: AsyncClient):
        data = await _register_provider(client, family="badperiod")
        api_key = data["api_key"]
        resp = await client.get(
            "/v1/providers/me/dashboard?period=last_999_days",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert resp.status_code == 400


class TestWebhookTest:
    @pytest.mark.asyncio
    async def test_webhook_test_no_url_returns_400(self, client: AsyncClient):
        data = await _register_provider(client, family="nowebhook")
        api_key = data["api_key"]
        resp = await client.post(
            "/v1/providers/me/webhook/test",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert resp.status_code == 400
