"""Tests for the US-008 runtime version metadata endpoint."""

from datetime import datetime, timezone
from subprocess import CompletedProcess
from unittest.mock import patch

from fastapi.testclient import TestClient


def _client() -> TestClient:
    """Create a client for a fresh service app without starting model lifespan."""
    from src.vsl.service import create_app

    return TestClient(create_app(), raise_server_exceptions=False)


def _parse_utc_timestamp(value: str) -> datetime:
    """Parse an ISO-8601 timestamp and require a UTC offset."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert parsed.utcoffset() == timezone.utc.utcoffset(parsed)
    return parsed


def test_version_uses_build_environment_metadata(monkeypatch) -> None:
    """Configured model, Git SHA, and build timestamp are returned as-is/UTC."""
    monkeypatch.setenv("VSL_MODEL_VERSION", "v2.3.1")
    monkeypatch.setenv("GIT_SHA", "abc1234")
    monkeypatch.setenv("BUILD_TIME", "2026-11-02T12:15:30+02:00")

    client = _client()
    with patch("src.vsl.service.subprocess.run") as run_git:
        response = client.get("/version")

    assert response.status_code == 200
    assert response.json() == {
        "model_version": "v2.3.1",
        "git_sha": "abc1234",
        "build_time": "2026-11-02T10:15:30Z",
    }
    run_git.assert_not_called()

    openapi = _client().get("/openapi.json").json()
    schema = openapi["components"]["schemas"]["VersionResponse"]
    assert set(schema["properties"]) == {"model_version", "git_sha", "build_time"}


def test_version_falls_back_to_local_git_and_service_start_time(monkeypatch) -> None:
    """Without build variables, use local Git and a generated UTC timestamp."""
    monkeypatch.delenv("VSL_MODEL_VERSION", raising=False)
    monkeypatch.delenv("GIT_SHA", raising=False)
    monkeypatch.delenv("BUILD_TIME", raising=False)

    with patch(
        "src.vsl.service.subprocess.run",
        return_value=CompletedProcess(
            args=["git", "rev-parse", "HEAD"],
            returncode=0,
            stdout="local-commit-sha\n",
            stderr="",
        ),
    ):
        response = _client().get("/version")

    assert response.status_code == 200
    data = response.json()
    assert data["model_version"] == "v1.0"
    assert data["git_sha"] == "local-commit-sha"
    _parse_utc_timestamp(data["build_time"])


def test_version_uses_unknown_when_git_is_unavailable(monkeypatch) -> None:
    """Missing GIT_SHA and unavailable Git produce a safe fallback."""
    monkeypatch.delenv("GIT_SHA", raising=False)

    with patch(
        "src.vsl.service.subprocess.run",
        side_effect=OSError("git unavailable"),
    ):
        response = _client().get("/version")

    assert response.status_code == 200
    assert response.json()["git_sha"] == "unknown"
