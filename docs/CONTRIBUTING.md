# Contributing to canar.ai

Thank you for your interest in contributing to canar.ai. This project aims to improve the security of AI agents interacting with web content, and every contribution -- whether a new test module, a bug fix, or a documentation improvement -- helps the entire ecosystem.

---

## Types of Contributions

We welcome the following types of contributions:

- **New test modules**: Document and implement new prompt injection techniques as YAML test files. This is the highest-impact contribution you can make.
- **Detection improvements**: New fingerprinting signals, behavioral heuristics, or agent identification patterns.
- **API features**: New endpoints, improved analytics, better error handling.
- **Script improvements**: Performance optimizations, new delivery methods, observation engine enhancements.
- **Documentation**: Corrections, clarifications, new guides, or translations.
- **Bug fixes**: Fixes for reported issues.
- **Test coverage**: Additional automated tests for the API or script.

---

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- [pnpm](https://pnpm.io/) 9+ (`npm install -g pnpm`)
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Git

### Clone and install

```bash
git clone https://github.com/xdavidj/canarai.git
cd canarai

# Install JavaScript dependencies
pnpm install

# Install Python dependencies
cd packages/canarai-api
uv sync --extra dev
cd ../..
```

### Verify your setup

```bash
# Build the script
pnpm build:script

# Run API tests
cd packages/canarai-api && uv run pytest

# Validate test modules
python scripts/seed-tests.py --verbose
```

---

## Project Structure

```
canarai/
  packages/
    canarai-script/        # Embeddable TypeScript script (IIFE bundle)
      src/
        detect/           # Agent detection (UA, fingerprint, behavioral)
        inject/           # Test payload injection (DOM, meta, style)
        observe/          # MutationObserver, network monitoring
        types.ts          # Shared TypeScript types
        config.ts         # Configuration resolution
    canarai-api/           # FastAPI backend
      src/canarai/
        models/           # SQLAlchemy ORM models
        schemas/          # Pydantic request/response schemas
        services/         # Business logic (detection, scoring, alerting)
        db/               # Database engine and session management
        config.py         # Environment-based settings
    canarai-tests/         # YAML test module library
      tests/
        instruction-override/
        data-exfiltration/
        ...
      schema/
        test-module.schema.json
  scripts/                # CLI utilities
  docker/                 # Docker Compose configurations
  demo/                   # Demo HTML page
  docs/                   # Documentation
```

---

## Making Changes

### Adding Test Modules

Test modules are the most impactful contribution. Each test documents a specific prompt injection technique and how to detect whether an AI agent is vulnerable to it.

1. Read the [Test Authoring Guide](test-authoring.md) thoroughly
2. Choose a unique test ID (next sequential `CAN-XXXX` number)
3. Create a YAML file in the appropriate category subdirectory
4. Validate against the JSON Schema: `python scripts/seed-tests.py --verbose`
5. Test with the agent simulator if possible

### API Development (Python)

The API uses FastAPI with async SQLAlchemy and Pydantic.

**Key conventions:**

- All route handlers are `async`
- Database sessions are injected via `Depends(get_session)`
- Request/response bodies use Pydantic models in `schemas/`
- Business logic goes in `services/`, not in route handlers
- ORM models are in `models/`
- Use type hints everywhere (the project uses `mypy --strict`)

**Adding a new endpoint:**

1. Define request/response schemas in `schemas/`
2. Add business logic in `services/` if needed
3. Create or update a router in the appropriate module
4. Add tests in the test suite

**Running the API in development:**

```bash
cd packages/canarai-api
uv run uvicorn canarai.main:app --reload --port 8787
```

**Running tests:**

```bash
cd packages/canarai-api
uv run pytest
uv run pytest -v            # verbose output
uv run pytest -x            # stop on first failure
uv run pytest tests/test_ingest.py  # specific test file
```

### Script Development (TypeScript)

The script is written in vanilla TypeScript with zero runtime dependencies. It compiles to an IIFE bundle via Rollup.

**Key conventions:**

- Strict TypeScript (`strict: true` in tsconfig)
- Zero external runtime dependencies (everything is self-contained)
- All DOM manipulation uses safe APIs (`textContent`, `setAttribute`) -- never `innerHTML`
- Feature detection before using browser APIs (wrap in `try/catch`)
- Keep the bundle size under 15KB gzipped

**Building:**

```bash
pnpm build:script           # Production build
pnpm dev:script             # Watch mode
```

**Adding a new delivery method:**

1. Add the method name to the `DeliveryMethod` union type in `types.ts`
2. Implement the method in the appropriate injector (`dom.ts`, `meta.ts`, or `style.ts`)
3. Add the method to the injector's `*_METHODS` set
4. Add the method to the JSON Schema enum in `test-module.schema.json`
5. Add the method to the `delivery_method` enum in the API schema

**Adding a new detection signal:**

1. Implement the check function in the appropriate detector (`useragent.ts`, `fingerprint.ts`, or `behavioral.ts`)
2. Add it to the detector's main function
3. Update the `DetectionSignals` type in `types.ts` if needed

---

## Testing

### Run all tests

```bash
# API tests
cd packages/canarai-api && uv run pytest

# Script tests
pnpm test:script

# Validate YAML test modules
python scripts/seed-tests.py --verbose
```

### Writing tests

**API tests** use `pytest` with `pytest-asyncio` and `httpx` for testing async endpoints:

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

**Script tests** use the project's configured test runner. Tests should cover:
- Detection accuracy (known UAs should be identified)
- Fingerprint checks (mock browser environment properties)
- Injection output (verify correct DOM elements are created)
- Observation (verify canary markers are detected in mutations)

---

## Code Style

### Python

The project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
cd packages/canarai-api

# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run mypy .
```

Ruff is configured in the root `pyproject.toml`:
- Target: Python 3.11
- Line length: 100
- Enabled rules: E, F, I, N, W, UP (pycodestyle, pyflakes, isort, pep8-naming, warnings, pyupgrade)

### TypeScript

- Strict mode enabled
- No `any` types unless absolutely necessary (and documented why)
- Use `const` by default, `let` only when reassignment is needed
- Prefer `function` declarations over arrow functions for top-level exports

---

## Pull Request Process

### Branch naming

Use descriptive branch names with a prefix:

- `feat/` -- New features or test modules (e.g., `feat/can-0021-base64-injection`)
- `fix/` -- Bug fixes (e.g., `fix/sqlite-concurrent-writes`)
- `docs/` -- Documentation changes (e.g., `docs/webhook-setup-guide`)
- `refactor/` -- Code refactoring (e.g., `refactor/detection-pipeline`)

### Before submitting

1. Run all tests and ensure they pass
2. Run linters (`ruff check`, `ruff format --check`, `mypy`)
3. If adding a test module, verify it validates against the JSON Schema
4. Write a clear commit message describing the change

### PR description

Include:
- **What**: Brief description of the change
- **Why**: Motivation or issue number
- **How**: Approach taken (for non-trivial changes)
- **Testing**: How you verified the change works

### Review process

1. A maintainer will review your PR within a few business days
2. Address any feedback by pushing additional commits (do not force-push during review)
3. Once approved, a maintainer will merge the PR

---

## Security

### Reporting vulnerabilities

If you discover a security vulnerability in canar.ai, please report it **privately**:

- Use [GitHub Security Advisories](https://github.com/xdavidj/canarai/security/advisories/new)
- Or email: security@canar.ai

**Do not create public GitHub issues for security vulnerabilities.**

We will acknowledge receipt within 48 hours and work with you to understand and address the issue before any public disclosure.

### Security guidelines for contributions

- Never use `innerHTML`, `outerHTML`, `insertAdjacentHTML`, or `document.write` in the script package
- Never log or store raw API keys (only store hashes)
- Never store raw IP addresses (use one-way hashes)
- Validate all input with Pydantic schemas
- Use parameterized queries (SQLAlchemy handles this automatically)

---

## Code of Conduct

We are committed to providing a welcoming and inclusive experience for everyone. Contributors are expected to:

- Be respectful and constructive in all communications
- Welcome newcomers and help them get started
- Focus on what is best for the project and community
- Accept constructive criticism gracefully
- Refrain from personal attacks, harassment, or discriminatory language

Unacceptable behavior can be reported to conduct@canar.ai. All reports will be reviewed and investigated promptly.

---

## Questions?

If you have questions about contributing, open a [GitHub Discussion](https://github.com/xdavidj/canarai/discussions) or reach out to the maintainers. We are happy to help you get started.
