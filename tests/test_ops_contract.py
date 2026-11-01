"""Bộ kiểm thử hợp đồng vận hành, CI/CD và kiến trúc Container.

Bao phủ các Acceptance Criteria theo yêu cầu:
- US-023: AC-023-01 (Warm-up ping khi tải trang)
- US-025: AC-025-01 (CORS Cloudflare Pages), AC-025-02 (Phân biệt lỗi 503 cold start)
- US-026: AC-026-01 (CI workflow lint/test/build), AC-026-02 (CI failure blocking)
- US-027: AC-027-01 (Loại bỏ nhánh master, bảo vệ main)
- US-031: AC-031-01 (Rollback traffic < 5 phút), AC-031-02 (Smoke test failure triggers rollback)
- US-035: AC-035-01 (Tài liệu README & Runbook đầy đủ 4 kịch bản)
- US-038: AC-038-01 (Cache layer phụ thuộc), AC-038-02 (Multi-stage & Digest),
          AC-038-03 (Chỉ định platform linux/amd64), AC-038-04 (Đo kích thước & thời gian)
"""

from pathlib import Path
from unittest.mock import MagicMock
import ast
import os
import subprocess
import yaml

try:
    import pytest
except ImportError:
    pytest = None

try:
    from fastapi.testclient import TestClient
    from src.vsl.service import create_app
except ImportError:
    TestClient = None
    create_app = None

ROOT = Path(__file__).resolve().parents[1]
SERVICE_PATH = ROOT / "src" / "vsl" / "service.py"
DOCKERFILE_PATH = ROOT / "Dockerfile"
DOCKERIGNORE_PATH = ROOT / ".dockerignore"
CI_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "ci.yml"
RUNBOOK_PATH = ROOT / "docs" / "RUNBOOK.md"
README_PATH = ROOT / "README.md"
SMOKE_TEST_PATH = ROOT / "scripts" / "smoke_test.py"
ROLLBACK_SH_PATH = ROOT / "scripts" / "rollback.sh"
ROLLBACK_PY_PATH = ROOT / "scripts" / "rollback.py"


# -----------------------------------------------------------------------------
# US-023: Warm-up ping khi tải trang
# -----------------------------------------------------------------------------
def test_ac_023_01_warm_up_ping_endpoint_health():
    """AC-023-01: Endpoint /health sẵn sàng phản hồi ping từ frontend khi cold start."""
    if create_app and TestClient:
        app = create_app()
        app.state.model = None  # Giả lập container vừa thức dậy, chưa nạp xong model
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/health")
        assert resp.status_code in [200, 503]
        data = resp.json()
        assert "status" in data
        assert "model_loaded" in data
    else:
        # Static AST contract verification khi chạy môi trường chưa cài FastAPI
        assert SERVICE_PATH.is_file()
        content = SERVICE_PATH.read_text(encoding="utf-8")
        assert '@app.get(\n        "/health"' in content or '"/health"' in content
        assert "model_loaded" in content
        assert "status.HTTP_503_SERVICE_UNAVAILABLE" in content


# -----------------------------------------------------------------------------
# US-025: CORS và xử lý lỗi mạng
# -----------------------------------------------------------------------------
def test_ac_025_01_cors_allowed_origin_and_preflight():
    """AC-025-01: Origin Cloudflare Pages được chấp nhận, preflight OPTIONS trả đúng header."""
    if create_app and TestClient:
        app = create_app()
        app.state.model = MagicMock()
        client = TestClient(app)

        # 1. Preflight OPTIONS
        opt_resp = client.options(
            "/predict",
            headers={
                "Origin": "https://vsl-frontend.pages.dev",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert opt_resp.status_code == 200
        assert opt_resp.headers.get("access-control-allow-origin") == "https://vsl-frontend.pages.dev"
        assert "POST" in opt_resp.headers.get("access-control-allow-methods", "")

        # 2. Origin pages.dev preview subdomain (regex matching)
        preview_resp = client.get(
            "/health",
            headers={"Origin": "https://pr-12.vsl-frontend.pages.dev"},
        )
        assert preview_resp.status_code == 200
        assert preview_resp.headers.get("access-control-allow-origin") == "https://pr-12.vsl-frontend.pages.dev"
    else:
        content = SERVICE_PATH.read_text(encoding="utf-8")
        assert "CORSMiddleware" in content
        assert "https://vsl-frontend.pages.dev" in content
        assert "allow_origin_regex" in content
        assert "OPTIONS" in content


def test_ac_025_02_backend_503_distinction():
    """AC-025-02: Backend trả 503 khi đang khởi động nguội, phân biệt rõ với lỗi mạng thông thường."""
    if create_app and TestClient:
        app = create_app()
        app.state.model = None
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/predict", files={"file": ("test.jpg", b"fake", "image/jpeg")})
        assert resp.status_code == 503
        detail = resp.json().get("detail", "")
        assert "chưa sẵn sàng" in detail or "khởi động" in detail
    else:
        content = SERVICE_PATH.read_text(encoding="utf-8")
        assert "status.HTTP_503_SERVICE_UNAVAILABLE" in content
        assert "Mô hình nhận diện chưa sẵn sàng" in content or "chưa sẵn sàng" in content


# -----------------------------------------------------------------------------
# US-026: Pipeline CI chạy lint, test và docker build
# -----------------------------------------------------------------------------
def test_ac_026_01_ci_workflow_structure_and_jobs():
    """AC-026-01: File .github/workflows/ci.yml tồn tại và có đầy đủ các bước lint, test, docker build."""
    assert CI_WORKFLOW_PATH.is_file(), f"Không tìm thấy CI workflow tại {CI_WORKFLOW_PATH}"
    content = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    workflow = yaml.safe_load(content)

    jobs = workflow.get("jobs", {})
    assert "lint-and-test" in jobs, "CI thiếu job lint-and-test"
    assert "docker-build" in jobs, "CI thiếu job docker-build"

    # docker build không push
    build_steps = jobs["docker-build"].get("steps", [])
    build_step = next((s for s in build_steps if "docker/build-push-action" in str(s.get("uses", ""))), None)
    assert build_step is not None, "Thiếu bước docker/build-push-action"
    assert build_step.get("with", {}).get("push") is False, "Docker build trong CI KHÔNG được phép push (TSK-050)"


def test_ac_026_02_ci_failure_blocking():
    """AC-026-02: Kiểm tra cấu hình CI yêu cầu lint-and-test thành công trước khi chạy docker build."""
    content = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    workflow = yaml.safe_load(content)
    docker_job = workflow.get("jobs", {}).get("docker-build", {})
    assert docker_job.get("needs") == "lint-and-test", "docker-build phải phụ thuộc (needs) vào lint-and-test"


# -----------------------------------------------------------------------------
# US-027: Chốt nhánh main và bảo vệ nhánh (BR-021)
# -----------------------------------------------------------------------------
def test_ac_027_01_no_master_branch():
    """AC-027-01: Nhánh master không được tồn tại trong Git, chỉ có main và develop (BR-021)."""
    res = subprocess.run(
        ["git", "branch", "-a"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    branches = res.stdout.splitlines()
    master_branches = [b.strip() for b in branches if "master" in b and not "backlog" in b]
    assert len(master_branches) == 0, f"Phát hiện nhánh master còn tồn tại: {master_branches}. Cần xóa theo BR-021."


# -----------------------------------------------------------------------------
# US-031: Rollback backend bằng traffic split và diễn tập
# -----------------------------------------------------------------------------
def test_ac_031_01_rollback_scripts_exist():
    """AC-031-01: Script rollback tồn tại ở cả 2 định dạng Bash và Python, hỗ trợ gcloud update-traffic."""
    assert ROLLBACK_SH_PATH.is_file(), "Thiếu scripts/rollback.sh"
    assert ROLLBACK_PY_PATH.is_file(), "Thiếu scripts/rollback.py"

    sh_content = ROLLBACK_SH_PATH.read_text(encoding="utf-8")
    assert "update-traffic" in sh_content
    assert "--to-revisions" in sh_content

    py_content = ROLLBACK_PY_PATH.read_text(encoding="utf-8")
    assert "update-traffic" in py_content
    assert "--to-revisions" in py_content


def test_ac_031_02_smoke_test_failure_triggers_exit_code():
    """AC-031-02: Script smoke_test.py trả mã thoát 1 khi dịch vụ lỗi để dừng pipeline và kích hoạt hoàn tác."""
    assert SMOKE_TEST_PATH.is_file(), "Thiếu scripts/smoke_test.py"
    # Chạy smoke test tới một cổng không có dịch vụ nào chạy
    res = subprocess.run(
        ["python", str(SMOKE_TEST_PATH), "--url", "http://127.0.0.1:59999", "--timeout", "1"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert res.returncode != 0, f"Smoke test với URL lỗi phải trả mã thoát khác 0, thực tế: {res.returncode}"


# -----------------------------------------------------------------------------
# US-035: README và runbook xử lý sự cố (BR-024)
# -----------------------------------------------------------------------------
def test_ac_035_01_runbook_contains_all_four_scenarios():
    """AC-035-01: Runbook chứa đầy đủ hướng dẫn xử lý 4 kịch bản sự cố trọng tâm."""
    assert RUNBOOK_PATH.is_file(), "Thiếu docs/RUNBOOK.md"
    content = RUNBOOK_PATH.read_text(encoding="utf-8")

    assert "Khởi động nguội chậm" in content, "Runbook thiếu kịch bản Cold start"
    assert "Pipeline CI báo đỏ" in content, "Runbook thiếu kịch bản CI đỏ"
    assert "Smoke test thất bại" in content, "Runbook thiếu kịch bản Smoke test fail & Rollback"
    assert "Vượt ngân sách" in content or "vượt chi phí" in content.lower(), "Runbook thiếu kịch bản chi phí"


# -----------------------------------------------------------------------------
# US-038: Tối ưu và tái lập quá trình build image (BR-025)
# -----------------------------------------------------------------------------
def test_ac_038_01_layer_cache_order():
    """AC-038-01: COPY requirements.txt trước khi COPY mã nguồn để tối ưu Docker layer cache."""
    assert DOCKERFILE_PATH.is_file(), "Thiếu Dockerfile"
    lines = DOCKERFILE_PATH.read_text(encoding="utf-8").splitlines()

    req_idx = -1
    src_idx = -1
    for i, line in enumerate(lines):
        if "COPY requirements.txt" in line and req_idx == -1:
            req_idx = i
        if "COPY src" in line and src_idx == -1:
            src_idx = i

    assert req_idx != -1, "Dockerfile thiếu bước COPY requirements.txt"
    assert src_idx != -1, "Dockerfile thiếu bước COPY src"
    assert req_idx < src_idx, "COPY requirements.txt phải đứng trước COPY src để tận dụng cache"


def test_ac_038_02_multistage_and_digest():
    """AC-038-02: Dockerfile dùng multi-stage (builder/runtime) và ghim base image bằng digest sha256."""
    content = DOCKERFILE_PATH.read_text(encoding="utf-8")
    assert "AS builder" in content, "Dockerfile thiếu stage builder"
    assert "AS runtime" in content, "Dockerfile thiếu stage runtime"
    assert "@sha256:" in content, "Base image phải ghim bằng digest SHA-256 (BR-025)"
    assert "COPY --from=builder /opt/venv /opt/venv" in content, "Runtime stage phải copy virtualenv từ builder"


def test_ac_038_03_explicit_platform_linux_amd64():
    """AC-038-03: Mọi lệnh FROM trong Dockerfile đều chỉ định rõ --platform=linux/amd64."""
    content = DOCKERFILE_PATH.read_text(encoding="utf-8")
    for line in content.splitlines():
        if line.strip().startswith("FROM "):
            assert "--platform=linux/amd64" in line, f"Dòng FROM thiếu platform linux/amd64: {line}"


def test_ac_038_04_ci_measures_image_metrics():
    """AC-038-04: Pipeline CI có bước đo lường và in ra kích thước image và thời gian build."""
    content = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "BUILD_START" in content
    assert "GITHUB_STEP_SUMMARY" in content
    assert "docker image inspect" in content or "Size" in content
