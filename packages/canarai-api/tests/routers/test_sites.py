"""Tests for the /v1/sites endpoints."""

import pytest
from httpx import AsyncClient

from canarai.routers.sites import _site_creation_limits


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_site(client: AsyncClient, domain: str = "sites-test.com", **extra) -> dict:
    resp = await client.post("/v1/sites", json={"domain": domain, **extra})
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# POST /v1/sites — creation
# ---------------------------------------------------------------------------


class TestCreateSite:
    @pytest.mark.asyncio
    async def test_creates_site_with_live_prefix_by_default(self, client: AsyncClient):
        _site_creation_limits.clear()
        data = await _create_site(client, "live-prefix.com")
        assert data["site"]["site_key"].startswith("ca_live_")

    @pytest.mark.asyncio
    async def test_creates_site_with_live_prefix_explicit(self, client: AsyncClient):
        _site_creation_limits.clear()
        resp = await client.post(
            "/v1/sites", json={"domain": "live-explicit.com", "environment": "live"}
        )
        assert resp.status_code == 201
        assert resp.json()["site"]["site_key"].startswith("ca_live_")

    @pytest.mark.asyncio
    async def test_creates_site_with_test_prefix(self, client: AsyncClient):
        _site_creation_limits.clear()
        resp = await client.post(
            "/v1/sites", json={"domain": "test-env.com", "environment": "test"}
        )
        assert resp.status_code == 201
        assert resp.json()["site"]["site_key"].startswith("ca_test_")

    @pytest.mark.asyncio
    async def test_api_key_starts_with_ca_sk(self, client: AsyncClient):
        _site_creation_limits.clear()
        data = await _create_site(client, "api-key-prefix.com")
        assert data["api_key"].startswith("ca_sk_")

    @pytest.mark.asyncio
    async def test_response_contains_api_key_prefix(self, client: AsyncClient):
        _site_creation_limits.clear()
        data = await _create_site(client, "prefix-check.com")
        assert "api_key_prefix" in data
        assert data["api_key"].startswith(data["api_key_prefix"])

    @pytest.mark.asyncio
    async def test_response_contains_site_object(self, client: AsyncClient):
        _site_creation_limits.clear()
        data = await _create_site(client, "site-obj.com")
        site = data["site"]
        assert "id" in site
        assert "site_key" in site
        assert "domain" in site
        assert site["domain"] == "site-obj.com"

    @pytest.mark.asyncio
    async def test_site_is_active_by_default(self, client: AsyncClient):
        _site_creation_limits.clear()
        data = await _create_site(client, "active-default.com")
        assert data["site"]["is_active"] is True

    @pytest.mark.asyncio
    async def test_missing_domain_returns_422(self, client: AsyncClient):
        _site_creation_limits.clear()
        resp = await client.post("/v1/sites", json={})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_environment_returns_422(self, client: AsyncClient):
        _site_creation_limits.clear()
        resp = await client.post(
            "/v1/sites", json={"domain": "bad-env.com", "environment": "staging"}
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_rate_limit_5_then_429(self, client: AsyncClient):
        """6th creation from same IP within window must return 429."""
        _site_creation_limits.clear()
        for i in range(5):
            resp = await client.post(
                "/v1/sites", json={"domain": f"rate-limit-{i}.com"}
            )
            assert resp.status_code == 201, f"Request {i + 1} should succeed, got {resp.status_code}"

        resp = await client.post("/v1/sites", json={"domain": "rate-limit-6.com"})
        assert resp.status_code == 429


# ---------------------------------------------------------------------------
# GET /v1/sites — listing
# ---------------------------------------------------------------------------


class TestListSites:
    @pytest.mark.asyncio
    async def test_requires_auth_header(self, client: AsyncClient):
        """Without Authorization header the field validator returns 422."""
        resp = await client.get("/v1/sites")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_api_key_returns_401(self, client: AsyncClient):
        resp = await client.get(
            "/v1/sites",
            headers={"Authorization": "Bearer ca_sk_totally_wrong_key"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_auth_returns_200(self, client: AsyncClient, site_with_key: dict):
        resp = await client.get(
            "/v1/sites",
            headers={"Authorization": f"Bearer {site_with_key['api_key']}"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_list(self, client: AsyncClient, site_with_key: dict):
        resp = await client.get(
            "/v1/sites",
            headers={"Authorization": f"Bearer {site_with_key['api_key']}"},
        )
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_returns_own_site(self, client: AsyncClient, site_with_key: dict):
        resp = await client.get(
            "/v1/sites",
            headers={"Authorization": f"Bearer {site_with_key['api_key']}"},
        )
        site_ids = [s["id"] for s in resp.json()]
        assert site_with_key["site_id"] in site_ids


# ---------------------------------------------------------------------------
# PATCH /v1/sites/{site_id}
# ---------------------------------------------------------------------------


class TestUpdateSite:
    @pytest.mark.asyncio
    async def test_patch_domain_succeeds(self, client: AsyncClient, site_with_key: dict):
        resp = await client.patch(
            f"/v1/sites/{site_with_key['site_id']}",
            json={"domain": "updated-domain.com"},
            headers={"Authorization": f"Bearer {site_with_key['api_key']}"},
        )
        assert resp.status_code == 200
        assert resp.json()["domain"] == "updated-domain.com"

    @pytest.mark.asyncio
    async def test_patch_wrong_api_key_returns_403(self, client: AsyncClient, site_with_key: dict):
        _site_creation_limits.clear()
        # Create a second site to get a different API key
        other = await client.post("/v1/sites", json={"domain": "other-site.com"})
        other_key = other.json()["api_key"]

        resp = await client.patch(
            f"/v1/sites/{site_with_key['site_id']}",
            json={"domain": "hacked.com"},
            headers={"Authorization": f"Bearer {other_key}"},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_patch_nonexistent_site_returns_404(self, client: AsyncClient, site_with_key: dict):
        resp = await client.patch(
            "/v1/sites/nonexistent-site-id",
            json={"domain": "ghost.com"},
            headers={"Authorization": f"Bearer {site_with_key['api_key']}"},
        )
        assert resp.status_code in (403, 404)

    @pytest.mark.asyncio
    async def test_patch_is_active_false_deactivates_site(
        self, client: AsyncClient, site_with_key: dict
    ):
        resp = await client.patch(
            f"/v1/sites/{site_with_key['site_id']}",
            json={"is_active": False},
            headers={"Authorization": f"Bearer {site_with_key['api_key']}"},
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    @pytest.mark.asyncio
    async def test_patch_requires_auth(self, client: AsyncClient, site_with_key: dict):
        resp = await client.patch(
            f"/v1/sites/{site_with_key['site_id']}",
            json={"domain": "no-auth.com"},
        )
        assert resp.status_code == 422
