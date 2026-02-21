"""Tests for the /v1/results endpoints."""

import uuid

import pytest
from httpx import AsyncClient

from canarai.routers.sites import _site_creation_limits


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TIMESTAMP = "2026-02-21T10:00:00Z"


async def _create_site(client: AsyncClient, domain: str) -> dict:
    _site_creation_limits.clear()
    resp = await client.post("/v1/sites", json={"domain": domain})
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _ingest(
    client: AsyncClient,
    site_key: str,
    visit_id: str | None = None,
    classification: str = "human",
    confidence: float = 0.0,
    agent_family: str | None = None,
    outcomes: list[str] | None = None,
    test_id: str = "CAN-0001",
    ua: str | None = None,
) -> None:
    vid = visit_id or f"v-{uuid.uuid4().hex[:12]}"
    test_results = []
    for outcome in (outcomes or []):
        test_results.append(
            {
                "test_id": test_id,
                "test_version": "1.0",
                "delivery_method": "meta_tag",
                "outcome": outcome,
                "evidence": {},
            }
        )

    payload = {
        "v": 1,
        "site_key": site_key,
        "visit_id": vid,
        "timestamp": TIMESTAMP,
        "page_url": "https://example.com/",
        "detection": {
            "confidence": confidence,
            "signals": {},
            "classification": classification,
            "agent_family": agent_family,
        },
        "test_results": test_results,
    }
    headers = {}
    if ua:
        headers["User-Agent"] = ua
    resp = await client.post("/v1/ingest", json=payload, headers=headers)
    assert resp.status_code == 202, resp.text
    return vid


def _auth(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}"}


# ---------------------------------------------------------------------------
# GET /v1/results — auth requirements
# ---------------------------------------------------------------------------


class TestResultsAuth:
    @pytest.mark.asyncio
    async def test_no_auth_header_returns_422(self, client: AsyncClient):
        resp = await client.get("/v1/results")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_api_key_returns_401(self, client: AsyncClient):
        resp = await client.get(
            "/v1/results",
            headers={"Authorization": "Bearer ca_sk_bad_key"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_auth_returns_200(self, client: AsyncClient, site_with_key: dict):
        resp = await client.get(
            "/v1/results", headers=_auth(site_with_key["api_key"])
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_list(self, client: AsyncClient, site_with_key: dict):
        resp = await client.get(
            "/v1/results", headers=_auth(site_with_key["api_key"])
        )
        assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# GET /v1/results — data retrieval
# ---------------------------------------------------------------------------


class TestResultsData:
    @pytest.mark.asyncio
    async def test_results_returned_for_own_site(self, client: AsyncClient):
        data = await _create_site(client, "results-own.com")
        site_key = data["site"]["site_key"]
        api_key = data["api_key"]
        vid = await _ingest(client, site_key)

        resp = await client.get("/v1/results", headers=_auth(api_key))
        visit_ids = [v["visit_id"] for v in resp.json()]
        assert vid in visit_ids

    @pytest.mark.asyncio
    async def test_cross_site_access_returns_403(self, client: AsyncClient):
        """API key from site A must not be able to query site B's results."""
        data_a = await _create_site(client, "cross-a.com")
        data_b = await _create_site(client, "cross-b.com")

        resp = await client.get(
            "/v1/results",
            params={"site_id": data_b["site"]["id"]},
            headers=_auth(data_a["api_key"]),
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /v1/results — pagination
# ---------------------------------------------------------------------------


class TestResultsPagination:
    @pytest.mark.asyncio
    async def test_limit_parameter_respected(self, client: AsyncClient):
        data = await _create_site(client, "paginate-limit.com")
        site_key = data["site"]["site_key"]
        api_key = data["api_key"]

        for _ in range(5):
            await _ingest(client, site_key)

        resp = await client.get(
            "/v1/results",
            params={"limit": 2},
            headers=_auth(api_key),
        )
        assert resp.status_code == 200
        assert len(resp.json()) <= 2

    @pytest.mark.asyncio
    async def test_offset_parameter_respected(self, client: AsyncClient):
        data = await _create_site(client, "paginate-offset.com")
        site_key = data["site"]["site_key"]
        api_key = data["api_key"]

        for _ in range(4):
            await _ingest(client, site_key)

        all_resp = await client.get(
            "/v1/results", params={"limit": 100}, headers=_auth(api_key)
        )
        offset_resp = await client.get(
            "/v1/results", params={"limit": 100, "offset": 2}, headers=_auth(api_key)
        )
        # With offset=2, we should get 2 fewer results
        assert len(offset_resp.json()) == len(all_resp.json()) - 2


# ---------------------------------------------------------------------------
# GET /v1/results — filtering
# ---------------------------------------------------------------------------


class TestResultsFiltering:
    @pytest.mark.asyncio
    async def test_filter_by_classification(self, client: AsyncClient):
        data = await _create_site(client, "filter-class.com")
        site_key = data["site"]["site_key"]
        api_key = data["api_key"]

        # Ingest one confirmed_agent via GPTBot UA, one human
        await _ingest(client, site_key, ua="GPTBot/1.0")
        await _ingest(
            client,
            site_key,
            classification="human",
            confidence=0.0,
            ua="Mozilla/5.0",
        )

        resp = await client.get(
            "/v1/results",
            params={"classification": "confirmed_agent"},
            headers=_auth(api_key),
        )
        assert resp.status_code == 200
        for visit in resp.json():
            assert visit["classification"] == "confirmed_agent"

    @pytest.mark.asyncio
    async def test_filter_by_test_id(self, client: AsyncClient):
        data = await _create_site(client, "filter-testid.com")
        site_key = data["site"]["site_key"]
        api_key = data["api_key"]

        await _ingest(client, site_key, outcomes=["ignored"], test_id="CAN-0001")
        await _ingest(client, site_key, outcomes=["ignored"], test_id="CAN-0002")

        resp = await client.get(
            "/v1/results",
            params={"test_id": "CAN-0001"},
            headers=_auth(api_key),
        )
        assert resp.status_code == 200
        for visit in resp.json():
            result_test_ids = {tr["test_id"] for tr in visit["test_results"]}
            assert "CAN-0001" in result_test_ids

    @pytest.mark.asyncio
    async def test_filter_by_outcome(self, client: AsyncClient):
        data = await _create_site(client, "filter-outcome.com")
        site_key = data["site"]["site_key"]
        api_key = data["api_key"]

        await _ingest(client, site_key, outcomes=["exfiltration_attempted"], test_id="CAN-0001")
        await _ingest(client, site_key, outcomes=["ignored"], test_id="CAN-0001")

        resp = await client.get(
            "/v1/results",
            params={"outcome": "exfiltration_attempted"},
            headers=_auth(api_key),
        )
        assert resp.status_code == 200
        for visit in resp.json():
            outcomes = {tr["outcome"] for tr in visit["test_results"]}
            assert "exfiltration_attempted" in outcomes


# ---------------------------------------------------------------------------
# GET /v1/results/summary
# ---------------------------------------------------------------------------


class TestResultsSummary:
    @pytest.mark.asyncio
    async def test_summary_requires_auth(self, client: AsyncClient):
        resp = await client.get("/v1/results/summary")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_summary_returns_200_with_auth(self, client: AsyncClient, site_with_key: dict):
        resp = await client.get(
            "/v1/results/summary", headers=_auth(site_with_key["api_key"])
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_summary_structure(self, client: AsyncClient, site_with_key: dict):
        resp = await client.get(
            "/v1/results/summary", headers=_auth(site_with_key["api_key"])
        )
        body = resp.json()
        assert "total_visits" in body
        assert "agent_visits" in body
        assert "human_visits" in body
        assert "total_tests" in body
        assert "resilience_score" in body
        assert "critical_failure_rate" in body
        assert "outcomes" in body
        assert "top_agent_families" in body

    @pytest.mark.asyncio
    async def test_summary_counts_are_correct(self, client: AsyncClient):
        data = await _create_site(client, "summary-counts.com")
        site_key = data["site"]["site_key"]
        api_key = data["api_key"]

        # One confirmed agent (via GPTBot UA) with 2 test results, one human
        await _ingest(
            client,
            site_key,
            outcomes=["full_compliance", "exfiltration_attempted"],
            test_id="CAN-0001",
            ua="GPTBot/1.0",
        )
        await _ingest(client, site_key, confidence=0.0)

        resp = await client.get("/v1/results/summary", headers=_auth(api_key))
        summary = resp.json()

        assert summary["total_visits"] == 2
        assert summary["agent_visits"] == 1
        assert summary["human_visits"] == 1
        assert summary["total_tests"] == 2

    @pytest.mark.asyncio
    async def test_summary_resilience_score(self, client: AsyncClient):
        data = await _create_site(client, "summary-resilience.com")
        site_key = data["site"]["site_key"]
        api_key = data["api_key"]

        # full_compliance=75, exfiltration_attempted=100 -> avg=87.5
        await _ingest(
            client,
            site_key,
            outcomes=["full_compliance", "exfiltration_attempted"],
            test_id="CAN-0001",
        )

        resp = await client.get("/v1/results/summary", headers=_auth(api_key))
        assert resp.json()["resilience_score"] == 87.5

    @pytest.mark.asyncio
    async def test_summary_cross_site_access_forbidden(self, client: AsyncClient):
        data_a = await _create_site(client, "sum-cross-a.com")
        data_b = await _create_site(client, "sum-cross-b.com")

        resp = await client.get(
            "/v1/results/summary",
            params={"site_id": data_b["site"]["id"]},
            headers=_auth(data_a["api_key"]),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_summary_empty_site_returns_zeros(self, client: AsyncClient):
        data = await _create_site(client, "summary-empty.com")
        resp = await client.get("/v1/results/summary", headers=_auth(data["api_key"]))
        summary = resp.json()
        assert summary["total_visits"] == 0
        assert summary["agent_visits"] == 0
        assert summary["resilience_score"] == 0.0
        assert summary["critical_failure_rate"] == 0.0
