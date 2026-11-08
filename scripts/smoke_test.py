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
        raise SmokeTestError(
            f"{method} {url} returned HTTP {exc.code}: {detail[:300]}"
        ) from exc
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
            (
                f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            ).encode(),
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
    image_path: Path,
    timeout: float = 30,
) -> dict[str, str | float]:
    """Run all smoke checks, raising SmokeTestError on any failed requirement."""
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
    print(f"PASS /version: git_sha={actual_sha}")

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
        required=True,
        type=Path,
        help="Path to a valid image with a detectable hand and face",
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
"""Script kiểm thử khói (Smoke Test) tự động sau triển khai (US-017, BR-013).

Chức năng:
- Gọi GET /health: mong đợi HTTP 200, status=="ok", model_loaded==True.
- Gọi GET /version: mong đợi HTTP 200, git_sha khớp commit (nếu có yêu cầu).
- Gọi POST /predict: gửi ảnh mẫu thử nghiệm, mong đợi HTTP 200 và cấu trúc phản hồi hợp lệ.
- Trả mã thoát (exit code) 0 khi toàn bộ kiểm tra thành công, 1 khi có bất kỳ bước nào thất bại.
- Sử dụng hoàn toàn Python Standard Library (không cần cài thêm dependencies).

Sử dụng:
    python scripts/smoke_test.py --url https://<service-url>.run.app
    python scripts/smoke_test.py --url http://localhost:8080 --expected-sha 06095d7
"""

import argparse
import base64
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

# Bảo đảm hiển thị tiếng Việt an toàn trên console Windows không bị UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ảnh JPEG 50x50 trắng hợp lệ mã hóa base64 (thuần chuẩn, không phụ thuộc opencv/numpy)
DUMMY_JPEG_B64 = (
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAIBAQEBAQIBAQECAgICAgQDAgICAgUEBAMEBgUGBgY"
    "FBgYGBwkIBgcJBwYGCAsICQoKCgoKBggLDAsKDAkKCgr/2wBDAQICAgICAgUDAwUKBwYHCgoKCgo"
    "KCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgr/wAARCAAyADIDASIA"
    "AhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQA"
    "AAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3"
    "ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWm"
    "p6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEA"
    "AwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSEx"
    "BhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElK"
    "U1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3"
    "uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD9/KKK"
    "KACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAoooo"
    "AKKKKAP/2Q=="
)


def log_step(name: str, status: str, detail: str = "", duration_ms: float = 0.0):
    symbol = "✅ PASS" if status == "PASS" else "❌ FAIL"
    time_str = f"({duration_ms:.1f}ms)" if duration_ms > 0 else ""
    print(f"[{symbol}] {name} {time_str} - {detail}")


def run_health_check(base_url: str, timeout: int) -> bool:
    url = f"{base_url.rstrip('/')}/health"
    start = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "VSL-SmokeTest/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            duration = (time.time() - start) * 1000
            if resp.status != 200:
                log_step("GET /health", "FAIL", f"Mã trạng thái {resp.status} != 200", duration)
                return False
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") != "ok" or data.get("model_loaded") is not True:
                log_step("GET /health", "FAIL", f"Phản hồi không hợp lệ: {data}", duration)
                return False
            log_step(
                "GET /health",
                "PASS",
                f"Model đã nạp (version={data.get('model_version')})",
                duration,
            )
            return True
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        json.JSONDecodeError,
        TimeoutError,
        OSError,
    ) as exc:
        duration = (time.time() - start) * 1000
        log_step("GET /health", "FAIL", f"Lỗi kết nối: {exc}", duration)
        return False


def run_version_check(base_url: str, expected_sha: str | None, timeout: int) -> bool:
    url = f"{base_url.rstrip('/')}/version"
    start = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "VSL-SmokeTest/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            duration = (time.time() - start) * 1000
            if resp.status != 200:
                log_step("GET /version", "FAIL", f"Mã trạng thái {resp.status} != 200", duration)
                return False
            data = json.loads(resp.read().decode("utf-8"))
            git_sha = data.get("git_sha", "")
            if expected_sha and not git_sha.startswith(expected_sha):
                log_step(
                    "GET /version",
                    "FAIL",
                    f"git_sha '{git_sha}' không khớp mong đợi '{expected_sha}'",
                    duration,
                )
                return False
            log_step(
                "GET /version",
                "PASS",
                f"version={data.get('version')}, git_sha={git_sha}",
                duration,
            )
            return True
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        json.JSONDecodeError,
        TimeoutError,
        OSError,
    ) as exc:
        duration = (time.time() - start) * 1000
        log_step("GET /version", "FAIL", f"Lỗi kết nối: {exc}", duration)
        return False


def run_predict_check(base_url: str, timeout: int) -> bool:
    url = f"{base_url.rstrip('/')}/predict"
    start = time.time()
    try:
        image_bytes = base64.b64decode(DUMMY_JPEG_B64)
        boundary = "----VSLSmokeTestBoundary7MA4YWxkTrZu0gW"

        body = io.BytesIO()
        body.write(f"--{boundary}\r\n".encode())
        body.write(b'Content-Disposition: form-data; name="file"; filename="test.jpg"\r\n')
        body.write(b"Content-Type: image/jpeg\r\n\r\n")
        body.write(image_bytes)
        body.write(b"\r\n")
        body.write(f"--{boundary}--\r\n".encode())

        req_data = body.getvalue()
        headers = {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(req_data)),
            "User-Agent": "VSL-SmokeTest/1.0",
        }

        req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            duration = (time.time() - start) * 1000
            if resp.status != 200:
                log_step("POST /predict", "FAIL", f"Mã trạng thái {resp.status} != 200", duration)
                return False
            data = json.loads(resp.read().decode("utf-8"))
            if "detected" not in data:
                log_step(
                    "POST /predict",
                    "FAIL",
                    f"Thiếu trường 'detected' trong phản hồi: {data}",
                    duration,
                )
                return False
            log_step(
                "POST /predict",
                "PASS",
                f"Phản hồi hợp lệ (detected={data.get('detected')})",
                duration,
            )
            return True
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        json.JSONDecodeError,
        TimeoutError,
        OSError,
    ) as exc:
        duration = (time.time() - start) * 1000
        log_step("POST /predict", "FAIL", f"Lỗi kiểm thử POST /predict: {exc}", duration)
        return False


def main():
    parser = argparse.ArgumentParser(description="VSL API Smoke Test (US-017)")
    parser.add_argument(
        "--url",
        default=os.getenv("SERVICE_URL", "http://localhost:8080"),
        help="Base URL của dịch vụ",
    )
    parser.add_argument(
        "--expected-sha", default=os.getenv("EXPECTED_GIT_SHA"), help="Git commit SHA mong đợi"
    )
    parser.add_argument("--timeout", type=int, default=30, help="Thời gian chờ mỗi request (giây)")
    args = parser.parse_args()

    print("=" * 60)
    print(f"BẮT ĐẦU SMOKE TEST DỊCH VỤ: {args.url}")
    print(f"Thời gian: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    all_passed = True

    # 1. Kiểm tra /health
    if not run_health_check(args.url, args.timeout):
        all_passed = False

    # 2. Kiểm tra /version
    if not run_version_check(args.url, args.expected_sha, args.timeout):
        all_passed = False

    # 3. Kiểm tra /predict
    if not run_predict_check(args.url, args.timeout):
        all_passed = False

    print("=" * 60)
    if all_passed:
        print("🎉 TẤT CẢ CÁC BƯỚC SMOKE TEST ĐỀU ĐẠT CHUẨN (PASS)!")
        sys.exit(0)
    else:
        print("💥 SMOKE TEST THẤT BẠI (FAIL) - YÊU CẦU HOÀN TÁC HOẶC KIỂM TRA LẠI!")
        sys.exit(1)


if __name__ == "__main__":
    main()