"""Tests for canarai.services.alerting."""

import json
from datetime import datetime, timezone

import pytest
import respx
from httpx import AsyncClient, Response, TimeoutException

from canarai.models.site import Site
from canarai.models.webhook import Webhook, WebhookDelivery
from canarai.services.alerting import (
    dispatch_webhook,
    fire_webhooks_for_event,
    get_webhooks_for_site,
    sign_payload,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_site(site_id: str = "site-alert-1") -> Site:
    return Site(
        id=site_id,
        site_key=f"ca_live_alerttest{site_id[:8].replace('-', '')}",
        domain="alert-test.com",
    )


def _make_webhook(
    webhook_id: str = "wh-alert-1",
    site_id: str = "site-alert-1",
    url: str = "https://example.com/hook",
    secret: str = "testsecret",
    events: list[str] | None = None,
    enabled: bool = True,
) -> Webhook:
    return Webhook(
        id=webhook_id,
        site_id=site_id,
        url=url,
        events=events if events is not None else ["visit.agent_detected"],
        secret=secret,
        enabled=enabled,
    )


# ---------------------------------------------------------------------------
# sign_payload
# ---------------------------------------------------------------------------


class TestSignPayload:
    """Tests for sign_payload()."""

    def test_returns_hex_string(self):
        sig = sign_payload({"foo": "bar"}, "secret")
        assert isinstance(sig, str)
        # SHA-256 hex digest is always 64 characters
        assert len(sig) == 64

    def test_deterministic_same_inputs(self):
        payload = {"event": "visit.agent_detected", "z": 1, "a": 2}
        sig1 = sign_payload(payload, "mysecret")
        sig2 = sign_payload(payload, "mysecret")
        assert sig1 == sig2

    def test_sort_keys_makes_order_irrelevant(self):
        """Key order in the dict must not affect the signature."""
        payload_a = {"b": 2, "a": 1}
        payload_b = {"a": 1, "b": 2}
        assert sign_payload(payload_a, "s") == sign_payload(payload_b, "s")

    def test_different_secrets_produce_different_sigs(self):
        payload = {"data": "same"}
        assert sign_payload(payload, "secret-one") != sign_payload(payload, "secret-two")

    def test_different_payloads_produce_different_sigs(self):
        assert sign_payload({"a": 1}, "s") != sign_payload({"a": 2}, "s")

    def test_signature_matches_manual_hmac(self):
        import hashlib
        import hmac

        payload = {"event": "test", "value": 42}
        secret = "known-secret"
        body = json.dumps(payload, sort_keys=True, default=str)
        expected = hmac.new(
            secret.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        assert sign_payload(payload, secret) == expected

    def test_empty_payload_does_not_raise(self):
        sig = sign_payload({}, "secret")
        assert len(sig) == 64

    def test_nested_payload_is_stable(self):
        payload = {"outer": {"inner": [1, 2, 3]}}
        sig1 = sign_payload(payload, "s")
        sig2 = sign_payload(payload, "s")
        assert sig1 == sig2


# ---------------------------------------------------------------------------
# dispatch_webhook
# ---------------------------------------------------------------------------


class TestDispatchWebhook:
    """Tests for dispatch_webhook() using respx to mock httpx."""

    @pytest.mark.asyncio
    async def test_200_response_sets_status_code(self, db_session):
        site = _make_site("site-d200")
        db_session.add(site)
        webhook = _make_webhook("wh-d200", site_id="site-d200")
        db_session.add(webhook)
        await db_session.flush()

        with respx.mock:
            respx.post("https://example.com/hook").mock(return_value=Response(200))
            delivery = await dispatch_webhook(
                db_session, webhook, "visit.agent_detected", {"test": True}
            )

        assert delivery.status_code == 200

    @pytest.mark.asyncio
    async def test_200_response_no_retry_scheduled(self, db_session):
        site = _make_site("site-d200b")
        db_session.add(site)
        webhook = _make_webhook("wh-d200b", site_id="site-d200b")
        db_session.add(webhook)
        await db_session.flush()

        with respx.mock:
            respx.post("https://example.com/hook").mock(return_value=Response(200))
            delivery = await dispatch_webhook(
                db_session, webhook, "visit.agent_detected", {"test": True}
            )

        assert delivery.next_retry_at is None

    @pytest.mark.asyncio
    async def test_400_response_schedules_retry(self, db_session):
        site = _make_site("site-d400")
        db_session.add(site)
        webhook = _make_webhook("wh-d400", site_id="site-d400")
        db_session.add(webhook)
        await db_session.flush()

        with respx.mock:
            respx.post("https://example.com/hook").mock(return_value=Response(400))
            delivery = await dispatch_webhook(
                db_session, webhook, "visit.agent_detected", {"test": True}
            )

        assert delivery.status_code == 400
        assert delivery.next_retry_at is not None
        assert delivery.next_retry_at > datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_500_response_schedules_retry(self, db_session):
        site = _make_site("site-d500")
        db_session.add(site)
        webhook = _make_webhook("wh-d500", site_id="site-d500")
        db_session.add(webhook)
        await db_session.flush()

        with respx.mock:
            respx.post("https://example.com/hook").mock(return_value=Response(500))
            delivery = await dispatch_webhook(
                db_session, webhook, "visit.agent_detected", {"test": True}
            )

        assert delivery.status_code == 500
        assert delivery.next_retry_at is not None

    @pytest.mark.asyncio
    async def test_timeout_sets_status_code_none(self, db_session):
        site = _make_site("site-dtout")
        db_session.add(site)
        webhook = _make_webhook("wh-dtout", site_id="site-dtout")
        db_session.add(webhook)
        await db_session.flush()

        with respx.mock:
            respx.post("https://example.com/hook").mock(side_effect=TimeoutException("timed out"))
            delivery = await dispatch_webhook(
                db_session, webhook, "visit.agent_detected", {"test": True}
            )

        assert delivery.status_code is None

    @pytest.mark.asyncio
    async def test_timeout_schedules_retry(self, db_session):
        site = _make_site("site-dtout2")
        db_session.add(site)
        webhook = _make_webhook("wh-dtout2", site_id="site-dtout2")
        db_session.add(webhook)
        await db_session.flush()

        with respx.mock:
            respx.post("https://example.com/hook").mock(side_effect=TimeoutException("timed out"))
            delivery = await dispatch_webhook(
                db_session, webhook, "visit.agent_detected", {"test": True}
            )

        assert delivery.next_retry_at is not None
        assert delivery.next_retry_at > datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_headers_include_signature(self, db_session):
        site = _make_site("site-dhdr")
        db_session.add(site)
        webhook = _make_webhook("wh-dhdr", site_id="site-dhdr", secret="header-test-secret")
        db_session.add(webhook)
        await db_session.flush()

        captured_request = None

        with respx.mock:
            route = respx.post("https://example.com/hook").mock(return_value=Response(200))
            await dispatch_webhook(
                db_session, webhook, "visit.agent_detected", {"data": "payload"}
            )
            captured_request = route.calls.last.request

        assert "x-canarai-signature" in captured_request.headers

    @pytest.mark.asyncio
    async def test_headers_include_event_type(self, db_session):
        site = _make_site("site-dhdr2")
        db_session.add(site)
        webhook = _make_webhook("wh-dhdr2", site_id="site-dhdr2")
        db_session.add(webhook)
        await db_session.flush()

        with respx.mock:
            route = respx.post("https://example.com/hook").mock(return_value=Response(200))
            await dispatch_webhook(
                db_session, webhook, "visit.agent_detected", {"x": 1}
            )
            captured_request = route.calls.last.request

        assert captured_request.headers["x-canarai-event"] == "visit.agent_detected"

    @pytest.mark.asyncio
    async def test_headers_include_delivery_id(self, db_session):
        site = _make_site("site-dhdr3")
        db_session.add(site)
        webhook = _make_webhook("wh-dhdr3", site_id="site-dhdr3")
        db_session.add(webhook)
        await db_session.flush()

        with respx.mock:
            route = respx.post("https://example.com/hook").mock(return_value=Response(200))
            delivery = await dispatch_webhook(
                db_session, webhook, "visit.agent_detected", {"x": 1}
            )
            captured_request = route.calls.last.request

        assert captured_request.headers["x-canarai-delivery"] == delivery.id

    @pytest.mark.asyncio
    async def test_delivery_record_added_to_session(self, db_session):
        site = _make_site("site-dadd")
        db_session.add(site)
        webhook = _make_webhook("wh-dadd", site_id="site-dadd")
        db_session.add(webhook)
        await db_session.flush()

        with respx.mock:
            respx.post("https://example.com/hook").mock(return_value=Response(200))
            delivery = await dispatch_webhook(
                db_session, webhook, "visit.agent_detected", {"y": 2}
            )

        # The delivery must be tracked by the session (i.e., db.add was called)
        assert delivery in db_session.new or delivery.id is not None

    @pytest.mark.asyncio
    async def test_delivery_has_correct_event_type(self, db_session):
        site = _make_site("site-devt")
        db_session.add(site)
        webhook = _make_webhook("wh-devt", site_id="site-devt")
        db_session.add(webhook)
        await db_session.flush()

        with respx.mock:
            respx.post("https://example.com/hook").mock(return_value=Response(200))
            delivery = await dispatch_webhook(
                db_session, webhook, "test.critical_failure", {"z": 3}
            )

        assert delivery.event_type == "test.critical_failure"

    @pytest.mark.asyncio
    async def test_delivery_has_correct_webhook_id(self, db_session):
        site = _make_site("site-dwid")
        db_session.add(site)
        webhook = _make_webhook("wh-dwid-unique", site_id="site-dwid")
        db_session.add(webhook)
        await db_session.flush()

        with respx.mock:
            respx.post("https://example.com/hook").mock(return_value=Response(200))
            delivery = await dispatch_webhook(
                db_session, webhook, "visit.agent_detected", {}
            )

        assert delivery.webhook_id == "wh-dwid-unique"


# ---------------------------------------------------------------------------
# get_webhooks_for_site
# ---------------------------------------------------------------------------


class TestGetWebhooksForSite:
    """Tests for get_webhooks_for_site()."""

    @pytest.mark.asyncio
    async def test_returns_matching_webhooks(self, db_session):
        site = _make_site("site-gwfs1")
        db_session.add(site)
        wh = _make_webhook(
            "wh-gwfs1",
            site_id="site-gwfs1",
            events=["visit.agent_detected"],
        )
        db_session.add(wh)
        await db_session.flush()

        result = await get_webhooks_for_site(db_session, "site-gwfs1", "visit.agent_detected")
        assert len(result) == 1
        assert result[0].id == "wh-gwfs1"

    @pytest.mark.asyncio
    async def test_excludes_disabled_webhooks(self, db_session):
        site = _make_site("site-gwfs2")
        db_session.add(site)
        wh = _make_webhook(
            "wh-gwfs2",
            site_id="site-gwfs2",
            enabled=False,
            events=["visit.agent_detected"],
        )
        db_session.add(wh)
        await db_session.flush()

        result = await get_webhooks_for_site(db_session, "site-gwfs2", "visit.agent_detected")
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_excludes_non_subscribed_event_types(self, db_session):
        site = _make_site("site-gwfs3")
        db_session.add(site)
        wh = _make_webhook(
            "wh-gwfs3",
            site_id="site-gwfs3",
            events=["test.critical_failure"],
        )
        db_session.add(wh)
        await db_session.flush()

        result = await get_webhooks_for_site(db_session, "site-gwfs3", "visit.agent_detected")
        assert len(result) == 0
