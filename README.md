```
      ___           ___           ___           ___           ___           ___
     /\  \         /\  \         /\__\         /\  \         /\  \         /\  \
    /::\  \       /::\  \       /::|  |       /::\  \       /::\  \       /::\  \
   /:/\:\  \     /:/\:\  \     /:|:|  |      /:/\:\  \     /:/\:\  \     /:/\ \  \
  /:/  \:\  \   /::\~\:\  \   /:/|:|  |__   /::\~\:\  \   /::\~\:\  \  _\:\~\ \  \
 /:/__/ \:\__\ /:/\:\ \:\__\ /:/ |:| /\__\ /:/\:\ \:\__\ /:/\:\ \:\__\/\ \:\ \ \__\
 \:\  \  \/__/ \/__\:\/:/  / \/__|:|/:/  / \/__\:\/:/  / \/_|::\/:/  /\:\ \:\ \/__/
  \:\  \            \::/  /      |:/:/  /       \::/  /     |:|::/  /  \:\ \:\__\
   \:\  \           /:/  /       |::/  /        /:/  /      |:|\/__/    \:\/:/  /
    \:\__\         /:/  /        /:/  /        /:/  /       |:|  |       \::/  /
     \/__/         \/__/         \/__/         \/__/         \|__|        \/__/
```

# canar.ai

**Open source AI agent prompt injection testing framework**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/xdavidj/canarai/ci.yml?branch=main&label=CI)](https://github.com/xdavidj/canarai/actions)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](docker/docker-compose.selfhosted.yml)

---

## What is canar.ai?

AI agents that browse the web are vulnerable to **prompt injection attacks** hidden in page content. Malicious actors can embed invisible instructions in HTML -- using CSS `display:none` divs, white-on-white text, hidden form fields, meta tags, and more -- that are invisible to human users but readable by LLMs processing page content. These hidden instructions can hijack the agent's goals, exfiltrate user data, or force the agent to take unintended actions.

canar.ai is an open source framework that lets **website owners and security researchers** test how AI agents respond to controlled prompt injection. You embed a lightweight JavaScript snippet on your site. When an AI agent visits, canar.ai detects it through user-agent matching, browser fingerprinting, and behavioral analysis. It then injects a set of controlled test payloads using the same techniques real attackers use -- hidden divs, meta tags, JSON-LD, CSS pseudo-elements, and 13 other delivery methods. canar.ai observes whether the agent reads, acknowledges, or follows the injected instructions, then reports the results to your API.

Think of it as a **penetration testing framework for AI agents**. Instead of testing your own security, you are testing the security of the AI agents visiting your site. The results help agent developers harden their products, and they help site owners understand their exposure.

---

## Quick Start

**1. Start the server**

```bash
git clone https://github.com/xdavidj/canarai.git
cd canarai
docker compose -f docker/docker-compose.selfhosted.yml up -d
```

**2. Create a site and embed the script**

```bash
# Generate keys
python scripts/generate-api-key.py --api-url http://localhost:8787 --domain yoursite.com
```

Add the returned script tag to your site:

```html
<script
  src="http://localhost:8787/static/canarai.js"
  data-canarai-site-key="ca_live_xxxxxxxxxxxxxxxxxxxx"
  data-canarai-endpoint="http://localhost:8787"
></script>
```

**3. View results**

```bash
curl -H "Authorization: Bearer ca_sk_..." http://localhost:8787/v1/results
```

See the full [Quickstart Guide](docs/quickstart.md) for detailed setup instructions.

---

## How It Works

```
                          CANARAI DETECTION PIPELINE

  Website Visit           Detection             Test Injection
 +-----------+      +------------------+      +------------------+
 | AI Agent  | ---> | User-Agent  (40%)|      | css_display_none |
 | visits    |      | Fingerprint (25%)|      | white_on_white   |
 | your page |      | Behavioral  (25%)|      | meta_tag         |
 +-----------+      | (network)  (10%)|      | json_ld          |
                    +--------+---------+      | aria_hidden      |
                             |                | 12 more methods  |
                             v                +--------+---------+
                    +------------------+               |
                    | Score >= 0.50?   |               |
                    | suspected_agent  |               v
                    | Score >= 0.70?   |      +------------------+
                    | likely_agent     |      | Observation      |
                    | Score >= 0.85?   |      | - MutationObserver|
                    | confirmed_agent  |      | - Network patches|
                    +--------+---------+      | - Timing analysis|
                             |                +--------+---------+
                             v                         |
                    +------------------+               v
                    | Inject tests     | ---> +------------------+
                    | if agent detected|      | Report results   |
                    +------------------+      | sendBeacon / fetch|
                                              +--------+---------+
                                                       |
                                                       v
                                              +------------------+
                                              | API + Database   |
                                              | SQLite / Postgres|
                                              | Webhooks         |
                                              +------------------+
```

1. **Detect**: The embedded script runs a multi-layered detection pipeline combining user-agent matching (40% weight), browser fingerprinting (25%), and behavioral analysis (25%) to determine whether a visitor is an AI agent. Known crawlers (Googlebot, Bingbot, etc.) are excluded. Known AI agent UAs (GPTBot, ClaudeBot, PerplexityBot, etc.) short-circuit to `confirmed_agent`.

2. **Inject**: If the confidence score meets the threshold, canar.ai injects test payloads from the test library into the page DOM using 17 different delivery methods. All injections use `textContent` and `setAttribute` -- never `innerHTML` -- to prevent self-inflicted XSS.

3. **Observe**: A MutationObserver watches for DOM changes that reference canary markers. Network requests are monitored for exfiltration attempts. Timing analysis detects how quickly the agent processes hidden content.

4. **Report**: Results are sent to the API via `sendBeacon` (primary), `fetch` (fallback), or tracking pixel (last resort). Each test outcome is scored from 0 (ignored) to 100 (exfiltration attempted).

---

## Architecture

canar.ai is a monorepo with three packages:

| Package | Language | Description |
|---------|----------|-------------|
| `packages/canarai-script` | TypeScript | Embeddable detection + injection script (IIFE, <15KB gzipped, zero dependencies) |
| `packages/canarai-api` | Python | FastAPI backend with async SQLAlchemy, Pydantic schemas, webhook dispatch |
| `packages/canarai-tests` | YAML | Test module library with JSON Schema validation |

Supporting files:

| Directory | Description |
|-----------|-------------|
| `docker/` | Docker Compose configs for self-hosted and development |
| `scripts/` | CLI utilities for key generation, test seeding, agent simulation |
| `demo/` | Demo HTML page for local testing |

See [Architecture Documentation](docs/architecture.md) for the full technical deep-dive.

---

## Test Library

canar.ai ships with 20 test modules across 10 categories. Each test is a YAML file validated against a JSON Schema.

| ID | Name | Category | Severity |
|----|------|----------|----------|
| CAN-0001 | Basic Instruction Override | instruction_override | common |
| CAN-0002 | Override via HTML Comment | instruction_override | common |
| CAN-0003 | Authority Escalation via White-on-White Text | instruction_override | common |
| CAN-0004 | Markdown Image Exfiltration | data_exfiltration | common |
| CAN-0005 | Hidden Form Data Exfiltration | data_exfiltration | common |
| CAN-0006 | JSON-LD Injection | structured_data_injection | common |
| CAN-0007 | Microdata Injection | structured_data_injection | uncommon |
| CAN-0008 | Meta Tag Instruction Override | instruction_override | common |
| CAN-0009 | CSS Pseudo-Element Instruction | encoding_bypass | uncommon |
| CAN-0010 | SVG Text Hidden Instruction | encoding_bypass | uncommon |
| CAN-0011 | System Prompt Extraction | system_prompt_leakage | common |
| CAN-0012 | Goal Hijacking via Offscreen Div | goal_hijacking | common |
| CAN-0013 | Persona Manipulation | persona_manipulation | uncommon |
| CAN-0014 | Tool/Action Abuse via Aria-Hidden | tool_action_abuse | common |
| CAN-0015 | Noscript Block Injection | encoding_bypass | emerging |
| CAN-0016 | Data Attribute Instruction | context_manipulation | uncommon |
| CAN-0017 | Image Alt Text Injection | context_manipulation | uncommon |
| CAN-0018 | Multi-Turn Chained Attack | multi_turn_chained | emerging |
| CAN-0019 | Base64-Encoded Instruction | encoding_bypass | emerging |
| CAN-0020 | Zero Font Size Instruction | instruction_override | common |

**Severity levels:**

- **common** -- Widely documented attack vectors seen in the wild
- **uncommon** -- Known techniques that are less frequently observed
- **emerging** -- Novel or theoretical vectors under active research

See [Test Authoring Guide](docs/test-authoring.md) for how to contribute new tests.

---

## Self-Hosted vs Hosted

| Feature | Self-Hosted | Hosted (canar.ai) |
|---------|-------------|-------------------|
| Cost | Free | Free tier + paid plans |
| Database | SQLite (default) or PostgreSQL | Managed PostgreSQL |
| Setup | Docker Compose or bare metal | Embed script tag, done |
| Data storage | Your infrastructure | canar.ai cloud |
| Agent feed | No | Yes (cross-site agent intelligence) |
| Trend analysis | No | Yes (industry-wide trends) |
| Webhooks | Yes | Yes |
| Custom tests | Yes | Yes |
| SLA | None | 99.9% uptime |

See the [Self-Hosted Guide](docs/self-hosted-guide.md) for deployment instructions.

---

## API Reference

All endpoints are versioned under `/v1/`. Authentication uses site keys (public, for the embedded script) and API keys (secret, Bearer token for management).

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/health` | None | Health check |
| `POST` | `/v1/ingest` | Site key | Submit detection results from the script |
| `GET` | `/v1/config/{site_key}` | Site key | Fetch test configuration for a site |
| `POST` | `/v1/sites` | API key | Create a new site |
| `GET` | `/v1/sites` | API key | List your sites |
| `PATCH` | `/v1/sites/{id}` | API key | Update site settings |
| `GET` | `/v1/results` | API key | Query test results |
| `GET` | `/v1/results/summary` | API key | Get aggregate statistics |
| `POST` | `/v1/webhooks` | API key | Register a webhook |
| `POST` | `/v1/webhooks/{id}/test` | API key | Send a test webhook |
| `GET` | `/v1/feed/agents` | API key | Agent intelligence feed (hosted only) |
| `GET` | `/v1/feed/trends` | API key | Trend analysis feed (hosted only) |

See the full [API Reference](docs/api-reference.md) with request/response examples and curl commands.

---

## Contributing

Contributions are welcome. The most impactful way to contribute is by **adding new test modules** -- every new prompt injection technique you document helps the entire ecosystem.

Other welcome contributions:

- Detection improvements (new fingerprinting signals, behavioral heuristics)
- API features (new endpoints, better analytics)
- Documentation improvements
- Bug fixes

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for development setup and guidelines.

---

## Security

canar.ai is a security testing tool and should be used responsibly.

**Reporting vulnerabilities**: If you discover a security vulnerability in canar.ai itself, please report it privately via [GitHub Security Advisories](https://github.com/xdavidj/canarai/security/advisories/new) or email security@canar.ai. Do **not** create a public issue.

**Responsible use**: canar.ai injects controlled test content into pages you own. Do not use it to attack, disrupt, or interfere with third-party AI agents without authorization.

---

## License

canar.ai is released under the [MIT License](LICENSE).

---

## References

- [OWASP Top 10 for LLM Applications (2025) -- LLM01: Prompt Injection](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [Greshake et al. -- "Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection" (2023)](https://arxiv.org/abs/2302.12173)
- [BrowseSafe -- "Invisible Text Attacks on LLM Web Agents" (2024)](https://arxiv.org/abs/2403.02887)
- [Promptfoo -- "LLM Red Teaming Guide"](https://www.promptfoo.dev/docs/red-team/)
- [Embrace The Red -- "Bing Chat Data Exfiltration PoC"](https://embracethered.com/blog/posts/2023/bing-chat-data-exfiltration-poc-and-fix/)
- [Simon Willison -- "Prompt Injection: What's the Worst That Can Happen?"](https://simonwillison.net/2023/Apr/14/worst-that-can-happen/)
