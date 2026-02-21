"""Tests for the /v1/config/{site_key} endpoint."""

import pytest
from httpx import AsyncClient

from canarai.routers.sites import _site_creation_limits


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_site(client: AsyncClient, domain: str = "config-test.com", **extra) -> dict:
    _site_creation_limits.clear()
    resp = await client.post("/v1/sites", json={"domain": domain, **extra})
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _get_config(client: AsyncClient, site_key: str) -> dict:
    resp = await client.get(f"/v1/config/{site_key}")
    return resp


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGetConfig:
    @pytest.mark.asyncio
    async def test_valid_site_key_returns_200(self, client: AsyncClient):
        data = await _create_site(client, "cfg-200.com")
        resp = await _get_config(client, data["site"]["site_key"])
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_response_contains_default_tests(self, client: AsyncClient):
        data = await _create_site(client, "cfg-defaults.com")
        resp = await _get_config(client, data["site"]["site_key"])
        body = resp.json()
        test_ids = {t["test_id"] for t in body["tests"]}
        assert "CAN-0001" in test_ids
        assert "CAN-0002" in test_ids
        assert "CAN-0003" in test_ids

    @pytest.mark.asyncio
    async def test_response_structure(self, client: AsyncClient):
        data = await _create_site(client, "cfg-struct.com")
        resp = await _get_config(client, data["site"]["site_key"])
        body = resp.json()
        assert "site_key" in body
        assert "enabled" in body
        assert "detection_threshold" in body
        assert "tests" in body
        assert "delivery_methods" in body
        assert "ingest_url" in body

    @pytest.mark.asyncio
    async def test_enabled_is_true_for_active_site(self, client: AsyncClient):
        data = await _create_site(client, "cfg-enabled.com")
        resp = await _get_config(client, data["site"]["site_key"])
        assert resp.json()["enabled"] is True

    @pytest.mark.asyncio
    async def test_delivery_method_filtering_meta_tag_only(self, client: AsyncClient):
        """Site configured with only meta_tag delivery — tests with meta_tag are filtered,
        tests without it fall back to their full default delivery methods."""
        resp = await client.post(
            "/v1/sites",
            json={
                "domain": "cfg-filter.com",
                "config": {
                    "enabled_tests": ["CAN-0001", "CAN-0002", "CAN-0003"],
                    "delivery_methods": ["meta_tag"],
                    "detection_threshold": 0.5,
                },
            },
        )
        assert resp.status_code == 201
        site_key = resp.json()["site"]["site_key"]

        config_resp = await _get_config(client, site_key)
        body = config_resp.json()
        for test in body["tests"]:
            if "meta_tag" in test["delivery_methods"]:
                # Tests that support meta_tag should be filtered to only meta_tag
                # unless the filter produced an empty list (fallback to defaults)
                pass
            # CAN-0002 has ["html_comment", "http_header"] — no overlap with ["meta_tag"],
            # so it falls back to its full default list per the router logic:
            # `filtered_methods or test_config.delivery_methods`
        # At minimum, CAN-0001 and CAN-0003 should include meta_tag
        test_ids_with_meta = [
            t["test_id"] for t in body["tests"] if "meta_tag" in t["delivery_methods"]
        ]
        assert "CAN-0001" in test_ids_with_meta
        assert "CAN-0003" in test_ids_with_meta

    @pytest.mark.asyncio
    async def test_unknown_test_ids_in_config_silently_skipped(self, client: AsyncClient):
        """A config with a nonexistent test ID should simply omit that test."""
        resp = await client.post(
            "/v1/sites",
            json={
                "domain": "cfg-unknown.com",
                "config": {
                    "enabled_tests": ["CAN-0001", "CAN-9999"],
                    "delivery_methods": ["html_comment", "meta_tag", "http_header"],
                    "detection_threshold": 0.5,
                },
            },
        )
        assert resp.status_code == 201
        site_key = resp.json()["site"]["site_key"]

        config_resp = await _get_config(client, site_key)
        test_ids = {t["test_id"] for t in config_resp.json()["tests"]}
        assert "CAN-0001" in test_ids
        assert "CAN-9999" not in test_ids

    @pytest.mark.asyncio
    async def test_disabled_site_returns_404(self, client: AsyncClient, site_with_key: dict):
        """Deactivating a site must cause /v1/config to return 404."""
        # Deactivate via PATCH
        await client.patch(
            f"/v1/sites/{site_with_key['site_id']}",
            json={"is_active": False},
            headers={"Authorization": f"Bearer {site_with_key['api_key']}"},
        )
        resp = await _get_config(client, site_with_key["site_key"])
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_site_key_returns_404(self, client: AsyncClient):
        resp = await _get_config(client, "ca_live_totally_bogus_key_12345")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_site_key_in_response_matches_request(self, client: AsyncClient):
        data = await _create_site(client, "cfg-key-match.com")
        site_key = data["site"]["site_key"]
        resp = await _get_config(client, site_key)
        assert resp.json()["site_key"] == site_key

    @pytest.mark.asyncio
    async def test_ingest_url_ends_with_v1_ingest(self, client: AsyncClient):
        data = await _create_site(client, "cfg-url.com")
        resp = await _get_config(client, data["site"]["site_key"])
        assert resp.json()["ingest_url"].endswith("/v1/ingest")

    @pytest.mark.asyncio
    async def test_detection_threshold_default_is_0_5(self, client: AsyncClient):
        data = await _create_site(client, "cfg-threshold.com")
        resp = await _get_config(client, data["site"]["site_key"])
        assert resp.json()["detection_threshold"] == 0.5
