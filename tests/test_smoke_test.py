"""Tests for the deployment smoke-test CLI."""

from pathlib import Path

import pytest

from scripts import smoke_test


def _image_file(tmp_path: Path) -> Path:
    image = tmp_path / "sample.png"
    image.write_bytes(b"sample image bytes")
    return image


def test_smoke_test_checks_health_version_and_prediction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    image = _image_file(tmp_path)
    calls = []

    def request_json(
        url: str,
        *,
        method: str = "GET",
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 30,
    ) -> dict[str, object]:
        calls.append((url, method, data, headers, timeout))
        if url.endswith("/health"):
            return {"model_loaded": True}
        if url.endswith("/version"):
            return {"git_sha": "commit-123"}
        assert method == "POST"
        assert headers is not None
        assert headers["Content-Type"].startswith("multipart/form-data; boundary=")
        assert data is not None
        assert b'name="file"; filename="sample.png"' in data
        assert image.read_bytes() in data
        return {
            "status": "ok",
            "detected": True,
            "letter": "a",
            "confidence": 0.95,
        }

    monkeypatch.setattr(smoke_test, "_request_json", request_json)

    result = smoke_test.smoke_test(
        "https://service.example",
        expected_sha="commit-123",
        image_path=image,
        timeout=7,
    )

    assert result == {"letter": "a", "confidence": 0.95}
    assert [call[1] for call in calls] == ["GET", "GET", "POST"]
    assert all(call[4] == 7 for call in calls)
    assert "PASS /health" in capsys.readouterr().out


def test_smoke_test_stops_when_model_is_not_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []

    def request_json(url: str, **kwargs: object) -> dict[str, object]:
        calls.append(url)
        return {"model_loaded": False}

    monkeypatch.setattr(smoke_test, "_request_json", request_json)

    with pytest.raises(smoke_test.SmokeTestError, match="model_loaded"):
        smoke_test.smoke_test(
            "http://localhost:8080",
            expected_sha="commit-123",
            image_path=_image_file(tmp_path),
        )

    assert len(calls) == 1


def test_smoke_test_rejects_mismatched_deployment_sha(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []

    def request_json(url: str, **kwargs: object) -> dict[str, object]:
        calls.append(url)
        return {"model_loaded": True} if url.endswith("/health") else {"git_sha": "old"}

    monkeypatch.setattr(smoke_test, "_request_json", request_json)

    with pytest.raises(smoke_test.SmokeTestError, match="git_sha"):
        smoke_test.smoke_test(
            "http://localhost:8080",
            expected_sha="commit-123",
            image_path=_image_file(tmp_path),
        )

    assert len(calls) == 2


def test_predict_http_failure_returns_nonzero_exit_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def request_json(url: str, **kwargs: object) -> dict[str, object]:
        if url.endswith("/health"):
            return {"model_loaded": True}
        if url.endswith("/version"):
            return {"git_sha": "commit-123"}
        raise smoke_test.SmokeTestError("POST /predict returned HTTP 500")

    monkeypatch.setattr(smoke_test, "_request_json", request_json)

    result = smoke_test.main(
        [
            "--url",
            "http://localhost:8080",
            "--expected-sha",
            "commit-123",
            "--image",
            str(_image_file(tmp_path)),
        ]
    )

    assert result != 0
    assert "HTTP 500" in capsys.readouterr().err


def test_smoke_test_rejects_invalid_prediction_response(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def request_json(url: str, **kwargs: object) -> dict[str, object]:
        if url.endswith("/health"):
            return {"model_loaded": True}
        if url.endswith("/version"):
            return {"git_sha": "commit-123"}
        return {
            "status": "no_hand",
            "detected": False,
            "letter": None,
            "confidence": 0.0,
        }

    monkeypatch.setattr(smoke_test, "_request_json", request_json)

    with pytest.raises(smoke_test.SmokeTestError, match="prediction"):
        smoke_test.smoke_test(
            "http://localhost:8080",
            expected_sha="commit-123",
            image_path=_image_file(tmp_path),
        )


def test_smoke_test_rejects_missing_image_before_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    called = False

    def request_json(url: str, **kwargs: object) -> dict[str, object]:
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr(smoke_test, "_request_json", request_json)

    with pytest.raises(smoke_test.SmokeTestError, match="Image file"):
        smoke_test.smoke_test(
            "http://localhost:8080",
            expected_sha="commit-123",
            image_path=tmp_path / "missing.png",
        )

    assert not called


def test_request_json_rejects_non_200_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Response:
        status = 201

        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"ok": true}'

    monkeypatch.setattr(
        smoke_test.urllib.request, "urlopen", lambda *args, **kwargs: Response()
    )

    with pytest.raises(smoke_test.SmokeTestError, match="expected HTTP 200"):
        smoke_test._request_json("https://service.example/health")


def test_request_json_surfaces_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_http_error(*args: object, **kwargs: object) -> None:
        raise smoke_test.urllib.error.HTTPError(
            "https://service.example/predict",
            500,
            "Internal Server Error",
            None,
            None,
        )

    monkeypatch.setattr(smoke_test.urllib.request, "urlopen", raise_http_error)

    with pytest.raises(smoke_test.SmokeTestError, match="HTTP 500"):
        smoke_test._request_json("https://service.example/predict", method="POST")
