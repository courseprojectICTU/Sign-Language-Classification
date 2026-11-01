#!/usr/bin/env python3
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
