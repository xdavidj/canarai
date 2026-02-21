#!/usr/bin/env python3
"""
simulate-agent.py — Simulate an AI agent visiting a page with Canary tests.

Uses Playwright to launch a headless Chromium browser with an AI agent
user-agent string, navigates to a target URL, and observes what the
Canary script injects and detects.

Prerequisites:
    pip install playwright
    playwright install chromium

Usage:
    python scripts/simulate-agent.py
    python scripts/simulate-agent.py --url http://localhost:8787/demo
    python scripts/simulate-agent.py --url http://localhost:8787/demo --api-url http://localhost:8787
    python scripts/simulate-agent.py --timeout 60 --headed
"""

import argparse
import json
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("\033[91mError: Playwright is required.\033[0m")
    print("Install it with:")
    print("  pip install playwright")
    print("  playwright install chromium")
    sys.exit(1)


# ANSI color codes
class C:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


AI_AGENT_USER_AGENTS = {
    "claude": (
        "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko) "
        "Claude-Agent/1.0 (Anthropic; +https://anthropic.com)"
    ),
    "gpt": (
        "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko) "
        "ChatGPT-User/1.0 (OpenAI; +https://openai.com/bot)"
    ),
    "perplexity": (
        "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko) "
        "PerplexityBot/1.0 (+https://perplexity.ai/bot)"
    ),
    "generic": (
        "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko) "
        "Claude-Agent/1.0"
    ),
}


def check_api_results(api_url: str, visit_id: str | None = None) -> dict | None:
    """Check the API for detection results."""
    url = f"{api_url.rstrip('/')}/v1/results/latest"
    if visit_id:
        url += f"?visit_id={visit_id}"

    req = Request(url, headers={"Accept": "application/json"}, method="GET")

    try:
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (HTTPError, URLError):
        return None


def run_simulation(args: argparse.Namespace) -> None:
    """Run the AI agent simulation."""
    ua_string = AI_AGENT_USER_AGENTS.get(args.agent, AI_AGENT_USER_AGENTS["generic"])

    print(f"\n{C.BOLD}Canary Agent Simulator{C.RESET}")
    print(f"{C.DIM}{'=' * 60}{C.RESET}\n")
    print(f"  {C.BOLD}Target URL:{C.RESET}    {C.CYAN}{args.url}{C.RESET}")
    print(f"  {C.BOLD}Agent type:{C.RESET}    {args.agent}")
    print(f"  {C.BOLD}User-Agent:{C.RESET}    {C.DIM}{ua_string[:60]}...{C.RESET}")
    print(f"  {C.BOLD}Timeout:{C.RESET}       {args.timeout}s")
    print(f"  {C.BOLD}Headed mode:{C.RESET}   {'yes' if args.headed else 'no'}")
    if args.api_url:
        print(f"  {C.BOLD}API URL:{C.RESET}       {args.api_url}")
    print()

    with sync_playwright() as p:
        print(f"  {C.DIM}Launching Chromium...{C.RESET}")
        browser = p.chromium.launch(headless=not args.headed)
        context = browser.new_context(
            user_agent=ua_string,
            viewport={"width": 1280, "height": 720},
        )

        # Collect console messages
        console_messages: list[dict] = []
        page = context.new_page()

        def on_console(msg):
            console_messages.append({
                "type": msg.type,
                "text": msg.text,
                "timestamp": time.time(),
            })

        page.on("console", on_console)

        # Collect network requests
        network_requests: list[dict] = []

        def on_request(request):
            network_requests.append({
                "url": request.url,
                "method": request.method,
                "timestamp": time.time(),
            })

        page.on("request", on_request)

        # Navigate to target
        print(f"  {C.DIM}Navigating to {args.url}...{C.RESET}")
        try:
            page.goto(args.url, wait_until="networkidle", timeout=30000)
        except Exception as e:
            print(f"  {C.RED}Navigation failed: {e}{C.RESET}")
            browser.close()
            sys.exit(1)

        print(f"  {C.GREEN}Page loaded{C.RESET}")
        print(f"  {C.DIM}Title: {page.title()}{C.RESET}")

        # Wait for Canary script to execute
        print(f"\n  {C.BOLD}Waiting for Canary script...{C.RESET}")
        canary_state = None
        start_time = time.time()

        while time.time() - start_time < args.timeout:
            try:
                canary_state = page.evaluate("() => window.__CANARY_STATE__")
            except Exception:
                canary_state = None

            if canary_state:
                break

            time.sleep(0.5)
            elapsed = int(time.time() - start_time)
            sys.stdout.write(f"\r  {C.DIM}  Elapsed: {elapsed}s / {args.timeout}s{C.RESET}")
            sys.stdout.flush()

        print()

        # Report Canary state
        if canary_state:
            print(f"\n  {C.GREEN}{C.BOLD}Canary script detected!{C.RESET}")
            print(f"  {C.DIM}{'─' * 40}{C.RESET}")

            if isinstance(canary_state, dict):
                detection = canary_state.get("detection", {})
                tests = canary_state.get("tests", {})
                results = canary_state.get("results", {})

                print(f"  {C.BOLD}Detection:{C.RESET}")
                if isinstance(detection, dict):
                    score = detection.get("score", "N/A")
                    verdict = detection.get("verdict", "N/A")
                    score_color = C.RED if isinstance(score, (int, float)) and score >= 0.7 else C.GREEN
                    print(f"    Score:    {score_color}{score}{C.RESET}")
                    print(f"    Verdict:  {verdict}")
                else:
                    print(f"    {C.DIM}{detection}{C.RESET}")

                print(f"\n  {C.BOLD}Tests:{C.RESET}")
                if isinstance(tests, dict):
                    injected = tests.get("injected", 0)
                    observed = tests.get("observed", 0)
                    print(f"    Injected: {injected}")
                    print(f"    Observed: {observed}")
                elif isinstance(tests, list):
                    print(f"    Count: {len(tests)}")
                    for t in tests:
                        if isinstance(t, dict):
                            tid = t.get("id", "unknown")
                            status = t.get("status", "unknown")
                            status_color = C.RED if status == "triggered" else C.GREEN
                            print(f"    {tid}: {status_color}{status}{C.RESET}")
                else:
                    print(f"    {C.DIM}{tests}{C.RESET}")

                print(f"\n  {C.BOLD}Results:{C.RESET}")
                if isinstance(results, dict):
                    for key, val in results.items():
                        print(f"    {key}: {val}")
                elif isinstance(results, list):
                    print(f"    Count: {len(results)}")
                else:
                    print(f"    {C.DIM}{results}{C.RESET}")
            else:
                print(f"  {C.DIM}{json.dumps(canary_state, indent=2)}{C.RESET}")
        else:
            print(f"\n  {C.YELLOW}No Canary state found (window.__CANARY_STATE__ not set){C.RESET}")
            print(f"  {C.DIM}The Canary script may not be embedded on this page,")
            print(f"  or debug mode may not be enabled.{C.RESET}")

        # Check for injected DOM elements
        print(f"\n  {C.BOLD}DOM inspection:{C.RESET}")
        hidden_elements = page.evaluate("""
            () => {
                const hidden = document.querySelectorAll(
                    '[style*="display:none"], [style*="display: none"], ' +
                    '[style*="visibility:hidden"], [style*="visibility: hidden"], ' +
                    '[style*="opacity:0"], [style*="opacity: 0"], ' +
                    '[aria-hidden="true"]'
                );
                return Array.from(hidden).map(el => ({
                    tag: el.tagName.toLowerCase(),
                    text: el.textContent?.substring(0, 100) || '',
                    style: el.getAttribute('style') || '',
                }));
            }
        """)

        if hidden_elements:
            print(f"    Found {C.CYAN}{len(hidden_elements)}{C.RESET} hidden elements:")
            for i, el in enumerate(hidden_elements[:10]):
                text_preview = el.get("text", "").strip().replace("\n", " ")[:80]
                print(f"    {C.DIM}[{i}] <{el['tag']}> {text_preview}{C.RESET}")
        else:
            print(f"    {C.DIM}No hidden elements found{C.RESET}")

        # Console log analysis
        canary_logs = [m for m in console_messages if "canary" in m.get("text", "").lower()]
        if canary_logs:
            print(f"\n  {C.BOLD}Canary console messages:{C.RESET}")
            for msg in canary_logs:
                color = C.YELLOW if msg["type"] == "warning" else C.DIM
                print(f"    {color}[{msg['type']}] {msg['text'][:100]}{C.RESET}")

        # Network requests to Canary endpoint
        canary_requests = [r for r in network_requests if "canary" in r.get("url", "").lower()]
        if canary_requests:
            print(f"\n  {C.BOLD}Canary network requests:{C.RESET}")
            for req_info in canary_requests:
                print(f"    {C.DIM}{req_info['method']} {req_info['url'][:80]}{C.RESET}")

        # Wait for remaining observations
        if canary_state and args.timeout > 10:
            remaining = max(0, args.timeout - int(time.time() - start_time))
            if remaining > 0:
                print(f"\n  {C.DIM}Waiting {remaining}s for additional observations...{C.RESET}")
                for _ in range(remaining):
                    time.sleep(1)
                    new_state = page.evaluate("() => window.__CANARY_STATE__")
                    if new_state != canary_state:
                        print(f"  {C.YELLOW}State updated during observation period{C.RESET}")
                        canary_state = new_state

        # Check API results
        if args.api_url:
            print(f"\n  {C.BOLD}Checking API for results...{C.RESET}")
            visit_id = None
            if isinstance(canary_state, dict):
                visit_id = canary_state.get("visit_id")

            results = check_api_results(args.api_url, visit_id)
            if results:
                print(f"  {C.GREEN}API results received:{C.RESET}")
                print(f"  {C.DIM}{json.dumps(results, indent=2)[:500]}{C.RESET}")
            else:
                print(f"  {C.YELLOW}No results from API (may not have been reported yet){C.RESET}")

        # Screenshot
        if args.screenshot:
            screenshot_path = args.screenshot
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"\n  {C.GREEN}Screenshot saved:{C.RESET} {screenshot_path}")

        browser.close()

    print(f"\n{C.DIM}{'=' * 60}{C.RESET}")
    print(f"  {C.GREEN}Simulation complete{C.RESET}")
    print(f"{C.DIM}{'=' * 60}{C.RESET}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulate an AI agent visiting a page with Canary tests"
    )
    parser.add_argument(
        "--url",
        type=str,
        default="http://localhost:8787/demo",
        help="Target URL to visit (default: http://localhost:8787/demo)",
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default=None,
        help="API base URL to check for results (e.g., http://localhost:8787)",
    )
    parser.add_argument(
        "--agent",
        type=str,
        choices=list(AI_AGENT_USER_AGENTS.keys()),
        default="claude",
        help="AI agent type to simulate (default: claude)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Observation timeout in seconds (default: 30)",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser in headed (visible) mode",
    )
    parser.add_argument(
        "--screenshot",
        type=str,
        default=None,
        help="Path to save a screenshot of the final page state",
    )
    args = parser.parse_args()

    run_simulation(args)


if __name__ == "__main__":
    main()
