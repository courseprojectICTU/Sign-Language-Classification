"""Measure five Cloud Run cold starts after an explicit cold-state preflight."""

import argparse
import json
import math
import os
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Optional, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

RUN_COUNT = 5


def validate_preflight_receipt(raw_output: str) -> Dict[str, Any]:
    """Validate proof that the next request will start a cold container."""
    try:
        receipt = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise ValueError("Preflight must print one JSON receipt") from exc

    if not isinstance(receipt, dict):
        raise ValueError("Preflight receipt must be a JSON object")

    mode = receipt.get("mode")
    revision = receipt.get("revision")
    if not isinstance(revision, str) or not revision.strip():
        raise ValueError("Preflight receipt must include a revision name")

    if mode == "scale_to_zero":
        active = receipt.get("active_instances")
        minimum = receipt.get("min_instances")
        if (
            isinstance(active, bool)
            or not isinstance(active, int)
            or active != 0
            or isinstance(minimum, bool)
            or not isinstance(minimum, int)
            or minimum != 0
        ):
            raise ValueError(
                "scale_to_zero receipt must prove active_instances=0 and min_instances=0"
            )
    elif mode == "fresh_revision":
        if receipt.get("confirmed") is not True:
            raise ValueError("fresh_revision receipt must set confirmed=true")
    else:
        raise ValueError("Preflight mode must be scale_to_zero or fresh_revision")

    return receipt


def run_preflight(command: Sequence[str], run_number: int) -> Dict[str, Any]:
    """Run the operator-provided cold-state checker and validate its JSON receipt."""
    if not command:
        raise ValueError("A cold-state preflight command is required")

    environment = os.environ.copy()
    environment["COLD_START_RUN"] = str(run_number)
    try:
        completed = subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            timeout=900,
            env=environment,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"Could not complete cold-state preflight: {exc}") from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or f"exit code {completed.returncode}"
        raise RuntimeError(f"Cold-state preflight failed on run {run_number}: {detail}")

    try:
        return validate_preflight_receipt(completed.stdout)
    except ValueError as exc:
        raise RuntimeError(f"Invalid preflight receipt on run {run_number}: {exc}") from exc


def measure_request(url: str, timeout: float) -> Dict[str, Any]:
    """Measure first response-body byte (TTFB) and full response latency."""
    started_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    start = perf_counter()
    request = Request(url, headers={"User-Agent": "vsl-cold-start-benchmark/1.0"})

    try:
        with urlopen(request, timeout=timeout) as response:
            status_code = int(response.status)
            first_byte = response.read(1)
            ttfb_ms = (perf_counter() - start) * 1000
            body = first_byte + response.read()
            total_ms = (perf_counter() - start) * 1000
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"Staging request failed: {exc}") from exc

    if not 200 <= status_code < 300:
        raise RuntimeError(f"Staging returned HTTP {status_code}, expected a 2xx response")
    if not first_byte:
        raise RuntimeError("Staging response body was empty; TTFB could not be measured")

    return {
        "started_at_utc": started_at,
        "status_code": status_code,
        "ttfb_ms": round(ttfb_ms, 3),
        "total_ms": round(total_ms, 3),
        "bytes_received": len(body),
    }


def calculate_statistics(values: Sequence[float]) -> Dict[str, float]:
    """Return median, mean, minimum, and maximum for a non-empty sample."""
    if not values:
        raise ValueError("At least one measurement is required")
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Measurements must be finite numbers")

    return {
        "median_ms": round(statistics.median(values), 3),
        "mean_ms": round(statistics.mean(values), 3),
        "min_ms": round(min(values), 3),
        "max_ms": round(max(values), 3),
    }


def run_benchmark(
    url: str,
    preflight_command: Sequence[str],
    timeout: float = 120.0,
) -> Dict[str, Any]:
    """Run exactly five measurements, proving cold state before every request."""
    parsed_url = urlsplit(url)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise ValueError("Cloud Run staging URL must be an absolute HTTPS URL")
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Request timeout must be a positive finite number")

    measurements: List[Dict[str, Any]] = []
    for run_number in range(1, RUN_COUNT + 1):
        receipt = run_preflight(preflight_command, run_number)
        measurement = measure_request(url, timeout)
        measurement["run"] = run_number
        measurement["cold_state"] = receipt
        measurements.append(measurement)

    return {
        "url": url,
        "run_count": RUN_COUNT,
        "measurements": measurements,
        "statistics": {
            "ttfb": calculate_statistics([item["ttfb_ms"] for item in measurements]),
            "total": calculate_statistics([item["total_ms"] for item in measurements]),
        },
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the command-line benchmark and write JSON only after all runs pass."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="HTTPS URL for the staging health endpoint")
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="Per-request timeout in seconds (default: 120)",
    )
    parser.add_argument("--output", type=Path, required=True, help="Path for the JSON result")
    parser.add_argument(
        "--preflight-command",
        nargs=argparse.REMAINDER,
        required=True,
        help=(
            "Command that proves zero instances or a fresh revision and prints one JSON receipt; "
            "place this option last"
        ),
    )
    args = parser.parse_args(argv)

    try:
        result = run_benchmark(args.url, args.preflight_command, args.timeout)
    except (RuntimeError, ValueError) as exc:
        print(f"Benchmark aborted: {exc}", file=sys.stderr)
        return 1

    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"Could not write benchmark JSON: {exc}", file=sys.stderr)
        return 1

    print("Run | HTTP | TTFB ms | Total ms | Cold-state evidence")
    for item in result["measurements"]:
        evidence = item["cold_state"]
        print(
            f"{item['run']} | {item['status_code']} | {item['ttfb_ms']:.3f} | "
            f"{item['total_ms']:.3f} | {evidence['mode']}:{evidence['revision']}"
        )
    print(json.dumps(result["statistics"], indent=2))
    print(f"JSON report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
