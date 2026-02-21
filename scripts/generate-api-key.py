#!/usr/bin/env python3
"""
generate-api-key.py — Generate Canary site keys and API keys.

Generates cryptographically secure random keys for use with the Canary API.

Usage:
    python scripts/generate-api-key.py
    python scripts/generate-api-key.py --api-url http://localhost:8787
    python scripts/generate-api-key.py --domain example.com --api-url http://localhost:8787
"""

import argparse
import json
import secrets
import string
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


# ANSI color codes
class C:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


CHARSET = string.ascii_letters + string.digits


def generate_site_key(prefix: str = "cy_live_") -> str:
    """Generate a site key: cy_live_ + 20 random alphanumeric characters."""
    random_part = "".join(secrets.choice(CHARSET) for _ in range(20))
    return f"{prefix}{random_part}"


def generate_api_key() -> str:
    """Generate an API key: cy_sk_ + 40 random alphanumeric characters."""
    random_part = "".join(secrets.choice(CHARSET) for _ in range(40))
    return f"cy_sk_{random_part}"


def register_with_api(
    api_url: str, site_key: str, api_key: str, domain: str
) -> tuple[bool, str]:
    """Register the generated keys with the Canary API."""
    url = f"{api_url.rstrip('/')}/v1/sites"
    payload = json.dumps({
        "site_key": site_key,
        "api_key": api_key,
        "domain": domain,
    }).encode("utf-8")

    req = Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            return True, f"HTTP {resp.status} — {body[:200]}"
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:200]
        return False, f"HTTP {e.code}: {body}"
    except URLError as e:
        return False, f"Connection error: {e.reason}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Canary site keys and API keys"
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default=None,
        help="API base URL to register keys with (e.g., http://localhost:8787)",
    )
    parser.add_argument(
        "--domain",
        type=str,
        default="localhost",
        help="Domain to associate with the site key (default: localhost)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Generate test keys (cy_test_ prefix instead of cy_live_)",
    )
    args = parser.parse_args()

    prefix = "cy_test_" if args.test else "cy_live_"
    site_key = generate_site_key(prefix)
    api_key = generate_api_key()

    print(f"\n{C.BOLD}Canary Key Generator{C.RESET}")
    print(f"{C.DIM}{'=' * 60}{C.RESET}\n")

    print(f"  {C.BOLD}Site Key:{C.RESET}  {C.CYAN}{site_key}{C.RESET}")
    print(f"  {C.BOLD}API Key:{C.RESET}   {C.CYAN}{api_key}{C.RESET}")
    print(f"  {C.BOLD}Domain:{C.RESET}    {args.domain}")
    print(f"  {C.BOLD}Type:{C.RESET}      {'test' if args.test else 'production'}")

    print(f"\n{C.DIM}{'=' * 60}{C.RESET}\n")

    # Embed snippet
    print(f"  {C.BOLD}Embed snippet:{C.RESET}")
    endpoint = args.api_url or "https://your-canary-instance.com"
    print(f"  {C.DIM}<script")
    print(f'    src="{endpoint}/static/canary.js"')
    print(f'    data-site-key="{site_key}"')
    print(f'    data-endpoint="{endpoint}"')
    print(f"  ></script>{C.RESET}")

    print()

    # Environment variables
    print(f"  {C.BOLD}Environment variables:{C.RESET}")
    print(f"  {C.DIM}CANARY_SITE_KEY={site_key}")
    print(f"  CANARY_API_KEY={api_key}{C.RESET}")

    print()

    # Register with API if requested
    if args.api_url:
        print(f"  {C.BOLD}Registering with API...{C.RESET}")
        ok, msg = register_with_api(args.api_url, site_key, api_key, args.domain)
        if ok:
            print(f"  {C.GREEN}Registered successfully{C.RESET} {C.DIM}{msg}{C.RESET}")
        else:
            print(f"  {C.RED}Registration failed{C.RESET} {C.DIM}{msg}{C.RESET}")
            sys.exit(1)
        print()

    # Security reminder
    print(f"  {C.YELLOW}Keep your API key secret!{C.RESET}")
    print(f"  {C.DIM}The site key is safe to embed in client-side code.")
    print(f"  The API key should only be used server-side.{C.RESET}\n")


if __name__ == "__main__":
    main()
