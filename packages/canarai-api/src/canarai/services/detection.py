"""Server-side agent classification service.

Validates and enhances client-side detection signals using server-side
information such as HTTP headers and IP analysis.
"""

import hashlib
import hmac as hmac_module
import re

from canarai.schemas.ingest import DetectionData

# Known AI agent user-agent patterns
AGENT_UA_PATTERNS: list[tuple[str, str]] = [
    (r"GPTBot", "openai"),
    (r"ChatGPT-User", "openai"),
    (r"OAI-SearchBot", "openai"),
    (r"Claude-Web", "anthropic"),
    (r"ClaudeBot", "anthropic"),
    (r"anthropic-ai", "anthropic"),
    (r"Google-Extended", "google"),
    (r"Googlebot", "google"),
    (r"Bingbot", "microsoft"),
    (r"Perplexity", "perplexity"),
    (r"CCBot", "commoncrawl"),
    (r"cohere-ai", "cohere"),
    (r"Meta-ExternalAgent", "meta"),
    (r"Bytespider", "bytedance"),
    (r"PetalBot", "huawei"),
    (r"Applebot-Extended", "apple"),
]

# Headers that suggest automated/agent traffic
SUSPICIOUS_HEADERS = {
    "x-openai-gptbot",
    "x-anthropic-request",
    "x-ai-crawler",
}

CLASSIFICATION_THRESHOLDS = {
    "confirmed_agent": 0.85,
    "likely_agent": 0.70,
    "suspected_agent": 0.50,
    "human": 0.0,
}


def hash_ip(ip: str, secret: str | None = None) -> str:
    """HMAC-hash an IP address for privacy-preserving storage.

    Uses HMAC with the server secret so the hash cannot be brute-forced
    without knowing the key (plain SHA-256 of IPv4 is trivially reversible).
    """
    if secret is None:
        from canarai.config import get_settings
        secret = get_settings().api_secret_key
    return hmac_module.new(secret.encode(), ip.encode(), hashlib.sha256).hexdigest()[:16]


def detect_agent_from_ua(user_agent: str | None) -> tuple[bool, str | None, float]:
    """Check user-agent string against known AI agent patterns.

    Returns (is_agent, agent_family, confidence).
    """
    if not user_agent:
        return False, None, 0.0

    for pattern, family in AGENT_UA_PATTERNS:
        if re.search(pattern, user_agent, re.IGNORECASE):
            return True, family, 0.95

    return False, None, 0.0


def detect_agent_from_headers(headers: dict[str, str]) -> tuple[bool, float]:
    """Check request headers for known agent indicators.

    Returns (is_agent, confidence_boost).
    """
    lower_headers = {k.lower() for k in headers}
    matches = lower_headers & SUSPICIOUS_HEADERS

    if matches:
        return True, 0.3

    # No Accept-Language or Accept headers is mildly suspicious
    missing_human_headers = 0
    if "accept-language" not in lower_headers:
        missing_human_headers += 1
    if "accept" not in lower_headers:
        missing_human_headers += 1

    if missing_human_headers == 2:
        return False, 0.1

    return False, 0.0


def classify_visit(
    client_detection: DetectionData,
    user_agent: str | None = None,
    headers: dict[str, str] | None = None,
    ip: str | None = None,
) -> tuple[str, str | None, float]:
    """Classify a visit by combining client and server-side signals.

    Returns (classification, agent_family, final_confidence).
    """
    confidence = client_detection.confidence
    agent_family = client_detection.agent_family

    # Server-side UA check
    ua_is_agent, ua_family, ua_confidence = detect_agent_from_ua(user_agent)
    if ua_is_agent:
        confidence = max(confidence, ua_confidence)
        if not agent_family:
            agent_family = ua_family

    # Server-side header check
    if headers:
        header_is_agent, header_boost = detect_agent_from_headers(headers)
        if header_is_agent:
            confidence = min(1.0, confidence + header_boost)

    # Determine classification from confidence
    classification = "human"
    for label, threshold in CLASSIFICATION_THRESHOLDS.items():
        if confidence >= threshold:
            classification = label
            break

    return classification, agent_family, confidence
