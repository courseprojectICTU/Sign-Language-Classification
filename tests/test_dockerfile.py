"""Tests for US-010 Dockerfile and .dockerignore structural constraints and contracts.

Acceptance Criteria:
- AC-010-01: Container build and runtime constraints (BR-005, BR-009, BR-011, BR-025).
"""

from pathlib import Path
import re
import pytest

from src.vsl.config import PROJECT_ROOT

DOCKERFILE_PATH = PROJECT_ROOT / "Dockerfile"
DOCKERIGNORE_PATH = PROJECT_ROOT / ".dockerignore"


def test_ac_010_01_dockerignore_exists_and_excludes_heavy_artifacts() -> None:
    """Verify that .dockerignore exists and excludes heavy local directories and dev artifacts."""
    assert DOCKERIGNORE_PATH.is_file(), ".dockerignore phải tồn tại ở thư mục gốc dự án"
    content = DOCKERIGNORE_PATH.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines() if line.strip() and not line.strip().startswith("#")]

    required_exclusions = [
        ".git",
        ".venv",
        "data",
        "tests",
        "docs",
    ]
    for req in required_exclusions:
        assert any(
            req == line or line.startswith(f"{req}/") or line == f"{req}/" or f"*{req}" in line
            for line in lines
        ), f".dockerignore phải loại trừ '{req}' để tối ưu build context"


def test_ac_010_01_dockerfile_exists_and_has_required_directives() -> None:
    """Verify that Dockerfile exists and satisfies all mandatory instructions."""
    assert DOCKERFILE_PATH.is_file(), "Dockerfile phải tồn tại ở thư mục gốc dự án"
    content = DOCKERFILE_PATH.read_text(encoding="utf-8")

    # Base image: python:3.12-slim
    assert re.search(r"FROM\s+.*python:3\.12-slim", content, re.IGNORECASE), (
        "Dockerfile phải sử dụng base image python:3.12-slim theo BR-005"
    )

    # System dependencies: libgl1, libglib2.0-0, curl
    assert "libgl1" in content, "Dockerfile phải cài đặt libgl1 cho OpenCV / MediaPipe"
    assert "libglib2.0-0" in content, "Dockerfile phải cài đặt libglib2.0-0"
    assert "curl" in content, "Dockerfile phải cài đặt curl phục vụ HEALTHCHECK"

    # Python dependencies
    assert "requirements.txt" in content, "Dockerfile phải sao chép và cài đặt requirements.txt"
    assert re.search(r"pip\s+install.*-r\s+requirements\.txt", content), (
        "Dockerfile phải chạy pip install cho requirements.txt"
    )

    # Build argument for commit tracing (BR-009)
    assert "ARG GIT_SHA" in content, "Dockerfile phải khai báo ARG GIT_SHA theo BR-009"
    assert "ENV GIT_SHA" in content, "Dockerfile phải gán ARG GIT_SHA sang ENV GIT_SHA"

    # Port exposure & working directory
    assert re.search(r"EXPOSE\s+8080", content), "Dockerfile phải EXPOSE cổng 8080 cho Cloud Run"
    assert re.search(r"WORKDIR\s+/app", content), "Dockerfile phải đặt WORKDIR /app"

    # Healthcheck (BR-011)
    assert "HEALTHCHECK" in content, "Dockerfile phải cấu hình chỉ thị HEALTHCHECK"
    assert "/health" in content, "Chỉ thị HEALTHCHECK phải gọi endpoint /health"

    # Run command
    assert "uvicorn" in content, "Dockerfile phải sử dụng uvicorn để khởi chạy"
    assert "src.vsl.service:app" in content, "Dockerfile phải trỏ đúng app service"
    assert "8080" in content, "Lệnh khởi chạy phải lắng nghe cổng 8080"


def test_ac_010_01_layer_caching_order_requirements_before_src() -> None:
    """Verify layer caching order: requirements.txt must be copied and installed before copying source code."""
    assert DOCKERFILE_PATH.is_file(), "Dockerfile phải tồn tại ở thư mục gốc dự án"
    content = DOCKERFILE_PATH.read_text(encoding="utf-8")
    lines = content.splitlines()

    req_copy_idx = -1
    src_copy_idx = -1

    for idx, line in enumerate(lines):
        line_clean = line.strip()
        if line_clean.startswith("COPY") and "requirements.txt" in line_clean:
            req_copy_idx = idx
        elif line_clean.startswith("COPY") and ("src" in line_clean or "src/" in line_clean):
            src_copy_idx = idx

    assert req_copy_idx != -1, "Phải có lệnh COPY requirements.txt"
    assert src_copy_idx != -1, "Phải có lệnh COPY src/"
    assert req_copy_idx < src_copy_idx, (
        "Để tối ưu Docker layer cache (BR-025), COPY requirements.txt phải đứng trước COPY src/"
    )
