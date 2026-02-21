# Quickstart Guide

This guide walks you through setting up Canary, embedding the detection script on a page, and viewing your first test results.

---

## Prerequisites

**For Docker deployment (recommended):**

- Docker 24+ and Docker Compose v2

**For local development:**

- Python 3.11+
- Node.js 20+
- [pnpm](https://pnpm.io/) 9+
- [uv](https://docs.astral.sh/uv/) (Python package manager)

---

## 1. Self-Hosted Setup (Docker)

### Clone the repository

```bash
git clone https://github.com/canary-security/canary.git
cd canary
```

### Start the services

```bash
docker compose -f docker/docker-compose.selfhosted.yml up -d
```

This starts the Canary API on port `8787` with an SQLite database. Data is persisted in `docker/data/`.

Verify the server is running:

```bash
curl http://localhost:8787/health
# {"status":"ok"}
```

### Generate an API key

```bash
python scripts/generate-api-key.py --api-url http://localhost:8787 --domain yoursite.com
```

This outputs:
- A **site key** (`cy_live_...`) -- safe to embed in client-side code
- An **API key** (`cy_sk_...`) -- keep this secret, use it for management API calls
- An embed snippet you can copy into your HTML

### Create a site via the API

If the key generation script did not automatically register with the API, create a site manually:

```bash
curl -X POST http://localhost:8787/v1/sites \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "yoursite.com",
    "config": {
      "enabled_tests": ["CAN-0001", "CAN-0002", "CAN-0003", "CAN-0004"],
      "detection_threshold": 0.50
    }
  }'
```

The response includes the `site_key` and `api_key`. Save both.

### Embed the script on your site

Add this script tag to any page you want to monitor:

```html
<script
  src="http://localhost:8787/static/canary.js"
  data-canary-site-key="cy_live_xxxxxxxxxxxxxxxxxxxx"
  data-canary-endpoint="http://localhost:8787"
></script>
```

Replace the site key with the one returned from the previous step.

**Script tag attributes:**

| Attribute | Required | Description |
|-----------|----------|-------------|
| `data-canary-site-key` | Yes | Your site key |
| `data-canary-endpoint` | Yes | API base URL |
| `data-canary-tests` | No | Comma-separated test IDs to enable (overrides site config) |
| `data-canary-threshold` | No | Detection threshold, 0.0-1.0 (overrides site config) |
| `data-canary-reporting` | No | Reporting mode: `beacon`, `fetch`, or `pixel` |
| `data-canary-debug` | No | Set to `true` for console logging |

### Visit your site

Open the page in a browser. Since you are a human user, Canary should detect you as `human` and not inject tests. To test the full pipeline, use the agent simulator (see Step 4 below).

### Query results

```bash
# List all visits
curl -H "Authorization: Bearer cy_sk_..." http://localhost:8787/v1/results

# Get aggregate summary
curl -H "Authorization: Bearer cy_sk_..." http://localhost:8787/v1/results/summary
```

---

## 2. Development Setup

### Clone and install dependencies

```bash
git clone https://github.com/canary-security/canary.git
cd canary

# Install JavaScript dependencies (for the script package)
pnpm install

# Install Python dependencies (for the API)
cd packages/canary-api
uv sync
cd ../..
```

### Run the API

```bash
cd packages/canary-api
uv run uvicorn canary_api.main:app --reload --port 8787
```

The API starts on `http://localhost:8787` with SQLite and auto-reload enabled.

### Build the script

```bash
pnpm build:script
```

The bundled IIFE script is output to `packages/canary-script/dist/canary.js`.

For development with file watching:

```bash
pnpm dev:script
```

### Open the demo page

Open `demo/index.html` in your browser. The demo page has the Canary script embedded and pointed at `http://localhost:8787`.

### Validate test modules

```bash
python scripts/seed-tests.py
```

This loads all YAML test files from `packages/canary-tests/tests/`, validates them against the JSON Schema, and prints a summary.

To also upload them to a running API:

```bash
python scripts/seed-tests.py --api-url http://localhost:8787
```

---

## 3. Testing with the Agent Simulator

The agent simulator uses Playwright to visit your page as a headless browser, mimicking an AI agent.

### Install Playwright

```bash
pip install playwright
playwright install chromium
```

### Run the simulator

```bash
python scripts/simulate-agent.py --url http://localhost:3000 --agent "GPTBot"
```

The simulator:
1. Launches a headless Chromium instance with the specified agent User-Agent string
2. Navigates to the target URL
3. Waits for the Canary script to execute and report results
4. Prints a summary of what was detected and injected

### Check results

After the simulator runs, query the API to see what was captured:

```bash
curl -H "Authorization: Bearer cy_sk_..." http://localhost:8787/v1/results?classification=confirmed_agent
```

You should see the simulated visit with its detection signals and test outcomes.

---

## 4. Running Tests

### API tests (Python)

```bash
cd packages/canary-api
uv run pytest
```

### Script tests (TypeScript)

```bash
pnpm test:script
```

### Validate all YAML test modules

```bash
python scripts/seed-tests.py --verbose
```

---

## Next Steps

- Read the [Architecture Documentation](architecture.md) to understand how the detection pipeline, injection engine, and observation system work together
- Browse the [Test Library](../README.md#test-library) and learn how to [author new tests](test-authoring.md)
- Set up [webhooks](api-reference.md#post-v1webhooks) to get alerts when agents are detected
- Explore the full [API Reference](api-reference.md) for all available endpoints
- Deploy to production with the [Self-Hosted Guide](self-hosted-guide.md)
