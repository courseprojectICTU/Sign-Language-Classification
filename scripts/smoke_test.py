#!/usr/bin/env python3
"""Verify health, deployed commit metadata, and prediction on a running VSL API."""

import argparse
import json
import math
import mimetypes
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


class SmokeTestError(RuntimeError):
    """Raised when a deployed service does not satisfy the smoke-test contract."""


def _request_json(
    url: str,
    *,
    method: str = "GET",
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 30,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=data,
        headers=headers or {},
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status_code = response.status
            body = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        raise SmokeTestError(f"{method} {url} returned HTTP {exc.code}: {detail[:300]}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise SmokeTestError(f"{method} {url} network request failed: {exc}") from exc

    if status_code != 200:
        raise SmokeTestError(f"{method} {url} expected HTTP 200, got {status_code}")

    try:
        result = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SmokeTestError(f"{method} {url} returned invalid JSON") from exc

    if not isinstance(result, dict):
        raise SmokeTestError(f"{method} {url} response must be a JSON object")
    return result


def _multipart_image(image_path: Path) -> tuple[bytes, str]:
    if not image_path.is_file():
        raise SmokeTestError(f"Image file does not exist: {image_path}")
    try:
        image_bytes = image_path.read_bytes()
    except OSError as exc:
        raise SmokeTestError(f"Could not read image file {image_path}: {exc}") from exc
    if not image_bytes:
        raise SmokeTestError(f"Image file is empty: {image_path}")

    boundary = f"vsl-smoke-{uuid.uuid4().hex}"
    filename = image_path.name.replace('"', "_")
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    body = b"".join(
        (
            f"--{boundary}\r\n".encode(),
            (f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n').encode(),
            f"Content-Type: {content_type}\r\n\r\n".encode(),
            image_bytes,
            f"\r\n--{boundary}--\r\n".encode(),
        )
    )
    return body, f"multipart/form-data; boundary={boundary}"


def smoke_test(
    url: str,
    *,
    expected_sha: str,
    image_path: Path | None = None,
    timeout: float = 30,
) -> dict[str, str | float]:
    """Run readiness checks and an optional prediction check, raising on failure."""
    parsed_url = urlsplit(url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise SmokeTestError("--url must be an absolute HTTP or HTTPS base URL")
    if parsed_url.username is not None or parsed_url.password is not None:
        raise SmokeTestError("--url must not contain credentials")
    if parsed_url.query or parsed_url.fragment:
        raise SmokeTestError("--url must not contain a query string or fragment")
    if not expected_sha.strip():
        raise SmokeTestError("--expected-sha must not be empty")
    if timeout <= 0 or not math.isfinite(timeout):
        raise SmokeTestError("--timeout must be a finite positive number")

    normalized_url = url.rstrip("/")
    image_body = None
    image_content_type = None
    if image_path is not None:
        image_body, image_content_type = _multipart_image(Path(image_path))

    health = _request_json(f"{normalized_url}/health", timeout=timeout)
    if health.get("model_loaded") is not True:
        raise SmokeTestError("/health did not report model_loaded=true")
    print("PASS /health: model_loaded=true")

    version = _request_json(f"{normalized_url}/version", timeout=timeout)
    actual_sha = version.get("git_sha")
    if actual_sha != expected_sha:
        raise SmokeTestError(
            f"/version git_sha mismatch: expected {expected_sha!r}, got {actual_sha!r}"
        )
    if not isinstance(actual_sha, str):
        raise SmokeTestError("/version git_sha must be a string")
    print(f"PASS /version: git_sha={actual_sha}")

    if image_path is None:
        return {"git_sha": actual_sha}

    if image_body is None or image_content_type is None:
        raise SmokeTestError("Prediction smoke test image was not prepared")
    prediction = _request_json(
        f"{normalized_url}/predict",
        method="POST",
        data=image_body,
        headers={"Content-Type": image_content_type},
        timeout=timeout,
    )
    letter = prediction.get("letter")
    confidence = prediction.get("confidence")
    if (
        prediction.get("status") != "ok"
        or prediction.get("detected") is not True
        or not isinstance(letter, str)
        or not letter
        or isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not math.isfinite(confidence)
        or not 0 <= confidence <= 1
    ):
        raise SmokeTestError("/predict returned an invalid prediction response")
    print(f"PASS /predict: letter={letter}, confidence={confidence:.4f}")
    return {"letter": letter, "confidence": float(confidence)}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Base URL of the deployed API")
    parser.add_argument(
        "--expected-sha",
        required=True,
        help="Git SHA that the deployed /version endpoint must report",
    )
    parser.add_argument(
        "--image",
        type=Path,
        help="Optional valid image; when supplied, also verify POST /predict",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30,
        help="Per-request timeout in seconds (default: 30)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        smoke_test(
            args.url,
            expected_sha=args.expected_sha,
            image_path=args.image,
            timeout=args.timeout,
        )
    except SmokeTestError as exc:
        print(f"Smoke test failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
