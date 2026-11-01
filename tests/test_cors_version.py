"""Kiểm thử cho US-025 (CORS) và US-017 (/version endpoint).

Tuân thủ:
- BR-018: Same-Origin or Explicit CORS (không dùng wildcard cho mọi origin).
- BR-013: Deploy-Then-Shift Traffic (endpoint /version phục vụ smoke test).
"""

from unittest.mock import MagicMock
import os
import pytest
from fastapi.testclient import TestClient

from src.vsl.service import create_app


@pytest.fixture
def client():
    """Tạo TestClient với mock model đã nạp."""
    app = create_app()
    app.state.model = MagicMock(name="mock_model")
    app.state.model_version = "v1.0"
    return TestClient(app)


# ---------------------------------------------------------------- US-025: CORS Tests
def test_cors_allowed_origin_pages(client):
    """AC-025-01: Request từ Cloudflare Pages origin được chấp nhận với Access-Control-Allow-Origin tương ứng."""
    response = client.get(
        "/health",
        headers={"Origin": "https://vsl-frontend.pages.dev"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://vsl-frontend.pages.dev"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_allowed_origin_preview_pages(client):
    """AC-025-01: Request từ Cloudflare Pages preview URL (regex) được chấp nhận."""
    response = client.get(
        "/health",
        headers={"Origin": "https://feat-preview.vsl-frontend.pages.dev"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://feat-preview.vsl-frontend.pages.dev"


def test_cors_preflight_options(client):
    """AC-025-02: Preflight OPTIONS request trả về các header cho phép phương thức và thông tin xác thực."""
    response = client.options(
        "/predict",
        headers={
            "Origin": "https://vsl-frontend.pages.dev",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://vsl-frontend.pages.dev"
    assert "POST" in response.headers.get("access-control-allow-methods", "")


def test_cors_disallowed_origin(client):
    """BR-018: Origin không được cấp quyền sẽ KHÔNG có Access-Control-Allow-Origin tương ứng."""
    response = client.get(
        "/health",
        headers={"Origin": "https://unauthorized-domain.com"},
    )
    # FastAPI CORSMiddleware không gửi Access-Control-Allow-Origin nếu origin không hợp lệ
    assert response.headers.get("access-control-allow-origin") != "https://unauthorized-domain.com"


# ---------------------------------------------------------------- US-017: /version Tests
def test_version_endpoint_default(client):
    """AC-017-01: GET /version trả về status 200 với các trường version, git_sha, model_version."""
    response = client.get("/version")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "git_sha" in data
    assert "model_version" in data
    assert data["version"] == "1.0.0"


def test_version_endpoint_with_custom_git_sha(monkeypatch):
    """AC-017-01: GET /version phản ánh đúng GIT_SHA được cấu hình qua biến môi trường."""
    monkeypatch.setenv("GIT_SHA", "commit-abc1234")
    app = create_app()
    client = TestClient(app)
    response = client.get("/version")
    assert response.status_code == 200
    data = response.json()
    assert data["git_sha"] == "commit-abc1234"

