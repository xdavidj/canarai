# API Reference

Complete reference for the Canary API. All endpoints are versioned under `/v1/` unless otherwise noted.

---

## Authentication

Canary uses two types of credentials:

### Site Keys (Public)

Site keys have the prefix `cy_live_` (production) or `cy_test_` (testing) followed by 20 alphanumeric characters.

Site keys are embedded in client-side code and sent as part of the ingest payload body. They identify which site a visit belongs to but do not grant management access.

### API Keys (Secret)

API keys have the prefix `cy_sk_` followed by 40 alphanumeric characters.

API keys are sent as Bearer tokens in the `Authorization` header. They grant full management access to the associated site.

```
Authorization: Bearer cy_sk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Keep API keys secret. Never embed them in client-side code.

---

## Base URL

| Environment | Base URL |
|-------------|----------|
| Self-hosted | `http://localhost:8787` |
| Hosted | `https://api.canar.ai` |

All examples below use `http://localhost:8787`. Replace with your actual base URL.

---

## Endpoints

### GET /health

Health check endpoint. No authentication required.

**Request:**

```bash
curl http://localhost:8787/health
```

**Response:**

```json
{
  "status": "ok"
}
```

| Status | Description |
|--------|-------------|
| 200 | Server is healthy |

---

### POST /v1/ingest

Receive detection results and test outcomes from the embedded script. Authenticated via site key in the request body.

**Request:**

```bash
curl -X POST http://localhost:8787/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "v": 1,
    "site_key": "cy_live_xxxxxxxxxxxxxxxxxxxx",
    "visit_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2026-02-21T12:00:00Z",
    "page_url": "https://example.com/page",
    "detection": {
      "is_agent": true,
      "confidence": 0.92,
      "classification": "confirmed_agent",
      "agent_family": "OpenAI ChatGPT",
      "signals": [
        {"signal": "ua_match", "value": "ChatGPT-User", "confidence": 1.0},
        {"signal": "webdriver", "value": true, "confidence": 0.9}
      ]
    },
    "test_results": [
      {
        "test_id": "CAN-0001",
        "test_version": "1.0",
        "delivery_method": "css_display_none",
        "outcome": "full_compliance",
        "evidence": {
          "canary_token_observed": true,
          "response_time_ms": 340
        },
        "injected_at": "2026-02-21T12:00:01Z",
        "observed_at": "2026-02-21T12:00:01.340Z"
      }
    ]
  }'
```

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `v` | integer | Yes | Payload version (currently `1`) |
| `site_key` | string | Yes | Site key identifying the monitored site |
| `visit_id` | string | Yes | Unique visit identifier (UUID v4) |
| `timestamp` | string | Yes | ISO 8601 timestamp of the visit |
| `page_url` | string | Yes | Full URL of the visited page |
| `detection` | object | Yes | Detection results (see below) |
| `test_results` | array | No | Array of test outcomes (see below) |

**Detection Object:**

| Field | Type | Description |
|-------|------|-------------|
| `is_agent` | boolean | Whether the visitor was classified as an agent |
| `confidence` | float | Confidence score (0.0-1.0) |
| `classification` | string | `confirmed_agent`, `likely_agent`, `suspected_agent`, or `human` |
| `agent_family` | string | Detected agent family (e.g., "OpenAI ChatGPT") |
| `signals` | array | Detection signals with signal name, value, and confidence |

**Test Result Object:**

| Field | Type | Description |
|-------|------|-------------|
| `test_id` | string | Test ID in `CAN-XXXX` format |
| `test_version` | string | Version of the test that was run |
| `delivery_method` | string | How the payload was injected |
| `outcome` | string | `exfiltration_attempted`, `full_compliance`, `partial_compliance`, `acknowledged`, or `ignored` |
| `evidence` | object | Supporting evidence (canary token observations, timing, mutations) |
| `injected_at` | string | ISO 8601 timestamp of injection |
| `observed_at` | string | ISO 8601 timestamp of first observation |

**Response (200):**

```json
{
  "status": "accepted",
  "visit_id": "550e8400-e29b-41d4-a716-446655440000",
  "results_recorded": 1
}
```

| Status | Description |
|--------|-------------|
| 200 | Payload accepted and processed |
| 400 | Invalid payload (validation error) |
| 404 | Site key not found or site is inactive |
| 409 | Duplicate visit_id (replay protection) |

---

### GET /v1/config/{site_key}

Fetch the test configuration for a site. Called by the embedded script to determine which tests to run.

**Request:**

```bash
curl http://localhost:8787/v1/config/cy_live_xxxxxxxxxxxxxxxxxxxx
```

**Response (200):**

```json
{
  "site_key": "cy_live_xxxxxxxxxxxxxxxxxxxx",
  "enabled": true,
  "detection_threshold": 0.5,
  "tests": [
    {
      "test_id": "CAN-0001",
      "version": "1.0",
      "delivery_methods": ["css_display_none"],
      "payload_template": null
    },
    {
      "test_id": "CAN-0002",
      "version": "1.0",
      "delivery_methods": ["html_comment"],
      "payload_template": null
    }
  ],
  "delivery_methods": ["html_comment", "meta_tag", "css_display_none"],
  "ingest_url": "http://localhost:8787/v1/ingest",
  "script_version": "0.1.0"
}
```

| Status | Description |
|--------|-------------|
| 200 | Configuration returned |
| 404 | Site key not found or site is inactive |

---

### POST /v1/sites

Create a new monitored site. Returns the site details, a site key, and an API key.

**The API key is only returned once.** Store it securely.

**Request:**

```bash
curl -X POST http://localhost:8787/v1/sites \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "example.com",
    "config": {
      "enabled_tests": ["CAN-0001", "CAN-0002", "CAN-0003", "CAN-0004"],
      "detection_threshold": 0.5,
      "delivery_methods": ["css_display_none", "meta_tag", "json_ld"]
    },
    "environment": "live"
  }'
```

**Request Body:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `domain` | string | Yes | -- | Domain name (1-255 characters) |
| `config.enabled_tests` | string[] | No | `["CAN-0001", "CAN-0002", "CAN-0003"]` | Test IDs to enable |
| `config.detection_threshold` | float | No | `0.5` | Minimum confidence to trigger tests (0.0-1.0) |
| `config.delivery_methods` | string[] | No | `["html_comment", "meta_tag", "http_header"]` | Allowed delivery methods |
| `environment` | string | No | `"live"` | `"live"` or `"test"` |

**Response (201):**

```json
{
  "site": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "site_key": "cy_live_aBcDeFgHiJkLmNoPqRsT",
    "domain": "example.com",
    "config": {
      "enabled_tests": ["CAN-0001", "CAN-0002", "CAN-0003", "CAN-0004"],
      "detection_threshold": 0.5,
      "delivery_methods": ["css_display_none", "meta_tag", "json_ld"]
    },
    "is_active": true,
    "created_at": "2026-02-21T12:00:00Z",
    "updated_at": "2026-02-21T12:00:00Z"
  },
  "api_key": "cy_sk_aBcDeFgHiJkLmNoPqRsTuVwXyZaBcDeFgHiJkLmN",
  "api_key_prefix": "cy_sk_aB"
}
```

| Status | Description |
|--------|-------------|
| 201 | Site created successfully |
| 400 | Invalid request body |
| 409 | Domain already registered |

---

### GET /v1/sites

List all sites associated with the authenticated API key.

**Request:**

```bash
curl -H "Authorization: Bearer cy_sk_..." http://localhost:8787/v1/sites
```

**Response (200):**

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "site_key": "cy_live_aBcDeFgHiJkLmNoPqRsT",
    "domain": "example.com",
    "config": {
      "enabled_tests": ["CAN-0001", "CAN-0002", "CAN-0003"],
      "detection_threshold": 0.5,
      "delivery_methods": ["html_comment", "meta_tag"]
    },
    "is_active": true,
    "created_at": "2026-02-21T12:00:00Z",
    "updated_at": "2026-02-21T12:00:00Z"
  }
]
```

| Status | Description |
|--------|-------------|
| 200 | Sites returned |
| 401 | Missing or invalid API key |

---

### PATCH /v1/sites/{id}

Update a site's configuration. Only provided fields are updated.

**Request:**

```bash
curl -X PATCH http://localhost:8787/v1/sites/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer cy_sk_..." \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "enabled_tests": ["CAN-0001", "CAN-0002", "CAN-0003", "CAN-0004", "CAN-0008"],
      "detection_threshold": 0.70
    }
  }'
```

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `domain` | string | No | New domain name |
| `config` | object | No | Updated configuration (replaces entire config) |
| `is_active` | boolean | No | Enable or disable the site |

**Response (200):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "site_key": "cy_live_aBcDeFgHiJkLmNoPqRsT",
  "domain": "example.com",
  "config": {
    "enabled_tests": ["CAN-0001", "CAN-0002", "CAN-0003", "CAN-0004", "CAN-0008"],
    "detection_threshold": 0.70,
    "delivery_methods": ["html_comment", "meta_tag"]
  },
  "is_active": true,
  "created_at": "2026-02-21T12:00:00Z",
  "updated_at": "2026-02-21T14:30:00Z"
}
```

| Status | Description |
|--------|-------------|
| 200 | Site updated |
| 400 | Invalid request body |
| 401 | Missing or invalid API key |
| 404 | Site not found |

---

### GET /v1/results

Query test results with optional filtering and pagination.

**Request:**

```bash
# All results
curl -H "Authorization: Bearer cy_sk_..." http://localhost:8787/v1/results

# Filter by classification
curl -H "Authorization: Bearer cy_sk_..." \
  "http://localhost:8787/v1/results?classification=confirmed_agent"

# Filter by test ID and date range
curl -H "Authorization: Bearer cy_sk_..." \
  "http://localhost:8787/v1/results?test_id=CAN-0001&date_from=2026-02-01T00:00:00Z&limit=10"

# Filter by outcome
curl -H "Authorization: Bearer cy_sk_..." \
  "http://localhost:8787/v1/results?outcome=exfiltration_attempted"
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `site_id` | string | (all) | Filter by site UUID |
| `test_id` | string | (all) | Filter by test ID (e.g., `CAN-0001`) |
| `classification` | string | (all) | Filter by visit classification |
| `outcome` | string | (all) | Filter by test outcome |
| `date_from` | datetime | (none) | Start of date range (ISO 8601) |
| `date_to` | datetime | (none) | End of date range (ISO 8601) |
| `limit` | integer | 50 | Number of results to return (1-500) |
| `offset` | integer | 0 | Number of results to skip |

**Response (200):**

```json
[
  {
    "id": "visit-uuid",
    "visit_id": "550e8400-e29b-41d4-a716-446655440000",
    "site_id": "site-uuid",
    "page_url": "https://example.com/page",
    "timestamp": "2026-02-21T12:00:00Z",
    "user_agent": "Mozilla/5.0 ChatGPT-User ...",
    "classification": "confirmed_agent",
    "agent_family": "OpenAI ChatGPT",
    "test_results": [
      {
        "id": "result-uuid",
        "visit_id": "550e8400-e29b-41d4-a716-446655440000",
        "test_id": "CAN-0001",
        "test_version": "1.0",
        "delivery_method": "css_display_none",
        "outcome": "full_compliance",
        "score": 75,
        "evidence": {
          "canary_token_observed": true,
          "response_time_ms": 340
        },
        "injected_at": "2026-02-21T12:00:01Z",
        "observed_at": "2026-02-21T12:00:01.340Z",
        "created_at": "2026-02-21T12:00:02Z"
      }
    ],
    "created_at": "2026-02-21T12:00:02Z"
  }
]
```

| Status | Description |
|--------|-------------|
| 200 | Results returned |
| 401 | Missing or invalid API key |

---

### GET /v1/results/summary

Get aggregate statistics across all test results.

**Request:**

```bash
curl -H "Authorization: Bearer cy_sk_..." http://localhost:8787/v1/results/summary

# With date range
curl -H "Authorization: Bearer cy_sk_..." \
  "http://localhost:8787/v1/results/summary?date_from=2026-02-01T00:00:00Z"
```

**Query Parameters:**

Same filtering parameters as `GET /v1/results` (except `limit` and `offset`).

**Response (200):**

```json
{
  "total_visits": 1247,
  "agent_visits": 342,
  "human_visits": 905,
  "total_tests": 1368,
  "resilience_score": 42.5,
  "critical_failure_rate": 8.3,
  "outcomes": {
    "ignored": 624,
    "acknowledged": 198,
    "partial_compliance": 287,
    "full_compliance": 145,
    "exfiltration_attempted": 114
  },
  "top_agent_families": [
    {"family": "OpenAI ChatGPT", "count": 156},
    {"family": "Anthropic Claude", "count": 89},
    {"family": "Perplexity", "count": 52},
    {"family": "Google Gemini", "count": 28},
    {"family": "Headless Chrome", "count": 17}
  ]
}
```

**Field Descriptions:**

| Field | Description |
|-------|-------------|
| `resilience_score` | Average score across all tests (0-100). Higher means more vulnerable. |
| `critical_failure_rate` | Percentage of tests resulting in `exfiltration_attempted` (0-100). |
| `outcomes` | Count of each outcome type across all tests. |
| `top_agent_families` | Most frequently detected agent families, sorted by count. |

| Status | Description |
|--------|-------------|
| 200 | Summary returned |
| 401 | Missing or invalid API key |

---

### POST /v1/webhooks

Register a new webhook endpoint to receive event notifications.

**Request:**

```bash
curl -X POST http://localhost:8787/v1/webhooks \
  -H "Authorization: Bearer cy_sk_..." \
  -H "Content-Type: application/json" \
  -d '{
    "site_id": "550e8400-e29b-41d4-a716-446655440000",
    "url": "https://hooks.slack.com/services/T.../B.../xxx",
    "events": ["visit.agent_detected", "test.critical_failure"]
  }'
```

**Request Body:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `site_id` | string | Yes | -- | UUID of the site to monitor |
| `url` | string | Yes | -- | Webhook endpoint URL |
| `events` | string[] | No | `["visit.agent_detected", "test.critical_failure"]` | Event types to subscribe to |

**Response (201):**

```json
{
  "id": "webhook-uuid",
  "site_id": "550e8400-e29b-41d4-a716-446655440000",
  "url": "https://hooks.slack.com/services/T.../B.../xxx",
  "events": ["visit.agent_detected", "test.critical_failure"],
  "enabled": true,
  "created_at": "2026-02-21T12:00:00Z"
}
```

| Status | Description |
|--------|-------------|
| 201 | Webhook created |
| 400 | Invalid request body |
| 401 | Missing or invalid API key |
| 404 | Site not found |

---

### POST /v1/webhooks/{id}/test

Send a test payload to verify that the webhook endpoint is reachable and correctly configured.

**Request:**

```bash
curl -X POST http://localhost:8787/v1/webhooks/webhook-uuid/test \
  -H "Authorization: Bearer cy_sk_..."
```

**Response (200):**

```json
{
  "success": true,
  "status_code": 200,
  "error": null
}
```

**Response (200, failure):**

```json
{
  "success": false,
  "status_code": 500,
  "error": null
}
```

**Response (200, connection error):**

```json
{
  "success": false,
  "status_code": null,
  "error": "Request timed out"
}
```

| Status | Description |
|--------|-------------|
| 200 | Test completed (check `success` field) |
| 401 | Missing or invalid API key |
| 404 | Webhook not found |

---

### GET /v1/feed/agents (Hosted Only)

Get cross-site agent intelligence data. This endpoint aggregates anonymized agent detection data across all sites on the hosted platform.

**Request:**

```bash
curl -H "Authorization: Bearer cy_sk_..." https://api.canar.ai/v1/feed/agents
```

**Response (200):**

```json
{
  "agents": [
    {
      "family": "OpenAI ChatGPT",
      "first_seen": "2026-01-15T08:00:00Z",
      "last_seen": "2026-02-21T11:45:00Z",
      "total_visits": 15420,
      "unique_sites": 342,
      "avg_resilience_score": 38.2,
      "common_outcomes": {
        "ignored": 0.45,
        "acknowledged": 0.15,
        "partial_compliance": 0.22,
        "full_compliance": 0.12,
        "exfiltration_attempted": 0.06
      }
    }
  ],
  "updated_at": "2026-02-21T12:00:00Z"
}
```

| Status | Description |
|--------|-------------|
| 200 | Agent feed returned |
| 401 | Missing or invalid API key |
| 403 | Not available on self-hosted deployments |

---

### GET /v1/feed/trends (Hosted Only)

Get trend analysis showing how agent behavior changes over time.

**Request:**

```bash
curl -H "Authorization: Bearer cy_sk_..." \
  "https://api.canar.ai/v1/feed/trends?period=7d"
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `period` | string | `7d` | Time period: `24h`, `7d`, `30d`, `90d` |

**Response (200):**

```json
{
  "period": "7d",
  "data_points": [
    {
      "date": "2026-02-15",
      "total_agent_visits": 2340,
      "avg_resilience_score": 41.2,
      "critical_failure_rate": 7.8,
      "top_agents": ["OpenAI ChatGPT", "Anthropic Claude", "Perplexity"]
    },
    {
      "date": "2026-02-16",
      "total_agent_visits": 2518,
      "avg_resilience_score": 40.1,
      "critical_failure_rate": 7.5,
      "top_agents": ["OpenAI ChatGPT", "Anthropic Claude", "Google Gemini"]
    }
  ],
  "updated_at": "2026-02-21T12:00:00Z"
}
```

| Status | Description |
|--------|-------------|
| 200 | Trends returned |
| 401 | Missing or invalid API key |
| 403 | Not available on self-hosted deployments |

---

## Error Responses

All error responses follow a consistent format:

```json
{
  "detail": "Human-readable error description"
}
```

### Common Status Codes

| Status | Description |
|--------|-------------|
| 400 | Bad request -- invalid JSON or failed validation |
| 401 | Unauthorized -- missing or invalid API key |
| 403 | Forbidden -- endpoint not available in this deployment mode |
| 404 | Not found -- resource does not exist |
| 409 | Conflict -- duplicate resource (e.g., visit_id already exists) |
| 422 | Unprocessable entity -- valid JSON but semantically invalid |
| 429 | Rate limited -- too many requests (requires Redis) |
| 500 | Internal server error |

---

## Rate Limiting

Rate limiting is available when Redis is configured (`REDIS_URL` environment variable).

| Endpoint | Limit |
|----------|-------|
| `POST /v1/ingest` | 100 requests per minute per site key |
| `GET /v1/config/{site_key}` | 60 requests per minute per site key |
| All management endpoints | 30 requests per minute per API key |

When rate limited, the response includes:

```
HTTP/1.1 429 Too Many Requests
Retry-After: 12
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1708520412
```
