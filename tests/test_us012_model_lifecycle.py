"""Tests for US-012 model loading lifecycle and startup timing logs."""

import io
import logging
import re
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from src.vsl.labels import NUM_CLASSES


def _create_image_bytes() -> bytes:
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    success, encoded = cv2.imencode(".jpg", image)
    assert success
    return encoded.tobytes()


def test_model_loads_once_before_ten_predict_requests_and_logs_duration(
    caplog: pytest.LogCaptureFixture,
) -> None:
    from src.vsl.service import create_app

    app = create_app()
    model = MagicMock(name="loaded_model")
    probabilities = np.zeros((1, NUM_CLASSES), dtype=np.float32)
    probabilities[0, 0] = 1.0
    model.return_value.numpy.return_value = probabilities
    image_bytes = _create_image_bytes()
    caplog.set_level(logging.INFO, logger="vsl.service")

    with (
        patch("keras.models.load_model", return_value=model) as load_model,
        patch(
            "src.vsl.service.extract_landmarks_from_image",
            return_value=([0.5] * 93, True, True),
        ),
        patch("src.vsl.service.preprocess_heatmap", side_effect=lambda batch: batch),
        TestClient(app) as client,
    ):
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["model_loaded"] is True
        assert load_model.call_count == 1

        for _ in range(10):
            response = client.post(
                "/predict",
                files={"file": ("sample.jpg", io.BytesIO(image_bytes), "image/jpeg")},
            )
            assert response.status_code == 200
            assert response.json()["status"] == "ok"

        assert load_model.call_count == 1
        assert model.call_count == 10

    duration_logs = [
        record.getMessage()
        for record in caplog.records
        if record.name == "vsl.service" and "duration_ms=" in record.getMessage()
    ]
    assert len(duration_logs) == 1
    duration = re.search(r"duration_ms=(\d+(?:\.\d+)?)", duration_logs[0])
    assert duration is not None, f"Startup log lacks numeric model-load duration: {duration_logs}"
    assert float(duration.group(1)) >= 0


def test_health_stays_unavailable_when_startup_model_load_fails() -> None:
    from src.vsl.service import create_app

    app = create_app()
    with (
        patch("keras.models.load_model", side_effect=OSError("model unavailable")),
        TestClient(app) as client,
    ):
        response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["model_loaded"] is False
