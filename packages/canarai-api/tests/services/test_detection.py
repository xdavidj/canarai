"""Tests for canarai.services.detection."""

import hashlib
import hmac as hmac_stdlib

import pytest

from canarai.schemas.ingest import DetectionData
from canarai.services.detection import (
    AGENT_UA_PATTERNS,
    classify_visit,
    detect_agent_from_headers,
    detect_agent_from_ua,
    hash_ip,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SECRET = "test-secret-key"


def _expected_hash(ip: str, secret: str) -> str:
    """Manually replicate the HMAC-SHA256 logic from hash_ip."""
    return hmac_stdlib.new(secret.encode(), ip.encode(), hashlib.sha256).hexdigest()[:16]


def _detection(**kwargs) -> DetectionData:
    """Build a DetectionData with sensible defaults."""
    defaults = {"confidence": 0.0, "classification": "human"}
    defaults.update(kwargs)
    return DetectionData(**defaults)


# ---------------------------------------------------------------------------
# hash_ip
# ---------------------------------------------------------------------------


class TestHashIp:
    """Tests for hash_ip()."""

    def test_deterministic_same_input_same_output(self):
        assert hash_ip("192.168.1.1", _SECRET) == hash_ip("192.168.1.1", _SECRET)

    def test_different_secrets_produce_different_hashes(self):
        h1 = hash_ip("10.0.0.1", "secret-a")
        h2 = hash_ip("10.0.0.1", "secret-b")
        assert h1 != h2

    def test_returns_16_hex_characters(self):
        result = hash_ip("1.2.3.4", _SECRET)
        assert len(result) == 16
        assert all(c in "0123456789abcdef" for c in result)

    def test_hmac_value_matches_manual_computation(self):
        ip = "203.0.113.42"
        expected = _expected_hash(ip, _SECRET)
        assert hash_ip(ip, _SECRET) == expected

    def test_different_ips_produce_different_hashes(self):
        assert hash_ip("1.2.3.4", _SECRET) != hash_ip("4.3.2.1", _SECRET)

    def test_ipv6_address_hashed(self):
        result = hash_ip("2001:db8::1", _SECRET)
        assert len(result) == 16


# ---------------------------------------------------------------------------
# detect_agent_from_ua — all 16 patterns
# ---------------------------------------------------------------------------


class TestDetectAgentFromUa:
    """Tests for detect_agent_from_ua() covering every AGENT_UA_PATTERNS entry."""

    @pytest.mark.parametrize(
        "user_agent,expected_family",
        [
            ("Mozilla/5.0 (compatible; GPTBot/1.0; +https://openai.com/gptbot)", "openai"),
            ("Mozilla/5.0 AppleWebKit/537.36 ChatGPT-User/1.0", "openai"),
            ("OAI-SearchBot/1.0", "openai"),
            ("Claude-Web/1.0", "anthropic"),
            ("Mozilla/5.0 (compatible; ClaudeBot/1.0; +https://www.anthropic.com)", "anthropic"),
            ("anthropic-ai/0.1 (crawler)", "anthropic"),
            ("Mozilla/5.0 (compatible; Google-Extended)", "google"),
            ("Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)", "google"),
            ("Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)", "microsoft"),
            ("Perplexity/1.0 (AI search)", "perplexity"),
            ("CCBot/2.0 (https://commoncrawl.org/faq/)", "commoncrawl"),
            ("cohere-ai/1.0", "cohere"),
            ("Meta-ExternalAgent/1.1 (https://developers.facebook.com/docs/sharing/)", "meta"),
            ("Bytespider; spider-feedback@bytedance.com", "bytedance"),
            ("Mozilla/5.0 (Linux; Android 5.0) PetalBot", "huawei"),
            ("Applebot-Extended/0.1", "apple"),
        ],
    )
    def test_known_pattern_detected(self, user_agent: str, expected_family: str):
        is_agent, family, confidence = detect_agent_from_ua(user_agent)
        assert is_agent is True
        assert family == expected_family
        assert confidence == 0.95

    def test_all_16_patterns_present(self):
        """Guard: AGENT_UA_PATTERNS must still have exactly 16 entries."""
        assert len(AGENT_UA_PATTERNS) == 16

    def test_case_insensitive_gptbot(self):
        is_agent, family, confidence = detect_agent_from_ua("gptbot/1.0")
        assert is_agent is True
        assert family == "openai"

    def test_case_insensitive_claudebot(self):
        is_agent, family, _ = detect_agent_from_ua("claudebot/1.0")
        assert is_agent is True
        assert family == "anthropic"

    def test_none_ua_returns_not_agent(self):
        is_agent, family, confidence = detect_agent_from_ua(None)
        assert is_agent is False
        assert family is None
        assert confidence == 0.0

    def test_empty_string_returns_not_agent(self):
        is_agent, family, confidence = detect_agent_from_ua("")
        assert is_agent is False
        assert family is None
        assert confidence == 0.0

    def test_normal_browser_ua_returns_not_agent(self):
        ua = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        is_agent, family, confidence = detect_agent_from_ua(ua)
        assert is_agent is False
        assert family is None
        assert confidence == 0.0

    def test_curl_user_agent_returns_not_agent(self):
        is_agent, family, confidence = detect_agent_from_ua("curl/7.88.1")
        assert is_agent is False
        assert family is None
        assert confidence == 0.0


# ---------------------------------------------------------------------------
# detect_agent_from_headers
# ---------------------------------------------------------------------------


class TestDetectAgentFromHeaders:
    """Tests for detect_agent_from_headers()."""

    def test_suspicious_openai_header_returns_true_with_boost(self):
        headers = {
            "x-openai-gptbot": "1",
            "accept": "*/*",
            "accept-language": "en-US",
        }
        is_agent, boost = detect_agent_from_headers(headers)
        assert is_agent is True
        assert boost == 0.3

    def test_suspicious_anthropic_header_returns_true_with_boost(self):
        headers = {"x-anthropic-request": "true"}
        is_agent, boost = detect_agent_from_headers(headers)
        assert is_agent is True
        assert boost == 0.3

    def test_suspicious_ai_crawler_header_returns_true_with_boost(self):
        headers = {"x-ai-crawler": "1"}
        is_agent, boost = detect_agent_from_headers(headers)
        assert is_agent is True
        assert boost == 0.3

    def test_missing_both_accept_headers_returns_false_with_small_boost(self):
        # Neither Accept nor Accept-Language present
        headers = {"host": "example.com"}
        is_agent, boost = detect_agent_from_headers(headers)
        assert is_agent is False
        assert boost == 0.1

    def test_missing_accept_language_only_returns_zero_boost(self):
        headers = {"accept": "*/*", "host": "example.com"}
        is_agent, boost = detect_agent_from_headers(headers)
        assert is_agent is False
        assert boost == 0.0

    def test_missing_accept_only_returns_zero_boost(self):
        headers = {"accept-language": "en-US", "host": "example.com"}
        is_agent, boost = detect_agent_from_headers(headers)
        assert is_agent is False
        assert boost == 0.0

    def test_normal_browser_headers_returns_false_zero_boost(self):
        headers = {
            "accept": "text/html,application/xhtml+xml",
            "accept-language": "en-US,en;q=0.9",
            "accept-encoding": "gzip, deflate, br",
            "user-agent": "Mozilla/5.0",
        }
        is_agent, boost = detect_agent_from_headers(headers)
        assert is_agent is False
        assert boost == 0.0

    def test_header_check_is_case_insensitive(self):
        # Suspicious header in uppercase
        headers = {"X-OpenAI-GPTBot": "1"}
        is_agent, boost = detect_agent_from_headers(headers)
        assert is_agent is True
        assert boost == 0.3

    def test_empty_headers_returns_false_small_boost(self):
        # No headers at all => missing both Accept and Accept-Language
        is_agent, boost = detect_agent_from_headers({})
        assert is_agent is False
        assert boost == 0.1


# ---------------------------------------------------------------------------
# classify_visit
# ---------------------------------------------------------------------------


class TestClassifyVisitConfidenceThresholds:
    """Tests for classification thresholds based on client confidence alone."""

    def test_confidence_0_49_classifies_as_human(self):
        detection = _detection(confidence=0.49)
        classification, family, final_conf = classify_visit(detection)
        assert classification == "human"
        assert final_conf == pytest.approx(0.49)

    def test_confidence_0_50_classifies_as_suspected_agent(self):
        detection = _detection(confidence=0.50)
        classification, _, _ = classify_visit(detection)
        assert classification == "suspected_agent"

    def test_confidence_0_69_classifies_as_suspected_agent(self):
        detection = _detection(confidence=0.69)
        classification, _, _ = classify_visit(detection)
        assert classification == "suspected_agent"

    def test_confidence_0_70_classifies_as_likely_agent(self):
        detection = _detection(confidence=0.70)
        classification, _, _ = classify_visit(detection)
        assert classification == "likely_agent"

    def test_confidence_0_84_classifies_as_likely_agent(self):
        detection = _detection(confidence=0.84)
        classification, _, _ = classify_visit(detection)
        assert classification == "likely_agent"

    def test_confidence_0_85_classifies_as_confirmed_agent(self):
        detection = _detection(confidence=0.85)
        classification, _, _ = classify_visit(detection)
        assert classification == "confirmed_agent"

    def test_confidence_1_0_classifies_as_confirmed_agent(self):
        detection = _detection(confidence=1.0)
        classification, _, _ = classify_visit(detection)
        assert classification == "confirmed_agent"

    def test_confidence_0_0_classifies_as_human(self):
        detection = _detection(confidence=0.0)
        classification, _, _ = classify_visit(detection)
        assert classification == "human"


class TestClassifyVisitUaOverride:
    """Tests for UA-based confidence upgrade."""

    def test_low_confidence_but_known_ua_upgrades_to_confirmed(self):
        detection = _detection(confidence=0.1)
        ua = "Mozilla/5.0 (compatible; GPTBot/1.0)"
        classification, family, confidence = classify_visit(detection, user_agent=ua)
        # UA gives 0.95 confidence -> confirmed_agent
        assert classification == "confirmed_agent"
        assert confidence == pytest.approx(0.95)
        assert family == "openai"

    def test_ua_detection_does_not_lower_confidence(self):
        # Client confidence is already 0.99 — UA detection should not lower it.
        detection = _detection(confidence=0.99)
        ua = "Mozilla/5.0 (compatible; GPTBot/1.0)"
        _, _, confidence = classify_visit(detection, user_agent=ua)
        assert confidence == pytest.approx(0.99)

    def test_agent_family_from_ua_when_client_has_none(self):
        detection = _detection(confidence=0.9, agent_family=None)
        ua = "ClaudeBot/1.0"
        _, family, _ = classify_visit(detection, user_agent=ua)
        assert family == "anthropic"

    def test_client_agent_family_not_overwritten_by_ua(self):
        detection = _detection(confidence=0.9, agent_family="custom-family")
        ua = "Mozilla/5.0 (compatible; GPTBot/1.0)"
        _, family, _ = classify_visit(detection, user_agent=ua)
        # Client-supplied family takes precedence over UA-derived family
        assert family == "custom-family"

    def test_none_ua_no_change_to_confidence(self):
        detection = _detection(confidence=0.6)
        classification, _, confidence = classify_visit(detection, user_agent=None)
        assert classification == "suspected_agent"
        assert confidence == pytest.approx(0.6)


class TestClassifyVisitHeaderBoost:
    """Tests for header-based confidence boost."""

    def test_suspicious_header_boosts_confidence(self):
        # Start below 0.50; the 0.3 boost from suspicious header should push
        # confidence to 0.5 + 0.3 = 0.69 -> suspected_agent.
        detection = _detection(confidence=0.30)
        headers = {"x-openai-gptbot": "1", "accept": "*/*", "accept-language": "en"}
        classification, _, confidence = classify_visit(detection, headers=headers)
        assert confidence == pytest.approx(0.60)
        assert classification == "suspected_agent"

    def test_header_boost_capped_at_1_0(self):
        detection = _detection(confidence=0.9)
        headers = {"x-openai-gptbot": "1"}
        _, _, confidence = classify_visit(detection, headers=headers)
        assert confidence == pytest.approx(1.0)

    def test_non_suspicious_headers_no_boost(self):
        detection = _detection(confidence=0.4)
        headers = {"accept": "*/*", "accept-language": "en-US"}
        _, _, confidence = classify_visit(detection, headers=headers)
        assert confidence == pytest.approx(0.4)

    def test_none_headers_no_boost(self):
        detection = _detection(confidence=0.4)
        _, _, confidence = classify_visit(detection, headers=None)
        assert confidence == pytest.approx(0.4)


class TestClassifyVisitCombined:
    """Tests combining client confidence, UA, and headers."""

    def test_combined_ua_and_headers_produce_confirmed_agent(self):
        # Client confidence: 0.55 (suspected_agent)
        # UA match -> max(0.55, 0.95) = 0.95
        # Suspicious header -> min(1.0, 0.95 + 0.3) = 1.0
        detection = _detection(confidence=0.55)
        ua = "Mozilla/5.0 (compatible; GPTBot/1.0)"
        headers = {"x-openai-gptbot": "1", "accept-language": "en"}
        classification, family, confidence = classify_visit(
            detection, user_agent=ua, headers=headers
        )
        assert classification == "confirmed_agent"
        assert confidence == pytest.approx(1.0)
        assert family == "openai"

    def test_human_with_no_ua_no_headers(self):
        detection = _detection(confidence=0.1)
        classification, family, confidence = classify_visit(detection)
        assert classification == "human"
        assert family is None
        assert confidence == pytest.approx(0.1)

    def test_agent_family_propagates_from_detection_data(self):
        detection = _detection(confidence=0.9, agent_family="perplexity")
        classification, family, _ = classify_visit(detection)
        assert family == "perplexity"
        assert classification == "confirmed_agent"
