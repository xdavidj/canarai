#!/usr/bin/env python3
"""
seed-tests.py — Load and validate Canary test modules from YAML files.

Reads all YAML test files from packages/canary-tests/tests/,
validates each against the JSON Schema, prints a summary,
and optionally POSTs them to the API.

Usage:
    python scripts/seed-tests.py
    python scripts/seed-tests.py --api-url http://localhost:8787
"""

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    import yaml
except ImportError:
    print("\033[91mError: PyYAML is required. Install it with: pip install pyyaml\033[0m")
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


def colored(text: str, color: str) -> str:
    return f"{color}{text}{C.RESET}"


# ── Minimal JSON Schema validator (no external deps) ──────────────────


def validate_against_schema(data: dict, schema: dict) -> list[str]:
    """Validate a dict against a JSON Schema. Returns a list of error messages."""
    errors: list[str] = []

    # Check required fields
    for field in schema.get("required", []):
        if field not in data:
            errors.append(f"Missing required field: '{field}'")

    properties = schema.get("properties", {})

    for key, value in data.items():
        if key not in properties:
            continue

        prop_schema = properties[key]
        errors.extend(_validate_value(key, value, prop_schema))

    return errors


def _validate_value(path: str, value, schema: dict) -> list[str]:
    """Recursively validate a value against its schema definition."""
    errors: list[str] = []
    expected_type = schema.get("type")

    # Type checking
    type_map = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    if expected_type and expected_type in type_map:
        expected = type_map[expected_type]
        if not isinstance(value, expected):
            errors.append(f"'{path}': expected type '{expected_type}', got '{type(value).__name__}'")
            return errors

    # Pattern check for strings
    if expected_type == "string" and "pattern" in schema:
        if not re.match(schema["pattern"], value):
            errors.append(f"'{path}': value '{value}' does not match pattern '{schema['pattern']}'")

    # Enum check
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"'{path}': value '{value}' not in allowed values {schema['enum']}")

    # Array item validation
    if expected_type == "array" and "items" in schema:
        min_items = schema.get("minItems", 0)
        if len(value) < min_items:
            errors.append(f"'{path}': array has {len(value)} items, minimum is {min_items}")
        for i, item in enumerate(value):
            errors.extend(_validate_value(f"{path}[{i}]", item, schema["items"]))

    # Nested object validation
    if expected_type == "object":
        for field in schema.get("required", []):
            if field not in value:
                errors.append(f"'{path}': missing required field '{field}'")
        for sub_key, sub_value in value.items():
            sub_schema = schema.get("properties", {}).get(sub_key)
            if sub_schema:
                errors.extend(_validate_value(f"{path}.{sub_key}", sub_value, sub_schema))

    return errors


# ── Main logic ────────────────────────────────────────────────────────


def find_project_root() -> Path:
    """Find the project root by looking for the packages directory."""
    script_dir = Path(__file__).resolve().parent
    # scripts/ is one level below root
    root = script_dir.parent
    if (root / "packages" / "canary-tests").exists():
        return root
    # Fallback: try cwd
    cwd = Path.cwd()
    if (cwd / "packages" / "canary-tests").exists():
        return cwd
    print(colored("Error: Cannot find project root (packages/canary-tests not found)", C.RED))
    sys.exit(1)


def load_schema(root: Path) -> dict:
    """Load the JSON Schema for test modules."""
    schema_path = root / "packages" / "canary-tests" / "schema" / "test-module.schema.json"
    if not schema_path.exists():
        print(colored(f"Error: Schema not found at {schema_path}", C.RED))
        sys.exit(1)

    with open(schema_path) as f:
        return json.load(f)


def find_test_files(root: Path) -> list[Path]:
    """Find all YAML test files recursively."""
    tests_dir = root / "packages" / "canary-tests" / "tests"
    if not tests_dir.exists():
        print(colored(f"Error: Tests directory not found at {tests_dir}", C.RED))
        sys.exit(1)

    files = sorted(tests_dir.rglob("*.yml"))
    files.extend(sorted(tests_dir.rglob("*.yaml")))
    return files


def load_and_validate_test(path: Path, schema: dict) -> tuple[dict | None, list[str]]:
    """Load a YAML test file and validate it against the schema."""
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return None, [f"YAML parse error: {e}"]

    if not isinstance(data, dict):
        return None, ["File does not contain a YAML mapping"]

    errors = validate_against_schema(data, schema)
    return data, errors


def post_test_to_api(test_data: dict, api_url: str) -> tuple[bool, str]:
    """POST a test module to the API."""
    url = f"{api_url.rstrip('/')}/v1/tests"
    payload = json.dumps(test_data).encode("utf-8")

    req = Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(req, timeout=10) as resp:
            return True, f"HTTP {resp.status}"
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:200]
        return False, f"HTTP {e.code}: {body}"
    except URLError as e:
        return False, f"Connection error: {e.reason}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load and validate Canary test modules from YAML files"
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default=None,
        help="API base URL to POST tests to (e.g., http://localhost:8787)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed validation output",
    )
    args = parser.parse_args()

    root = find_project_root()
    schema = load_schema(root)
    test_files = find_test_files(root)

    if not test_files:
        print(colored("No test files found.", C.YELLOW))
        sys.exit(1)

    print(colored(f"\n{'=' * 60}", C.DIM))
    print(colored("  Canary Test Module Loader", C.BOLD))
    print(colored(f"{'=' * 60}\n", C.DIM))
    print(f"  Project root:  {colored(str(root), C.CYAN)}")
    print(f"  Test files:    {colored(str(len(test_files)), C.CYAN)}")
    if args.api_url:
        print(f"  API endpoint:  {colored(args.api_url, C.CYAN)}")
    print()

    valid_count = 0
    invalid_count = 0
    api_success = 0
    api_fail = 0

    category_counts: dict[str, int] = {}
    severity_counts: dict[str, int] = {}

    for path in test_files:
        relative = path.relative_to(root)
        test_data, errors = load_and_validate_test(path, schema)

        if errors:
            invalid_count += 1
            status = colored("FAIL", C.RED)
            test_id = test_data.get("id", "???") if test_data else "???"
            print(f"  {status}  {colored(test_id, C.BOLD)}  {colored(str(relative), C.DIM)}")
            for err in errors:
                print(f"         {colored(err, C.RED)}")
        else:
            valid_count += 1
            test_id = test_data["id"]
            name = test_data["metadata"]["name"]
            category = test_data["metadata"]["category"]
            severity = test_data["metadata"]["severity"]
            status = colored("OK", C.GREEN)

            category_counts[category] = category_counts.get(category, 0) + 1
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

            severity_color = {
                "common": C.GREEN,
                "uncommon": C.YELLOW,
                "emerging": C.MAGENTA,
            }.get(severity, C.DIM)

            print(
                f"  {status}    {colored(test_id, C.BOLD)}  "
                f"{name:<40} {colored(severity, severity_color)}"
            )

            if args.verbose:
                markers = test_data.get("canary_markers", [])
                payloads = test_data.get("payloads", [])
                print(f"         Category: {category}")
                print(f"         Payloads: {len(payloads)}")
                print(f"         Markers:  {', '.join(markers)}")

            # POST to API if requested
            if args.api_url:
                ok, msg = post_test_to_api(test_data, args.api_url)
                if ok:
                    api_success += 1
                    print(f"         {colored('Uploaded', C.GREEN)} {colored(msg, C.DIM)}")
                else:
                    api_fail += 1
                    print(f"         {colored('Upload failed', C.RED)} {colored(msg, C.DIM)}")

    # Summary
    print(colored(f"\n{'=' * 60}", C.DIM))
    print(colored("  Summary", C.BOLD))
    print(colored(f"{'=' * 60}\n", C.DIM))

    print(f"  Total:    {len(test_files)}")
    print(f"  Valid:    {colored(str(valid_count), C.GREEN)}")
    if invalid_count > 0:
        print(f"  Invalid:  {colored(str(invalid_count), C.RED)}")

    if category_counts:
        print(f"\n  {colored('Categories:', C.BOLD)}")
        for cat, count in sorted(category_counts.items()):
            print(f"    {cat:<35} {count}")

    if severity_counts:
        print(f"\n  {colored('Severity:', C.BOLD)}")
        for sev, count in sorted(severity_counts.items()):
            print(f"    {sev:<35} {count}")

    if args.api_url:
        print(f"\n  {colored('API Upload:', C.BOLD)}")
        print(f"    Succeeded:  {colored(str(api_success), C.GREEN)}")
        if api_fail > 0:
            print(f"    Failed:     {colored(str(api_fail), C.RED)}")

    print()

    if invalid_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
