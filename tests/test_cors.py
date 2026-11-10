"""CORS allowlist and preflight tests for the FastAPI service."""

import pytest
from fastapi.testclient import TestClient


def _client() -> TestClient:
    from src.vsl.service import create_app

    return TestClient(create_app(), raise_server_exceptions=False)


def test_configured_origin_can_preflight_and_read_startup_health(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    origin = "https://vsl-project.pages.dev"
    monkeypatch.setenv("VSL_ALLOWED_ORIGINS", origin)
    client = _client()

    preflight = client.options(
        "/predict",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    health = client.get("/health", headers={"Origin": origin})

    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == origin
    assert "POST" in preflight.headers["access-control-allow-methods"]
    assert health.status_code == 503
    assert health.headers["access-control-allow-origin"] == origin


def test_production_pages_origin_can_preflight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    origin = "https://sign-language-classification.pages.dev"
    monkeypatch.setenv("VSL_ALLOWED_ORIGINS", origin)
    response = _client().options(
        "/predict",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert "POST" in response.headers["access-control-allow-methods"]


def test_unconfigured_origin_is_denied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VSL_ALLOWED_ORIGINS", "https://vsl-project.pages.dev")
    response = _client().options(
        "/predict",
        headers={
            "Origin": "https://untrusted.pages.dev",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_missing_environment_variable_denies_cross_origin_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VSL_ALLOWED_ORIGINS", raising=False)
    response = _client().options(
        "/predict",
        headers={
            "Origin": "https://unconfigured.pages.dev",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.parametrize(
    "configured_origin",
    [
        "*",
        "https://vsl-project.pages.dev/path",
        "ftp://vsl-project.pages.dev",
        "https://vsl-project.pages.dev?query=1",
    ],
)
def test_invalid_or_wildcard_origin_configuration_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    configured_origin: str,
) -> None:
    monkeypatch.setenv("VSL_ALLOWED_ORIGINS", configured_origin)

    from src.vsl.service import create_app

    with pytest.raises(ValueError, match="VSL_ALLOWED_ORIGINS"):
        create_app()
