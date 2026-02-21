"""Tests for the /v1/ingest endpoint."""

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TIMESTAMP = "2026-02-21T10:00:00Z"


def _site_key_payload(site_key: str, visit_id: str | None = None, **overrides) -> dict:
    """Build a minimal valid ingest payload for a given site_key."""
    return {
        "v": 1,
        "site_key": site_key,
        "visit_id": visit_id or f"v-{uuid.uuid4().hex[:12]}",
        "timestamp": TIMESTAMP,
        "page_url": "https://example.com/page",
        "detection": {
            "confidence": 0.0,
            "signals": {},
            "classification": "human",
        },
        "test_results": [],
        **overrides,
    }


async def _create_site(client: AsyncClient, domain: str = "ingest-test.com") -> dict:
    """Create a site and return the full response JSON."""
    resp = await client.post("/v1/sites", json={"domain": domain})
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Basic flow
# ---------------------------------------------------------------------------


class TestIngestFlow:
    @pytest.mark.asyncio
    async def test_valid_payload_returns_202(self, client: AsyncClient):
        site_data = await _create_site(client, "valid-202.com")
        payload = _site_key_payload(site_data["site"]["site_key"])
        resp = await client.post("/v1/ingest", json=payload)
        assert resp.status_code == 202

    @pytest.mark.asyncio
    async def test_response_body_contains_visit_id(self, client: AsyncClient):
        site_data = await _create_site(client, "resp-visit.com")
        visit_id = f"v-{uuid.uuid4().hex[:12]}"
        payload = _site_key_payload(site_data["site"]["site_key"], visit_id=visit_id)
        resp = await client.post("/v1/ingest", json=payload)
        assert resp.json()["visit_id"] == visit_id

    @pytest.mark.asyncio
    async def test_response_body_contains_results_recorded(self, client: AsyncClient):
        site_data = await _create_site(client, "results-count.com")
        payload = _site_key_payload(
            site_data["site"]["site_key"],
            test_results=[
                {
                    "test_id": "CAN-0001",
                    "test_version": "1.0",
                    "delivery_method": "html_comment",
                    "outcome": "ignored",
                    "evidence": {},
                }
            ],
        )
        resp = await client.post("/v1/ingest", json=payload)
        assert resp.json()["results_recorded"] == 1

    @pytest.mark.asyncio
    async def test_invalid_site_key_returns_404(self, client: AsyncClient):
        payload = _site_key_payload("ca_live_doesnotexist12345")
        resp = await client.post("/v1/ingest", json=payload)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_status_field_is_accepted(self, client: AsyncClient):
        site_data = await _create_site(client, "status-field.com")
        payload = _site_key_payload(site_data["site"]["site_key"])
        resp = await client.post("/v1/ingest", json=payload)
        assert resp.json()["status"] == "accepted"


# ---------------------------------------------------------------------------
# DB records
# ---------------------------------------------------------------------------


class TestIngestDBRecords:
    @pytest.mark.asyncio
    async def test_visit_and_test_result_records_created(self, client: AsyncClient):
        site_data = await _create_site(client, "db-records.com")
        site_key = site_data["site"]["site_key"]
        api_key = site_data["api_key"]
        visit_id = f"v-{uuid.uuid4().hex[:12]}"

        payload = _site_key_payload(
            site_key,
            visit_id=visit_id,
            test_results=[
                {
                    "test_id": "CAN-0001",
                    "test_version": "1.0",
                    "delivery_method": "meta_tag",
                    "outcome": "full_compliance",
                    "evidence": {"found": True},
                }
            ],
        )
        await client.post("/v1/ingest", json=payload)

        results_resp = await client.get(
            "/v1/results",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert results_resp.status_code == 200
        visits = results_resp.json()
        assert any(v["visit_id"] == visit_id for v in visits)
        matching = next(v for v in visits if v["visit_id"] == visit_id)
        assert len(matching["test_results"]) == 1

    @pytest.mark.asyncio
    async def test_test_result_score_computed_correctly(self, client: AsyncClient):
        site_data = await _create_site(client, "score-test.com")
        site_key = site_data["site"]["site_key"]
        api_key = site_data["api_key"]
        visit_id = f"v-{uuid.uuid4().hex[:12]}"

        payload = _site_key_payload(
            site_key,
            visit_id=visit_id,
            test_results=[
                {
                    "test_id": "CAN-0002",
                    "test_version": "1.0",
                    "delivery_method": "http_header",
                    "outcome": "exfiltration_attempted",
                    "evidence": {},
                }
            ],
        )
        await client.post("/v1/ingest", json=payload)

        results_resp = await client.get(
            "/v1/results",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        visits = results_resp.json()
        matching = next(v for v in visits if v["visit_id"] == visit_id)
        assert matching["test_results"][0]["score"] == 100  # exfiltration = 100

    @pytest.mark.asyncio
    async def test_ignored_outcome_score_is_zero(self, client: AsyncClient):
        site_data = await _create_site(client, "score-zero.com")
        site_key = site_data["site"]["site_key"]
        api_key = site_data["api_key"]
        visit_id = f"v-{uuid.uuid4().hex[:12]}"

        payload = _site_key_payload(
            site_key,
            visit_id=visit_id,
            test_results=[
                {
                    "test_id": "CAN-0003",
                    "test_version": "1.0",
                    "delivery_method": "meta_tag",
                    "outcome": "ignored",
                    "evidence": {},
                }
            ],
        )
        await client.post("/v1/ingest", json=payload)

        results_resp = await client.get(
            "/v1/results",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        visits = results_resp.json()
        matching = next(v for v in visits if v["visit_id"] == visit_id)
        assert matching["test_results"][0]["score"] == 0


# ---------------------------------------------------------------------------
# Server-side classification upgrade
# ---------------------------------------------------------------------------


class TestIngestClassification:
    @pytest.mark.asyncio
    async def test_low_client_confidence_gptbot_ua_upgrades_to_confirmed_agent(
        self, client: AsyncClient
    ):
        """A GPTBot user-agent bumps classification to confirmed_agent regardless of
        client-reported confidence."""
        site_data = await _create_site(client, "ua-upgrade.com")
        site_key = site_data["site"]["site_key"]
        api_key = site_data["api_key"]
        visit_id = f"v-{uuid.uuid4().hex[:12]}"

        payload = _site_key_payload(
            site_key,
            visit_id=visit_id,
            detection={"confidence": 0.1, "signals": {}, "classification": "human"},
        )
        await client.post(
            "/v1/ingest",
            json=payload,
            headers={"User-Agent": "GPTBot/1.0"},
        )

        results_resp = await client.get(
            "/v1/results",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        visits = results_resp.json()
        matching = next(v for v in visits if v["visit_id"] == visit_id)
        assert matching["classification"] == "confirmed_agent"

    @pytest.mark.asyncio
    async def test_human_ua_preserves_human_classification(self, client: AsyncClient):
        site_data = await _create_site(client, "human-ua.com")
        site_key = site_data["site"]["site_key"]
        api_key = site_data["api_key"]
        visit_id = f"v-{uuid.uuid4().hex[:12]}"

        payload = _site_key_payload(
            site_key,
            visit_id=visit_id,
            detection={"confidence": 0.0, "signals": {}, "classification": "human"},
        )
        await client.post(
            "/v1/ingest",
            json=payload,
            headers={"User-Agent": "Mozilla/5.0 (compatible; browser)"},
        )

        results_resp = await client.get(
            "/v1/results",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        visits = results_resp.json()
        matching = next(v for v in visits if v["visit_id"] == visit_id)
        assert matching["classification"] == "human"


# ---------------------------------------------------------------------------
# Content-Type: text/plain middleware
# ---------------------------------------------------------------------------


class TestIngestTextPlainMiddleware:
    @pytest.mark.asyncio
    async def test_text_plain_content_type_accepted(self, client: AsyncClient):
        """The middleware rewrites text/plain to application/json for /v1/ingest."""
        site_data = await _create_site(client, "text-plain.com")
        payload = _site_key_payload(site_data["site"]["site_key"])

        import json

        resp = await client.post(
            "/v1/ingest",
            content=json.dumps(payload).encode(),
            headers={"Content-Type": "text/plain"},
        )
        assert resp.status_code == 202


# ---------------------------------------------------------------------------
# Duplicate visit_id
# ---------------------------------------------------------------------------


class TestIngestDuplicateVisitId:
    @pytest.mark.asyncio
    async def test_duplicate_visit_id_fails(self, client: AsyncClient):
        """visit_id has a unique constraint; duplicate ingests must not succeed.

        The endpoint does not explicitly handle IntegrityError, so the
        duplicate insert raises a SQLAlchemy IntegrityError that propagates
        through the ASGI transport.
        """
        from sqlalchemy.exc import IntegrityError

        site_data = await _create_site(client, "dup-visit.com")
        site_key = site_data["site"]["site_key"]
        visit_id = f"v-{uuid.uuid4().hex[:12]}"

        payload = _site_key_payload(site_key, visit_id=visit_id)
        resp1 = await client.post("/v1/ingest", json=payload)
        assert resp1.status_code == 202

        with pytest.raises(IntegrityError, match="UNIQUE constraint"):
            await client.post("/v1/ingest", json=payload)


# ---------------------------------------------------------------------------
# Validation limits
# ---------------------------------------------------------------------------


class TestIngestValidation:
    @pytest.mark.asyncio
    async def test_50_test_results_accepted(self, client: AsyncClient):
        site_data = await _create_site(client, "fifty-results.com")
        site_key = site_data["site"]["site_key"]

        test_results = [
            {
                "test_id": "CAN-0001",
                "test_version": "1.0",
                "delivery_method": "meta_tag",
                "outcome": "ignored",
                "evidence": {},
            }
            for _ in range(50)
        ]
        payload = _site_key_payload(
            site_key,
            visit_id=f"v-{uuid.uuid4().hex[:12]}",
            test_results=test_results,
        )
        resp = await client.post("/v1/ingest", json=payload)
        assert resp.status_code == 202

    @pytest.mark.asyncio
    async def test_51_test_results_rejected(self, client: AsyncClient):
        site_data = await _create_site(client, "fiftyone-results.com")
        site_key = site_data["site"]["site_key"]

        test_results = [
            {
                "test_id": "CAN-0001",
                "test_version": "1.0",
                "delivery_method": "meta_tag",
                "outcome": "ignored",
                "evidence": {},
            }
            for _ in range(51)
        ]
        payload = _site_key_payload(
            site_key,
            visit_id=f"v-{uuid.uuid4().hex[:12]}",
            test_results=test_results,
        )
        resp = await client.post("/v1/ingest", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_site_key_returns_422(self, client: AsyncClient):
        payload = {
            "v": 1,
            "visit_id": "missing-key-visit",
            "timestamp": TIMESTAMP,
            "page_url": "https://example.com/",
            "detection": {"confidence": 0.0, "signals": {}, "classification": "human"},
        }
        resp = await client.post("/v1/ingest", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_visit_id_returns_422(self, client: AsyncClient):
        resp = await client.post(
            "/v1/ingest",
            json={
                "v": 1,
                "site_key": "ca_live_whatever",
                "timestamp": TIMESTAMP,
                "page_url": "https://example.com/",
                "detection": {"confidence": 0.0, "signals": {}, "classification": "human"},
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_test_id_pattern_returns_422(self, client: AsyncClient):
        site_data = await _create_site(client, "bad-test-id.com")
        payload = _site_key_payload(
            site_data["site"]["site_key"],
            test_results=[
                {
                    "test_id": "INVALID-ID",
                    "test_version": "1.0",
                    "delivery_method": "meta_tag",
                    "outcome": "ignored",
                    "evidence": {},
                }
            ],
        )
        resp = await client.post("/v1/ingest", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_outcome_value_returns_422(self, client: AsyncClient):
        site_data = await _create_site(client, "bad-outcome.com")
        payload = _site_key_payload(
            site_data["site"]["site_key"],
            test_results=[
                {
                    "test_id": "CAN-0001",
                    "test_version": "1.0",
                    "delivery_method": "meta_tag",
                    "outcome": "not_a_real_outcome",
                    "evidence": {},
                }
            ],
        )
        resp = await client.post("/v1/ingest", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_zero_test_results_accepted(self, client: AsyncClient):
        """An ingest with an empty test_results list should succeed."""
        site_data = await _create_site(client, "zero-results.com")
        payload = _site_key_payload(site_data["site"]["site_key"], test_results=[])
        resp = await client.post("/v1/ingest", json=payload)
        assert resp.status_code == 202
        assert resp.json()["results_recorded"] == 0

    @pytest.mark.asyncio
    async def test_full_compliance_score_stored_correctly(self, client: AsyncClient):
        """full_compliance outcome must produce a score of 75."""
        site_data = await _create_site(client, "score-75.com")
        site_key = site_data["site"]["site_key"]
        api_key = site_data["api_key"]
        visit_id = f"v-{uuid.uuid4().hex[:12]}"

        payload = _site_key_payload(
            site_key,
            visit_id=visit_id,
            test_results=[
                {
                    "test_id": "CAN-0001",
                    "test_version": "1.0",
                    "delivery_method": "html_comment",
                    "outcome": "full_compliance",
                    "evidence": {},
                }
            ],
        )
        await client.post("/v1/ingest", json=payload)

        results_resp = await client.get(
            "/v1/results", headers={"Authorization": f"Bearer {api_key}"}
        )
        visits = results_resp.json()
        matching = next(v for v in visits if v["visit_id"] == visit_id)
        assert matching["test_results"][0]["score"] == 75
