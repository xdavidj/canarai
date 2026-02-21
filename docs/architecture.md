# Architecture

This document covers the technical architecture of Canary, including the detection pipeline, test injection engine, observation system, reporting mechanism, API design, database schema, and security model.

---

## System Overview

```
 +------------------------------------------------------+
 |                     YOUR WEBSITE                      |
 |                                                       |
 |  +------------------+   +-------------------------+  |
 |  | Page Content     |   | <script src="canary.js"> |  |
 |  | (HTML/CSS/JS)    |   | data-canary-site-key="."|  |
 |  +------------------+   +------------+------------+  |
 |                                      |                |
 +--------------------------------------+----------------+
                                        |
              +-------------------------v--------------------------+
              |              CANARY SCRIPT (client-side)           |
              |                                                    |
              |  1. Detection       2. Config        3. Injection  |
              |  +-----------+   +-----------+   +-----------+     |
              |  | UA Match  |   | GET /v1/  |   | DOM-based |     |
              |  | Finger-   |-->| config/   |-->| Meta/LD   |     |
              |  | print     |   | {site_key}|   | CSS-based |     |
              |  | Behavioral|   +-----------+   +-----------+     |
              |  +-----------+                        |            |
              |                   4. Observation      |            |
              |                   +-----------+       |            |
              |                   | Mutation  |<------+            |
              |                   | Observer  |                    |
              |                   | Network   |                    |
              |                   | Timing    |                    |
              |                   +-----+-----+                    |
              |                         |                          |
              |  5. Reporting           |                          |
              |  +-----------+          |                          |
              |  | sendBeacon|<---------+                          |
              |  | fetch     |                                     |
              |  | pixel     |                                     |
              |  +-----+-----+                                     |
              +--------+-----------------------------------------------+
                       |
                       v
              +--------+-----------------------------------------------+
              |              CANARY API (server-side)                   |
              |                                                        |
              |  +-------------+  +-----------+  +-----------+         |
              |  | POST /v1/   |  | Server-   |  | Scoring   |         |
              |  | ingest      |->| side      |->| Engine    |         |
              |  +-------------+  | detection |  +-----------+         |
              |                   +-----------+       |                |
              |                                       v                |
              |  +-----------+  +-----------+  +-----------+           |
              |  | Webhook   |<-| Database  |<-| Store     |           |
              |  | Dispatch  |  | (SQLite/  |  | results   |           |
              |  |           |  |  Postgres)|  |           |           |
              |  +-----+-----+  +-----------+  +-----------+           |
              +--------+-----------------------------------------------+
                       |
                       v
              +-----------+
              | Slack     |
              | Discord   |
              | Custom    |
              +-----------+
```

---

## Detection Pipeline

The detection pipeline runs entirely client-side in the embedded script. It combines four signal categories into a weighted confidence score.

### Signal Categories

| Category | Weight | Method | Signals |
|----------|--------|--------|---------|
| User-Agent | 40% | Regex matching against known AI agent UA strings | `ClaudeBot`, `GPTBot`, `ChatGPT-User`, `PerplexityBot`, `HeadlessChrome`, etc. |
| Fingerprint | 25% | Browser environment probing | `navigator.webdriver`, Chrome runtime, plugins, screen dimensions, languages, Notification API, CDP detection, permissions, connection API, window dimensions |
| Behavioral | 25% | Interaction observation over ~2.5s window | Mouse movement, scroll patterns, click timing, touch events, interaction rate |
| Network | 10% | Reserved for server-side enrichment | HTTP headers, IP analysis (applied server-side at ingest) |

### Scoring

Each category produces a score from 0.0 (human) to 1.0 (automated). The weighted average determines the final confidence:

```
confidence = (ua * 0.40 + fp * 0.25 + bh * 0.25) / 0.90
```

The network weight (0.10) is excluded client-side and applied server-side during ingest processing.

### Classification Thresholds

| Confidence | Classification | Action |
|------------|---------------|--------|
| >= 0.85 | `confirmed_agent` | Inject all enabled tests |
| >= 0.70 | `likely_agent` | Inject all enabled tests |
| >= 0.50 | `suspected_agent` | Inject all enabled tests |
| < 0.50 | `human` | No action, no reporting |

### Short-Circuit Paths

Two short-circuit paths exist for efficiency:

1. **Known crawler**: If the UA matches a traditional search crawler (Googlebot, Bingbot, DuckDuckBot, etc.), detection immediately returns `human` with confidence 0. These crawlers are not AI agents and should not be tested.

2. **Known AI agent UA**: If the UA matches a known AI agent pattern (GPTBot, ClaudeBot, etc.), detection immediately returns `confirmed_agent` with confidence 1.0. Fingerprint signals are still collected for data richness, but the behavioral observation window is skipped.

### Fingerprint Checks

The fingerprint analyzer runs 10 checks, each contributing points to a maximum of 10:

| Check | Points | Description |
|-------|--------|-------------|
| `navigator.webdriver` | 3 | Set to `true` by WebDriver-compliant tools |
| Chrome runtime missing | 1 | `window.chrome` exists but `chrome.runtime` is empty |
| No browser plugins | 1 | `navigator.plugins.length === 0` |
| Suspicious screen dimensions | 1 | 0x0, 800x600, or <300px in either dimension |
| Empty languages | 1 | `navigator.languages` missing or empty |
| Notification API missing | 1 | `typeof Notification === 'undefined'` |
| CDP detected | 3 | `$cdc_` properties, Puppeteer/Playwright globals |
| Permissions API anomaly | 1 | Missing or non-functional `navigator.permissions` |
| Connection API missing | 1 | Missing in Chrome UA (expected in real Chrome) |
| Window dimension anomaly | 1 | `outerWidth === innerWidth` (no browser chrome) |

The headless flag is set if `webdriver` or `cdp` are detected, or if 4+ checks fire.

### Behavioral Analysis

The behavioral observer runs for a configurable window (default 2500ms) and tracks:

- Mouse movement count and timing regularity
- Scroll event count and patterns (instant jump to bottom)
- Click timing variance (perfectly regular intervals indicate automation)
- Keyboard events
- Touch events
- Time to first interaction

Anomaly signals and their point values:

| Anomaly | Points | Trigger |
|---------|--------|---------|
| `no_mouse_movement` | 3 | No mouse events on non-touch device |
| `zero_interactions` | 2 | No events of any kind during window |
| `instant_scroll_to_bottom` | 2 | Scrolled >90% of page in <=3 scroll events |
| `perfectly_timed_clicks` | 2 | Click interval coefficient of variation <5% |
| `robotic_mouse_movement` | 1 | Mouse movement interval CV <3% |
| `instant_first_interaction` | 2 | First interaction <50ms after page load |
| `excessive_interaction_rate` | 1 | >100 events per second |

---

## Test Injection Engine

After detection, the injection engine takes a list of test payloads and inserts them into the page DOM.

### Delivery Methods

The engine supports 17 delivery methods across three injector modules:

**DOM Injector** (`inject/dom.ts`):

| Method | HTML Element | Hiding Technique |
|--------|-------------|------------------|
| `css_display_none` | `<div>` | `display: none` |
| `css_visibility_hidden` | `<div>` | `visibility: hidden; height: 0; overflow: hidden` |
| `css_opacity_zero` | `<div>` | `opacity: 0; position: absolute; height: 0` |
| `white_on_white_text` | `<div>` | `color: #fff; background: #fff; font-size: 1px` |
| `offscreen_positioning` | `<div>` | `position: absolute; left: -9999px; top: -9999px` |
| `zero_font_size` | `<span>` | `font-size: 0; line-height: 0; width: 0; height: 0` |
| `aria_hidden` | `<div>` | `aria-hidden="true"; position: absolute; height: 0` |
| `form_hidden_field` | `<form>` + `<input type="hidden">` | `display: none` on form |
| `data_attribute` | `<div>` | `data-canary-instruction` attribute, `display: none` |
| `svg_text` | `<svg>` + `<text>` | `width: 0; height: 0; position: absolute` |
| `noscript_block` | `<noscript>` | Content not rendered in JS-enabled browsers |

**Meta/Structured Data Injector** (`inject/meta.ts`):

| Method | HTML Element | Technique |
|--------|-------------|-----------|
| `meta_tag` | `<meta>` | `name` and `content` attributes in `<head>` |
| `json_ld` | `<script type="application/ld+json">` | JSON-LD structured data in `<head>` |
| `microdata` | `<div itemscope>` + `<meta itemprop>` | Schema.org microdata, `display: none` |

**Style Injector** (`inject/style.ts`):

| Method | HTML Element | Technique |
|--------|-------------|-----------|
| `css_pseudo_element` | `<style>` + `<div>` | CSS `::after` pseudo-element with `content` property |
| `image_alt_text` | `<img>` | 1x1 transparent pixel with payload in `alt` attribute |

### Placement Strategies

Each payload specifies where it should be placed in the DOM:

| Placement | Location |
|-----------|----------|
| `head` | Appended to `<head>` (forced for `meta_tag` and `json_ld`) |
| `body_top` | Prepended as first child of `<body>` |
| `body_bottom` | Appended as last child of `<body>` |
| `inline` | Inserted in the middle of `<main>` or `<body>` children |

### XSS Prevention

All injection methods use safe DOM APIs exclusively:

- `element.textContent = content` for text payloads
- `element.setAttribute(name, value)` for attribute payloads
- `JSON.stringify()` for JSON-LD payloads

The codebase never uses `innerHTML`, `outerHTML`, `insertAdjacentHTML`, or `document.write`. This is a deliberate security constraint to prevent the test framework from introducing XSS vulnerabilities into the pages it monitors.

---

## Observation Engine

After injection, the observation engine monitors for signs that an AI agent has read and acted on the injected content.

### MutationObserver

A `MutationObserver` watches the entire document for:

- **Added nodes**: New elements whose `textContent` or attributes contain canary markers
- **Character data changes**: Text node modifications that reference canary markers
- **Attribute changes**: Modifications to `src`, `href`, `content`, `value`, or `data-*` attributes that contain markers

The observer uses a pre-compiled regex from all canary marker strings for efficient matching, with a fallback to `Set`-based exact lookup for confirmation.

### Network Monitoring

The observation engine patches `fetch` and `XMLHttpRequest` to detect outbound requests containing canary markers in URLs or request bodies. This catches data exfiltration attempts where an agent renders a markdown image or makes an API call to an attacker-controlled endpoint.

### Timing Analysis

Response timing is recorded for each test:
- `injected_at`: Timestamp when the payload was placed in the DOM
- `observed_at`: Timestamp when the first matching mutation was detected

The delta between these timestamps indicates how quickly the agent processed the hidden content.

---

## Reporting

Results are sent to the API using a tiered transport strategy:

1. **`sendBeacon`** (primary): Uses `navigator.sendBeacon()` which is guaranteed to complete even during page unload. Best for reliability.

2. **`fetch`** (fallback): Used if `sendBeacon` is unavailable or fails. Sends a POST request with `keepalive: true`.

3. **Tracking pixel** (last resort): Encodes a minimal payload into query parameters of an image request. Limited by URL length but works in the most restrictive environments.

### Payload Format

```json
{
  "v": 1,
  "site_key": "cy_live_xxxxxxxxxxxxxxxxxxxx",
  "visit_id": "uuid-v4",
  "timestamp": "2026-02-21T12:00:00Z",
  "page_url": "https://example.com/page",
  "detection": {
    "confidence": 0.92,
    "classification": "confirmed_agent",
    "agent_family": "OpenAI ChatGPT",
    "signals": { ... }
  },
  "test_results": [
    {
      "test_id": "CAN-0001",
      "test_version": "1.0",
      "delivery_method": "css_display_none",
      "outcome": "full_compliance",
      "evidence": {
        "canary_token_observed": true,
        "response_time_ms": 340,
        "dom_mutations": ["div#response added containing CANARY-OVERRIDE-0001"]
      }
    }
  ]
}
```

---

## API Architecture

The API is built with FastAPI and follows a layered architecture:

```
Routes (FastAPI routers)
  |
  v
Schemas (Pydantic models for request/response validation)
  |
  v
Services (business logic: detection, scoring, alerting)
  |
  v
Models (SQLAlchemy ORM)
  |
  v
Database (async engine via SQLAlchemy + aiosqlite/asyncpg)
```

### Key Design Decisions

- **Async throughout**: The entire stack uses `async`/`await` from route handlers through database queries. This allows efficient handling of concurrent ingest requests without thread pools.

- **Pydantic everywhere**: All request bodies, response bodies, and configuration objects use Pydantic models for automatic validation and serialization.

- **Dependency injection**: Database sessions and settings are provided via FastAPI's dependency injection system (`Depends(get_session)`, `Depends(get_settings)`).

- **Server-side detection enrichment**: The ingest endpoint combines client-side detection signals with server-side analysis (User-Agent verification, header inspection, IP hashing) to produce a final classification.

### Middleware

- **CORS**: Configurable via `CORS_ORIGINS` environment variable
- **Rate limiting**: Optional, requires Redis (`REDIS_URL`)

---

## Database

### Schema Overview

```
sites
  |-- id (PK, UUID)
  |-- site_key (unique, indexed)
  |-- domain
  |-- config (JSON)
  |-- is_active
  |-- created_at, updated_at
  |
  +-- api_keys (1:N)
  |     |-- id (PK, UUID)
  |     |-- key_hash (SHA-256 of the raw key)
  |     |-- prefix (first 8 chars for identification)
  |     |-- environment (live/test)
  |     |-- is_active
  |
  +-- visits (1:N)
  |     |-- id (PK, UUID)
  |     |-- visit_id (unique, from client)
  |     |-- page_url
  |     |-- timestamp
  |     |-- user_agent
  |     |-- detection (JSON)
  |     |-- classification
  |     |-- agent_family
  |     |-- ip_hash
  |     |
  |     +-- test_results (1:N)
  |           |-- id (PK, UUID)
  |           |-- test_id (e.g. CAN-0001)
  |           |-- test_version
  |           |-- delivery_method
  |           |-- outcome
  |           |-- score (0-100)
  |           |-- evidence (JSON)
  |           |-- injected_at, observed_at
  |
  +-- webhooks (1:N)
        |-- id (PK, UUID)
        |-- url
        |-- events (JSON array)
        |-- secret (for HMAC signing)
        |-- enabled
        |
        +-- webhook_deliveries (1:N)
              |-- event_type
              |-- payload (JSON)
              |-- status_code
              |-- attempt
              |-- next_retry_at
```

### SQLite vs PostgreSQL

Canary uses a custom `JSONType` column type that automatically handles JSON serialization:
- **PostgreSQL**: Uses native `JSONB` for efficient JSON queries
- **SQLite**: Stores JSON as `TEXT` with `json.dumps()`/`json.loads()` serialization

The database driver is selected based on the `DATABASE_URL` connection string:
- `sqlite+aiosqlite:///./canary.db` for SQLite (self-hosted default)
- `postgresql+asyncpg://user:pass@host:5432/canary` for PostgreSQL

---

## Security Model

### Authentication

Canary uses two types of credentials:

| Type | Format | Use | Exposure |
|------|--------|-----|----------|
| Site key | `cy_live_` + 20 chars | Embedded in the script tag, sent with ingest payloads | Public (client-side) |
| API key | `cy_sk_` + 40 chars | Bearer token for management endpoints | Secret (server-side only) |

API keys are hashed with SHA-256 before storage. Only the prefix (first 8 characters) is stored in plaintext for identification purposes.

### Webhook Signing

All webhook payloads are signed with HMAC-SHA256 using the webhook's secret. The signature is sent in the `X-Canary-Signature` header. Recipients should verify this signature before processing the payload.

### CORS

CORS is configured via the `CORS_ORIGINS` environment variable. In development, `*` is acceptable. In production, restrict to the domains you are monitoring.

### Nonce System

Visit IDs serve as nonces to prevent replay attacks on the ingest endpoint. Each `visit_id` must be unique; duplicate submissions are rejected.

### No innerHTML

As noted in the injection engine section, the codebase never uses `innerHTML` or any other DOM API that parses HTML strings. This eliminates the risk of the framework itself becoming an XSS vector.

### IP Privacy

IP addresses are hashed with SHA-256 before storage. The raw IP is never persisted. This one-way hash allows for aggregate analysis (unique visitor counting) without storing personally identifiable information.

---

## Self-Hosted vs Hosted Architecture

| Component | Self-Hosted | Hosted |
|-----------|-------------|--------|
| Script delivery | Static file from your server | CDN-delivered with edge config injection |
| API | Single FastAPI instance | Multi-region FastAPI behind load balancer |
| Database | SQLite (single file) or PostgreSQL | Managed PostgreSQL with read replicas |
| Nonce store | In-database uniqueness constraint | Redis for fast nonce lookup |
| Rate limiting | None (or optional Redis) | Redis-backed per-key rate limiting |
| Agent feed | Not available | Cross-site agent intelligence aggregation |
| Webhooks | Direct dispatch from API | Queue-based dispatch with guaranteed delivery |

The self-hosted deployment is designed to be operationally simple: a single Docker container with an SQLite database is sufficient for most use cases. PostgreSQL is recommended if you expect high traffic or need concurrent write performance.
