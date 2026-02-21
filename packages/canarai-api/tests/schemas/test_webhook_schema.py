"""Tests for canarai.schemas.webhook.WebhookCreate — focusing on SSRF prevention."""

import pytest
from pydantic import ValidationError

from canarai.schemas.webhook import WebhookCreate


def _make(url: str) -> WebhookCreate:
    """Helper to construct a WebhookCreate with the given URL."""
    return WebhookCreate(site_id="site-abc", url=url)


def _assert_blocked(url: str) -> None:
    """Assert that the given URL is rejected by validation."""
    with pytest.raises(ValidationError):
        _make(url)


# ---------------------------------------------------------------------------
# Valid URLs
# ---------------------------------------------------------------------------


class TestWebhookCreateValidUrls:
    """URLs that must pass validation."""

    def test_https_url_accepted(self):
        wh = _make("https://example.com/webhook")
        assert wh.url == "https://example.com/webhook"

    def test_http_url_accepted(self):
        wh = _make("http://example.com/webhook")
        assert wh.url == "http://example.com/webhook"

    def test_https_with_custom_port_accepted(self):
        wh = _make("https://hooks.example.com:8080/path")
        assert "8080" in wh.url

    def test_slack_webhook_url_accepted(self):
        wh = _make("https://hooks.slack.com/services/xxx/yyy/zzz")
        assert wh.url.startswith("https://hooks.slack.com")

    def test_public_hostname_accepted(self):
        wh = _make("https://api.mycompany.io/webhooks/receive")
        assert wh.url.startswith("https://")


# ---------------------------------------------------------------------------
# Non-HTTP schemes
# ---------------------------------------------------------------------------


class TestWebhookCreateBlockedSchemes:
    """Non-HTTP/HTTPS schemes must be rejected."""

    def test_ftp_scheme_rejected(self):
        _assert_blocked("ftp://example.com/hook")

    def test_file_scheme_rejected(self):
        _assert_blocked("file:///etc/passwd")

    def test_javascript_scheme_rejected(self):
        _assert_blocked("javascript:alert(1)")

    def test_missing_scheme_rejected(self):
        _assert_blocked("example.com/webhook")


# ---------------------------------------------------------------------------
# Private / loopback / link-local IPv4
# ---------------------------------------------------------------------------


class TestWebhookCreateBlockedPrivateIPv4:
    """Private and loopback IPv4 addresses must be rejected."""

    def test_10_0_0_1_rejected(self):
        _assert_blocked("https://10.0.0.1/hook")

    def test_192_168_1_1_rejected(self):
        _assert_blocked("https://192.168.1.1/hook")

    def test_172_16_0_1_rejected(self):
        _assert_blocked("https://172.16.0.1/hook")

    def test_127_0_0_1_rejected(self):
        _assert_blocked("https://127.0.0.1/hook")

    def test_link_local_169_254_1_1_rejected(self):
        _assert_blocked("https://169.254.1.1/hook")


# ---------------------------------------------------------------------------
# IPv6 loopback / link-local
# ---------------------------------------------------------------------------


class TestWebhookCreateBlockedIPv6:
    """IPv6 loopback addresses must be rejected."""

    def test_ipv6_loopback_rejected(self):
        _assert_blocked("http://[::1]/hook")


# ---------------------------------------------------------------------------
# Cloud metadata endpoints
# ---------------------------------------------------------------------------


class TestWebhookCreateBlockedMetadata:
    """Cloud metadata service addresses must be rejected."""

    def test_aws_imds_ip_rejected(self):
        _assert_blocked("https://169.254.169.254/latest/meta-data/")

    def test_google_metadata_hostname_rejected(self):
        _assert_blocked("https://metadata.google.internal/computeMetadata/v1/")

    def test_alibaba_metadata_ip_rejected(self):
        _assert_blocked("https://100.100.100.200/latest/meta-data/")


# ---------------------------------------------------------------------------
# Hostname / structural edge cases
# ---------------------------------------------------------------------------


class TestWebhookCreateStructuralEdgeCases:
    """Edge cases around URL structure."""

    def test_empty_hostname_rejected(self):
        _assert_blocked("http:///path")

    def test_very_long_url_rejected(self):
        long_path = "a" * 2048
        _assert_blocked(f"https://example.com/{long_path}")

    def test_url_with_basic_auth_component_accepted(self):
        # Authentication in URL is a separate concern; the hostname is public so
        # SSRF validation should pass (the URL is structurally valid).
        wh = _make("https://user:pass@hooks.example.com/endpoint")
        assert wh.url.startswith("https://")
