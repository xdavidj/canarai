"""Tests for application-level middleware and configuration in canarai.main."""

import json
import uuid

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------


class TestSecurityHeaders:
    @pytest.mark.asyncio
    async def test_x_content_type_options_present(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.headers.get("x-content-type-options") == "nosniff"

    @pytest.mark.asyncio
    async def test_x_frame_options_present(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.headers.get("x-frame-options") == "DENY"

    @pytest.mark.asyncio
    async def test_cache_control_present(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.headers.get("cache-control") == "no-store"

    @pytest.mark.asyncio
    async def test_security_headers_on_post_endpoint(self, client: AsyncClient):
        """Security headers should be present on all responses, including 4xx."""
        resp = await client.post(
            "/v1/ingest",
            json={
                "v": 1,
                "site_key": "ca_live_nosuchsite12345678",
                "visit_id": "hdr-visit-001",
                "timestamp": "2026-02-21T00:00:00Z",
                "page_url": "https://example.com/",
                "detection": {"confidence": 0.0, "signals": {}, "classification": "human"},
            },
        )
        assert "x-content-type-options" in resp.headers
        assert "x-frame-options" in resp.headers
        assert "cache-control" in resp.headers


# ---------------------------------------------------------------------------
# CORS headers
# ---------------------------------------------------------------------------


class TestCORSHeaders:
    @pytest.mark.asyncio
    async def test_cors_headers_on_options_request(self, client: AsyncClient):
        resp = await client.options(
            "/v1/ingest",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        # CORS preflight should be handled (200 or 204)
        assert resp.status_code in (200, 204)
        assert "access-control-allow-origin" in resp.headers

    @pytest.mark.asyncio
    async def test_cors_allow_origin_present_on_get(self, client: AsyncClient):
        resp = await client.get(
            "/health",
            headers={"Origin": "https://example.com"},
        )
        assert "access-control-allow-origin" in resp.headers


# ---------------------------------------------------------------------------
# text/plain middleware
# ---------------------------------------------------------------------------


class TestTextPlainMiddleware:
    @pytest.mark.asyncio
    async def test_ingest_with_text_plain_returns_non_500(self, client: AsyncClient):
        """The middleware rewrites text/plain -> application/json for /v1/ingest.
        Even if the site key is invalid we should get 404 not 422/415."""
        payload = {
            "v": 1,
            "site_key": "ca_live_textplain12345678",
            "visit_id": f"tp-{uuid.uuid4().hex[:10]}",
            "timestamp": "2026-02-21T00:00:00Z",
            "page_url": "https://example.com/",
            "detection": {"confidence": 0.0, "signals": {}, "classification": "human"},
            "test_results": [],
        }
        resp = await client.post(
            "/v1/ingest",
            content=json.dumps(payload).encode(),
            headers={"Content-Type": "text/plain"},
        )
        # Should be parsed as JSON: 404 (invalid site key), not 422 (unparseable body)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_text_plain_only_rewritten_for_ingest_path(self, client: AsyncClient):
        """text/plain must NOT be rewritten for other endpoints."""
        resp = await client.post(
            "/v1/sites",
            content=json.dumps({"domain": "example.com"}).encode(),
            headers={"Content-Type": "text/plain"},
        )
        # Without rewriting, this should fail with 422 (unparseable)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# OpenAPI docs (development mode)
# ---------------------------------------------------------------------------


class TestOpenAPIDocs:
    @pytest.mark.asyncio
    async def test_openapi_json_available(self, client: AsyncClient):
        """In development mode, /openapi.json must return the schema."""
        resp = await client.get("/openapi.json")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_docs_available(self, client: AsyncClient):
        """In development mode, /docs must return the Swagger UI page."""
        resp = await client.get("/docs")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_openapi_schema_contains_paths(self, client: AsyncClient):
        resp = await client.get("/openapi.json")
        schema = resp.json()
        assert "paths" in schema
        assert "/v1/ingest" in schema["paths"]
