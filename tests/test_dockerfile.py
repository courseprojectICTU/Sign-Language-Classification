"""Tests for US-010 Dockerfile and .dockerignore structural constraints and contracts.

Acceptance Criteria:
- AC-010-01: Container build and runtime constraints (BR-005, BR-009, BR-011, BR-025).
"""

import re
from pathlib import Path

import pytest

from src.vsl.config import PROJECT_ROOT

DOCKERFILE_PATH = PROJECT_ROOT / "Dockerfile"
DOCKERIGNORE_PATH = PROJECT_ROOT / ".dockerignore"


def test_ac_010_01_dockerignore_exists_and_excludes_heavy_artifacts() -> None:
    """Verify that .dockerignore exists and excludes heavy local directories and dev artifacts."""
    assert DOCKERIGNORE_PATH.is_file(), ".dockerignore phải tồn tại ở thư mục gốc dự án"
    content = DOCKERIGNORE_PATH.read_text(encoding="utf-8")
    lines = [
        line.strip()
        for line in content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

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

    # Base image: pinned Python 3.12 slim image
    assert re.search(
        r"FROM\s+.*python:3\.12(?:\.\d+)?-slim",
        content,
        re.IGNORECASE,
    ), "Dockerfile phải sử dụng base image python:3.12-slim theo BR-005"

    # System dependencies: libgl1, libglib2.0-0, curl
    assert "libgl1" in content, "Dockerfile phải cài đặt libgl1 cho OpenCV / MediaPipe"
    assert "libglib2.0-0" in content, "Dockerfile phải cài đặt libglib2.0-0"
    assert "curl" in content, "Dockerfile phải cài đặt curl phục vụ HEALTHCHECK"

    # Python dependencies
    assert (
        "requirements-runtime.txt" in content
    ), "Dockerfile phải cài manifest dependencies tối thiểu cho runtime"
    assert re.search(
        r"pip\s+install.*-r\s+requirements-runtime\.txt", content
    ), "Dockerfile phải chạy pip install cho requirements-runtime.txt"

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
    """Verify runtime requirements are installed before copying application source."""
    assert DOCKERFILE_PATH.is_file(), "Dockerfile phải tồn tại ở thư mục gốc dự án"
    content = DOCKERFILE_PATH.read_text(encoding="utf-8")
    lines = content.splitlines()

    req_copy_idx = -1
    src_copy_idx = -1

    for idx, line in enumerate(lines):
        line_clean = line.strip()
        if line_clean.startswith("COPY") and "requirements-runtime.txt" in line_clean:
            req_copy_idx = idx
        elif line_clean.startswith("COPY") and ("src" in line_clean or "src/" in line_clean):
            src_copy_idx = idx

    assert req_copy_idx != -1, "Phải có lệnh COPY requirements-runtime.txt"
    assert src_copy_idx != -1, "Phải có lệnh COPY src/"
    assert (
        req_copy_idx < src_copy_idx
    ), "COPY runtime requirements phải đứng trước COPY src để tận dụng Docker layer cache"


def test_ac_038_multistage_build_is_pinned_and_amd64_only() -> None:
    content = DOCKERFILE_PATH.read_text(encoding="utf-8")
    from_lines = [line.strip() for line in content.splitlines() if line.strip().startswith("FROM ")]

    assert len(from_lines) == 2
    assert all("--platform=linux/amd64" in line for line in from_lines)
    assert all("@sha256:" in line for line in from_lines)
    assert "AS builder" in from_lines[0]
    assert "AS runtime" in from_lines[1]
    assert "COPY --from=builder /opt/venv /opt/venv" in content


def test_ac_038_buildkit_caches_requirements_and_excludes_build_tools_at_runtime() -> None:
    content = DOCKERFILE_PATH.read_text(encoding="utf-8")
    lines = content.splitlines()
    requirements_copy = next(
        index
        for index, line in enumerate(lines)
        if line.strip() == "COPY requirements-runtime.txt ./"
    )
    install = next(
        index
        for index, line in enumerate(lines)
        if "pip install" in line
        and "-r requirements-runtime.txt" in "\n".join(lines[index : index + 2])
    )
    source_copy = next(
        index for index, line in enumerate(lines) if line.strip() == "COPY src ./src"
    )
    assert requirements_copy < install < source_copy
    assert any("--mount=type=cache,target=/root/.cache/pip" in line for line in lines)
    assert "build-essential" in content
    runtime = content.split(" AS runtime", maxsplit=1)[1]
    assert "build-essential" not in runtime
    assert "gcc" not in runtime
    assert "g++" not in runtime
    assert "USER appuser" in runtime


def test_runtime_requirements_are_pinned_and_minimal() -> None:
    requirements = PROJECT_ROOT / "requirements-runtime.txt"
    lines = [
        line.strip()
        for line in requirements.read_text(encoding="ascii").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    full_requirements = {
        line.split("==", maxsplit=1)[0]: line
        for line in (PROJECT_ROOT / "requirements.txt")
        .read_text(encoding="ascii")
        .splitlines()
        if "==" in line
    }

    assert all("==" in line for line in lines)
    assert all(full_requirements.get(line.split("==", maxsplit=1)[0]) == line for line in lines)
    assert all(
        package not in "\n".join(lines)
        for package in ("notebook", "ipykernel", "matplotlib", "pandas", "scikit-learn")
    )


def test_ac_038_ci_uses_gha_cache_and_reports_build_metrics() -> None:
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "docker/build-push-action@" in workflow
    assert "cache-from: type=gha" in workflow
    assert "cache-to: type=gha,mode=max" in workflow
    assert "platforms: linux/amd64" in workflow
    assert "BUILD_START" in workflow
    assert "docker image inspect" in workflow
    assert "GITHUB_STEP_SUMMARY" in workflow
