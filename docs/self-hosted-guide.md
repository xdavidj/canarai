# Self-Hosted Deployment Guide

This guide covers deploying Canary on your own infrastructure. Canary is designed to be lightweight and operationally simple -- a single Docker container with SQLite is sufficient for most use cases.

---

## System Requirements

**Minimum:**

- Docker 24+ and Docker Compose v2
- 512 MB RAM
- 1 GB disk space

**For bare-metal (no Docker):**

- Python 3.11+
- 512 MB RAM
- 1 GB disk space

**Recommended for production:**

- 1 GB+ RAM
- PostgreSQL 16+ (instead of SQLite)
- Reverse proxy (nginx or Caddy) for HTTPS

---

## 1. Docker Deployment

### Quick Start

```bash
git clone https://github.com/canary-security/canary.git
cd canary

# Set a secure API secret key
export API_SECRET_KEY=$(openssl rand -hex 32)

# Start the server
docker compose -f docker/docker-compose.selfhosted.yml up -d
```

This starts the Canary API on port `8787` with SQLite storage. Data is persisted in `docker/data/canary.db`.

### Verify

```bash
curl http://localhost:8787/health
# {"status":"ok"}
```

### Stop

```bash
docker compose -f docker/docker-compose.selfhosted.yml down
```

Data is preserved in the `docker/data/` volume. To remove all data:

```bash
docker compose -f docker/docker-compose.selfhosted.yml down -v
rm -rf docker/data/
```

---

## 2. Configuration

### canary.toml

The `docker/canary.toml` file configures site-level behavior. It is mounted read-only into the container:

```toml
[canary]
domain = "example.com"
enabled_tests = ["CAN-0001", "CAN-0002", "CAN-0003", "CAN-0004", "CAN-0008"]
detection_threshold = 0.70

[canary.webhook]
url = ""
events = ["agent_detected", "test_failed"]
secret = "change-me"
```

| Key | Type | Description |
|-----|------|-------------|
| `domain` | string | The domain this configuration applies to |
| `enabled_tests` | string[] | List of test IDs to activate (e.g., `["CAN-0001", "CAN-0004"]`) |
| `detection_threshold` | float | Minimum confidence score to trigger test injection (0.0-1.0) |
| `webhook.url` | string | Webhook endpoint URL (leave empty to disable) |
| `webhook.events` | string[] | Event types to send to the webhook |
| `webhook.secret` | string | HMAC-SHA256 signing secret for webhook payloads |

---

## 3. Environment Variables

All configuration can be set via environment variables. These take precedence over `canary.toml` for server-level settings.

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./canary.db` | Database connection string |
| `API_SECRET_KEY` | `change-me` | Secret key for internal signing and session management. **Must be changed in production.** |
| `API_HOST` | `0.0.0.0` | Host address to bind the API server to |
| `API_PORT` | `8787` | Port to bind the API server to |
| `CORS_ORIGINS` | `*` | Comma-separated list of allowed CORS origins. Restrict in production. |
| `ENVIRONMENT` | `development` | `development` or `production`. Controls SQL echo logging and debug features. |
| `WEBHOOK_TIMEOUT_SECONDS` | `10` | Timeout for outgoing webhook requests |
| `WEBHOOK_MAX_RETRIES` | `3` | Maximum retry attempts for failed webhook deliveries |
| `SCRIPT_BASE_URL` | `http://localhost:8787` | Base URL used to construct the embed script URL |
| `REDIS_URL` | (none) | Redis connection string for rate limiting and nonce storage. Optional. |

### Setting environment variables with Docker Compose

Edit the `environment` section in `docker/docker-compose.selfhosted.yml`:

```yaml
services:
  canary-api:
    environment:
      DATABASE_URL: sqlite+aiosqlite:///data/canary.db
      API_SECRET_KEY: ${API_SECRET_KEY:-your-secure-key-here}
      CORS_ORIGINS: "https://yoursite.com,https://www.yoursite.com"
      ENVIRONMENT: production
      SCRIPT_BASE_URL: https://canary.yoursite.com
```

Or use a `.env` file in the project root:

```bash
# .env
API_SECRET_KEY=a1b2c3d4e5f6...
CORS_ORIGINS=https://yoursite.com
ENVIRONMENT=production
```

---

## 4. PostgreSQL Setup

SQLite works well for low-to-moderate traffic. For higher concurrency or production deployments, switch to PostgreSQL.

### Using Docker Compose with PostgreSQL

Use the full `docker-compose.yml` which includes a PostgreSQL service:

```bash
export API_SECRET_KEY=$(openssl rand -hex 32)
docker compose -f docker/docker-compose.yml up -d
```

This starts both the Canary API and PostgreSQL 16. The database is created automatically with:
- User: `canary`
- Password: `canary`
- Database: `canary`

**Change the default credentials in production.** Edit `docker/docker-compose.yml`:

```yaml
postgres:
  environment:
    POSTGRES_USER: canary
    POSTGRES_PASSWORD: a-strong-password-here
    POSTGRES_DB: canary
```

And update the `DATABASE_URL` in the API service accordingly:

```yaml
canary-api:
  environment:
    DATABASE_URL: postgresql+asyncpg://canary:a-strong-password-here@postgres:5432/canary
```

### Using an External PostgreSQL Instance

If you already have a PostgreSQL server, set `DATABASE_URL` to point to it:

```bash
DATABASE_URL=postgresql+asyncpg://user:password@your-pg-host:5432/canary
```

Install the `asyncpg` driver (included in the Docker image). For bare-metal:

```bash
cd packages/canary-api
uv sync --extra postgres
```

### Migrating from SQLite to PostgreSQL

1. Export data from SQLite (if you have existing data you want to preserve):
   ```bash
   sqlite3 canary.db .dump > canary_dump.sql
   ```

2. Start PostgreSQL and update `DATABASE_URL`

3. The API will create tables automatically on startup. For manual migration, use Alembic:
   ```bash
   cd packages/canary-api
   uv run alembic upgrade head
   ```

4. Import data using `psql` (manual cleanup may be needed for SQLite-to-PostgreSQL syntax differences)

---

## 5. Reverse Proxy

In production, place a reverse proxy in front of the Canary API to handle HTTPS termination.

### nginx

```nginx
server {
    listen 443 ssl http2;
    server_name canary.yoursite.com;

    ssl_certificate     /etc/letsencrypt/live/canary.yoursite.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/canary.yoursite.com/privkey.pem;

    # Security headers
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    location / {
        proxy_pass http://127.0.0.1:8787;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Increase timeout for webhook dispatch
        proxy_read_timeout 30s;
    }

    # Cache static assets (the script bundle)
    location /static/ {
        proxy_pass http://127.0.0.1:8787;
        proxy_cache_valid 200 1h;
        add_header Cache-Control "public, max-age=3600";
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name canary.yoursite.com;
    return 301 https://$server_name$request_uri;
}
```

### Caddy

```
canary.yoursite.com {
    reverse_proxy localhost:8787

    header {
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
    }
}
```

Caddy automatically provisions and renews HTTPS certificates via Let's Encrypt.

### Update configuration

After setting up the reverse proxy, update these settings:

```bash
SCRIPT_BASE_URL=https://canary.yoursite.com
CORS_ORIGINS=https://yoursite.com,https://www.yoursite.com
```

And update your embed snippet:

```html
<script
  src="https://canary.yoursite.com/static/canary.js"
  data-canary-site-key="cy_live_xxxxxxxxxxxxxxxxxxxx"
  data-canary-endpoint="https://canary.yoursite.com"
></script>
```

---

## 6. Webhook Setup

Webhooks allow you to receive real-time notifications when AI agents are detected or tests fail.

### Register a webhook

```bash
curl -X POST http://localhost:8787/v1/webhooks \
  -H "Authorization: Bearer cy_sk_..." \
  -H "Content-Type: application/json" \
  -d '{
    "site_id": "your-site-uuid",
    "url": "https://hooks.slack.com/services/T.../B.../xxx",
    "events": ["visit.agent_detected", "test.critical_failure"]
  }'
```

### Available event types

| Event | Trigger |
|-------|---------|
| `visit.agent_detected` | An AI agent visit is confirmed (classification >= `likely_agent`) |
| `test.critical_failure` | A test result has outcome `exfiltration_attempted` |
| `webhook.test` | Manual test delivery (from `POST /v1/webhooks/{id}/test`) |

### Webhook payload format

```json
{
  "event": "visit.agent_detected",
  "timestamp": "2026-02-21T12:00:00Z",
  "data": {
    "visit_id": "uuid",
    "site_id": "uuid",
    "page_url": "https://example.com/page",
    "classification": "confirmed_agent",
    "agent_family": "OpenAI ChatGPT",
    "confidence": 0.95,
    "test_results_count": 4
  }
}
```

### Webhook headers

| Header | Description |
|--------|-------------|
| `X-Canary-Signature` | HMAC-SHA256 signature of the payload body |
| `X-Canary-Event` | Event type (e.g., `visit.agent_detected`) |
| `X-Canary-Delivery` | Unique delivery ID (UUID) |
| `Content-Type` | `application/json` |

### Verifying signatures

To verify a webhook signature, compute `HMAC-SHA256(payload_body, webhook_secret)` and compare it to the `X-Canary-Signature` header.

**Python example:**

```python
import hmac
import hashlib
import json

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

### Slack integration

For Slack, use an [Incoming Webhook URL](https://api.slack.com/messaging/webhooks). Canary sends JSON directly, so you may need a middleware to transform the payload into Slack's format. Alternatively, use a tool like [Hookdeck](https://hookdeck.com/) or a small serverless function.

### Discord integration

Discord webhooks accept JSON payloads with a `content` field. Similar to Slack, you may need a thin transformation layer.

### Retry behavior

Failed webhook deliveries (HTTP 4xx/5xx or timeout) are retried with exponential backoff:
- 1st retry: after 2 minutes
- 2nd retry: after 4 minutes
- 3rd retry: after 8 minutes

After the maximum retries (`WEBHOOK_MAX_RETRIES`, default 3), the delivery is marked as failed.

### Test a webhook

```bash
curl -X POST http://localhost:8787/v1/webhooks/{webhook_id}/test \
  -H "Authorization: Bearer cy_sk_..."
```

---

## 7. Upgrading

### Docker

```bash
cd canary

# Pull latest code
git pull origin main

# Rebuild and restart
docker compose -f docker/docker-compose.selfhosted.yml down
docker compose -f docker/docker-compose.selfhosted.yml build --no-cache
docker compose -f docker/docker-compose.selfhosted.yml up -d
```

Your SQLite database in `docker/data/` is preserved across rebuilds.

### Bare-metal

```bash
cd canary
git pull origin main

# Update Python dependencies
cd packages/canary-api
uv sync

# Update JavaScript dependencies
cd ../..
pnpm install

# Rebuild the script
pnpm build:script

# Restart the API
# (depends on your process manager -- systemd, supervisor, etc.)
```

### Database migrations

If a release includes schema changes, run Alembic migrations:

```bash
cd packages/canary-api
uv run alembic upgrade head
```

Check the release notes for migration instructions before upgrading.

---

## 8. Troubleshooting

### API does not start

**Symptom**: Container exits immediately or API fails to bind.

**Check**:
- Ensure port 8787 is not in use: `lsof -i :8787`
- Check container logs: `docker compose -f docker/docker-compose.selfhosted.yml logs canary-api`
- Verify `DATABASE_URL` is valid and the database file path is writable

### Script not loading

**Symptom**: The Canary script returns a 404.

**Check**:
- Verify the script is built: `ls packages/canary-script/dist/canary.js`
- Ensure `SCRIPT_BASE_URL` matches the URL in your embed snippet
- If behind a reverse proxy, verify the `/static/` location is forwarded correctly

### No results appearing

**Symptom**: You visit the page but no data appears in the API.

**Check**:
- Open browser DevTools and check the Console for Canary debug messages (add `data-canary-debug="true"` to the script tag)
- Verify the `data-canary-site-key` matches an active site in the database
- Check that CORS allows requests from your domain to the API
- If testing manually, remember that human visitors (score < 0.50) do not trigger test injection or reporting

### Database locked (SQLite)

**Symptom**: Errors mentioning "database is locked" under concurrent access.

**Fix**: SQLite handles one writer at a time. For concurrent workloads, switch to PostgreSQL. As a temporary measure, reduce concurrent connections by setting `pool_size=1` in the engine configuration.

### Webhook not receiving events

**Symptom**: Webhooks are registered but no deliveries arrive.

**Check**:
- Verify the webhook URL is reachable from the server: `curl -X POST <webhook_url>`
- Check that the webhook is `enabled: true` in the API
- Verify the registered `events` array includes the event types you expect
- Check webhook delivery history via the API for error status codes

### High memory usage

**Symptom**: The API container uses excessive memory.

**Check**:
- SQLite databases grow in memory during large queries. Consider switching to PostgreSQL.
- Ensure `ENVIRONMENT=production` is set (disables SQL echo logging)
- Check for runaway webhook retry loops with `GET /v1/webhooks` and inspect delivery records
