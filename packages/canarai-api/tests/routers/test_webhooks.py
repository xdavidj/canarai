"""Tests for the /v1/webhooks endpoints."""

import pytest
import respx
from httpx import AsyncClient, Response

from canarai.routers.sites import _site_creation_limits


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_site(client: AsyncClient, domain: str) -> dict:
    _site_creation_limits.clear()
    resp = await client.post("/v1/sites", json={"domain": domain})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _auth(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}"}


def _webhook_body(site_id: str, url: str = "https://hooks.example.com/recv") -> dict:
    return {
        "site_id": site_id,
        "url": url,
        "events": ["visit.agent_detected", "test.critical_failure"],
    }


# ---------------------------------------------------------------------------
# POST /v1/webhooks — creation
# ---------------------------------------------------------------------------


class TestCreateWebhook:
    @pytest.mark.asyncio
    async def test_creates_webhook_with_valid_data(self, client: AsyncClient):
        data = await _create_site(client, "wh-create.com")
        resp = await client.post(
            "/v1/webhooks",
            json=_webhook_body(data["site"]["id"]),
            headers=_auth(data["api_key"]),
        )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_response_contains_webhook_fields(self, client: AsyncClient):
        data = await _create_site(client, "wh-fields.com")
        resp = await client.post(
            "/v1/webhooks",
            json=_webhook_body(data["site"]["id"]),
            headers=_auth(data["api_key"]),
        )
        body = resp.json()
        assert "id" in body
        assert "site_id" in body
        assert "url" in body
        assert "events" in body
        assert "enabled" in body
        assert "created_at" in body

    @pytest.mark.asyncio
    async def test_webhook_enabled_by_default(self, client: AsyncClient):
        data = await _create_site(client, "wh-enabled.com")
        resp = await client.post(
            "/v1/webhooks",
            json=_webhook_body(data["site"]["id"]),
            headers=_auth(data["api_key"]),
        )
        assert resp.json()["enabled"] is True

    @pytest.mark.asyncio
    async def test_ssrf_blocked_localhost_ip(self, client: AsyncClient):
        """POSTing http://127.0.0.1/hook must be rejected at validation time."""
        data = await _create_site(client, "wh-ssrf1.com")
        resp = await client.post(
            "/v1/webhooks",
            json=_webhook_body(data["site"]["id"], url="http://127.0.0.1/hook"),
            headers=_auth(data["api_key"]),
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_ssrf_blocked_private_ip(self, client: AsyncClient):
        """Private IP ranges must be rejected."""
        data = await _create_site(client, "wh-ssrf2.com")
        resp = await client.post(
            "/v1/webhooks",
            json=_webhook_body(data["site"]["id"], url="http://192.168.1.100/hook"),
            headers=_auth(data["api_key"]),
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_ssrf_blocked_cloud_metadata(self, client: AsyncClient):
        """Cloud metadata endpoint must be rejected."""
        data = await _create_site(client, "wh-ssrf3.com")
        resp = await client.post(
            "/v1/webhooks",
            json=_webhook_body(data["site"]["id"], url="http://169.254.169.254/latest/meta-data"),
            headers=_auth(data["api_key"]),
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_auth_required_no_header(self, client: AsyncClient):
        data = await _create_site(client, "wh-noauth.com")
        resp = await client.post(
            "/v1/webhooks",
            json=_webhook_body(data["site"]["id"]),
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_wrong_site_id_for_api_key_returns_403(self, client: AsyncClient):
        data_a = await _create_site(client, "wh-403-a.com")
        data_b = await _create_site(client, "wh-403-b.com")

        # Use data_a's API key but data_b's site_id
        resp = await client.post(
            "/v1/webhooks",
            json=_webhook_body(data_b["site"]["id"]),
            headers=_auth(data_a["api_key"]),
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /v1/webhooks/{webhook_id}/test
# ---------------------------------------------------------------------------


class TestTestWebhook:
    @pytest.mark.asyncio
    async def test_test_endpoint_requires_auth(self, client: AsyncClient):
        resp = await client.post("/v1/webhooks/some-id/test")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_nonexistent_webhook_returns_404(self, client: AsyncClient, site_with_key: dict):
        resp = await client.post(
            "/v1/webhooks/nonexistent-id/test",
            headers=_auth(site_with_key["api_key"]),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_test_endpoint_dispatches_and_returns_result(self, client: AsyncClient):
        data = await _create_site(client, "wh-test-dispatch.com")
        # Create webhook
        create_resp = await client.post(
            "/v1/webhooks",
            json=_webhook_body(data["site"]["id"], url="https://hooks.example.com/test-recv"),
            headers=_auth(data["api_key"]),
        )
        assert create_resp.status_code == 201
        webhook_id = create_resp.json()["id"]

        with respx.mock:
            respx.post("https://hooks.example.com/test-recv").mock(return_value=Response(200))
            resp = await client.post(
                f"/v1/webhooks/{webhook_id}/test",
                headers=_auth(data["api_key"]),
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "success" in body
        assert body["success"] is True

    @pytest.mark.asyncio
    async def test_test_endpoint_wrong_site_returns_403(self, client: AsyncClient):
        data_a = await _create_site(client, "wh-test-403a.com")
        data_b = await _create_site(client, "wh-test-403b.com")

        # Create webhook on site A
        create_resp = await client.post(
            "/v1/webhooks",
            json=_webhook_body(data_a["site"]["id"], url="https://hooks.example.com/site-a"),
            headers=_auth(data_a["api_key"]),
        )
        webhook_id = create_resp.json()["id"]

        # Try to test it with site B's API key
        resp = await client.post(
            f"/v1/webhooks/{webhook_id}/test",
            headers=_auth(data_b["api_key"]),
        )
        assert resp.status_code == 403
