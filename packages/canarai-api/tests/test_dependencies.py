"""Integration tests for auth dependency via actual HTTP endpoints.

These tests exercise the full FastAPI request pipeline using the in-memory
SQLite engine provided by the `client` fixture.  No mocking — real DB queries.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from canarai.models.api_key import ApiKey


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _auth(api_key: str) -> dict[str, str]:
    """Return an Authorization header dict for a Bearer token."""
    return {"Authorization": f"Bearer {api_key}"}


# ---------------------------------------------------------------------------
# Valid authentication
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_valid_api_key_returns_200(
    authenticated_client: tuple[AsyncClient, dict],
):
    """A valid Bearer token grants access to GET /v1/results."""
    client, site_data = authenticated_client
    response = await client.get("/v1/results", headers=_auth(site_data["api_key"]))
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Missing / malformed Authorization header
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_authorization_header_returns_422(client: AsyncClient):
    """Absence of the Authorization header yields 422 (missing required field)."""
    response = await client.get("/v1/results")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_authorization_without_bearer_prefix_returns_401(
    authenticated_client: tuple[AsyncClient, dict],
):
    """Authorization header that does not start with 'Bearer ' is rejected."""
    client, site_data = authenticated_client
    # Send the raw key without the "Bearer " prefix
    headers = {"Authorization": site_data["api_key"]}
    response = await client.get("/v1/results", headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_api_key_returns_401(client: AsyncClient):
    """A random string that does not match any stored key is rejected."""
    headers = {"Authorization": "Bearer ca_sk_totally_invalid_key_not_in_db"}
    response = await client.get("/v1/results", headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_bearer_with_empty_key_returns_401(client: AsyncClient):
    """'Bearer ' with nothing after it is rejected as an empty API key."""
    headers = {"Authorization": "Bearer "}
    response = await client.get("/v1/results", headers=headers)
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Deactivated API key
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deactivated_api_key_returns_401(
    authenticated_client: tuple[AsyncClient, dict],
    db_session: AsyncSession,
):
    """After deactivating an API key in the DB, requests with it must fail."""
    client, site_data = authenticated_client

    # Confirm it works before deactivation
    pre_response = await client.get("/v1/results", headers=_auth(site_data["api_key"]))
    assert pre_response.status_code == 200

    # Deactivate every key for this site directly via the session
    stmt = select(ApiKey).where(ApiKey.site_id == site_data["site_id"])
    result = await db_session.execute(stmt)
    keys = result.scalars().all()
    assert keys, "Expected at least one ApiKey in the DB for this site"
    for key in keys:
        key.is_active = False
    await db_session.commit()

    # The same bearer token should now be rejected
    post_response = await client.get("/v1/results", headers=_auth(site_data["api_key"]))
    assert post_response.status_code == 401


# ---------------------------------------------------------------------------
# Cross-tenant access (403)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_key_from_site_a_cannot_patch_site_b(client: AsyncClient):
    """API key belonging to site A must receive 403 when patching site B."""
    # Create site A
    resp_a = await client.post("/v1/sites", json={"domain": "site-a.example.com"})
    assert resp_a.status_code == 201
    data_a = resp_a.json()
    api_key_a = data_a["api_key"]

    # Create site B
    resp_b = await client.post("/v1/sites", json={"domain": "site-b.example.com"})
    assert resp_b.status_code == 201
    data_b = resp_b.json()
    site_b_id = data_b["site"]["id"]

    # Try to update site B using site A's API key
    response = await client.patch(
        f"/v1/sites/{site_b_id}",
        headers=_auth(api_key_a),
        json={"domain": "pwned.example.com"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_api_key_can_patch_own_site(
    authenticated_client: tuple[AsyncClient, dict],
):
    """An API key is allowed to update the site it was created for."""
    client, site_data = authenticated_client
    response = await client.patch(
        f"/v1/sites/{site_data['site_id']}",
        headers=_auth(site_data["api_key"]),
        json={"domain": "updated-domain.example.com"},
    )
    assert response.status_code == 200
    assert response.json()["domain"] == "updated-domain.example.com"


# ---------------------------------------------------------------------------
# Results endpoint cross-tenant guard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_results_for_another_site_returns_403(client: AsyncClient):
    """Passing site_id of another tenant to GET /v1/results must be rejected."""
    # Create two independent sites
    resp_a = await client.post("/v1/sites", json={"domain": "tenant-a.com"})
    assert resp_a.status_code == 201
    data_a = resp_a.json()
    api_key_a = data_a["api_key"]

    resp_b = await client.post("/v1/sites", json={"domain": "tenant-b.com"})
    assert resp_b.status_code == 201
    site_b_id = resp_b.json()["site"]["id"]

    # Query results for site B using site A's key
    response = await client.get(
        "/v1/results",
        headers=_auth(api_key_a),
        params={"site_id": site_b_id},
    )
    assert response.status_code == 403
