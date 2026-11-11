"""Tests for US-009 input format and 5 MB upload size validation (BR-010)."""

import io
import logging
import re
from datetime import datetime
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from src.vsl.labels import NUM_CLASSES

MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def _create_image_bytes(ext: str = ".jpg") -> bytes:
    img = np.full((64, 64, 3), 120, dtype=np.uint8)
    ok, encoded = cv2.imencode(ext, img)
    assert ok
    return encoded.tobytes()


def _client_with_mock_model() -> tuple[TestClient, MagicMock]:
    from src.vsl.service import create_app

    app = create_app()
    probs = np.zeros((1, NUM_CLASSES), dtype=np.float32)
    probs[0, 0] = 1.0
    model = MagicMock()
    model.return_value.numpy.return_value = probs
    app.state.model = model
    app.state.model_version = "v1.0"
    return TestClient(app, raise_server_exceptions=False), model


def _assert_rejection_warning_log(
    caplog: pytest.LogCaptureFixture,
    *,
    expected_status: int,
    expected_reason: str,
    forbidden_substring: str | None = None,
) -> None:
    warnings = [
        rec.getMessage()
        for rec in caplog.records
        if rec.name == "vsl.service" and rec.levelno == logging.WARNING
    ]
    assert len(warnings) == 1, f"Expected 1 rejection WARNING log, got: {warnings}"
    msg = warnings[0]
    assert "upload_rejected" in msg
    assert f"status_code={expected_status}" in msg
    assert f"reason={expected_reason}" in msg
    assert "content_type=" in msg
    assert "bytes_read=" in msg
    ts_match = re.search(r"timestamp=(\S+)", msg)
    assert ts_match is not None, f"Missing timestamp in log: {msg}"
    parsed = datetime.fromisoformat(ts_match.group(1).replace("Z", "+00:00"))
    assert parsed.utcoffset() is not None, f"Timestamp must include UTC timezone: {msg}"
    if forbidden_substring:
        assert forbidden_substring not in msg


def test_ac_009_01_pdf_renamed_as_jpg_returns_415(caplog: pytest.LogCaptureFixture) -> None:
    """AC-009-01: A PDF disguised as .jpg (image/jpeg) must return HTTP 415."""
    client, model = _client_with_mock_model()
    caplog.set_level(logging.WARNING, logger="vsl.service")
    pdf_payload = b"%PDF-1.4\n%SECRET_PAYLOAD_MARKER\n1 0 obj\n<<>>\nendobj\n%%EOF"

    with patch("src.vsl.service.extract_landmarks_from_image") as mock_extract:
        response = client.post(
            "/predict",
            files={"file": ("tep_gia_anh.jpg", io.BytesIO(pdf_payload), "image/jpeg")},
        )

    assert response.status_code == 415
    assert "detail" in response.json()
    mock_extract.assert_not_called()
    model.assert_not_called()
    _assert_rejection_warning_log(
        caplog,
        expected_status=415,
        expected_reason="invalid_file_signature",
        forbidden_substring="SECRET_PAYLOAD_MARKER",
    )


@pytest.mark.parametrize(
    ("filename", "content_type", "payload"),
    [
        ("doc.pdf", "application/pdf", b"%PDF-1.7\n"),
        ("blob.bin", "application/octet-stream", b"\xff\xd8\xff\xe0abc"),
        ("anim.webp", "image/webp", b"RIFF\x00\x00\x00\x00WEBP"),
        ("anim.gif", "image/gif", b"GIF89a"),
        ("note.txt", "text/plain", b"hello"),
        ("empty_mime.jpg", "", b"\xff\xd8\xff\xe0"),
    ],
)
def test_br_010_disallowed_content_type_returns_415(
    filename: str,
    content_type: str,
    payload: bytes,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """BR-010: Non-JPEG/JPG/PNG Content-Type is rejected with HTTP 415 before decoding."""
    client, model = _client_with_mock_model()
    caplog.set_level(logging.WARNING, logger="vsl.service")

    with patch("src.vsl.service.extract_landmarks_from_image") as mock_extract:
        response = client.post(
            "/predict",
            files={"file": (filename, io.BytesIO(payload), content_type)},
        )

    assert response.status_code == 415
    assert "detail" in response.json()
    mock_extract.assert_not_called()
    model.assert_not_called()
    _assert_rejection_warning_log(
        caplog,
        expected_status=415,
        expected_reason="unsupported_content_type",
    )


def test_br_010_mismatched_png_bytes_under_jpeg_mime_returns_415() -> None:
    """PNG bytes uploaded as image/jpeg or JPEG bytes as image/png return 415."""
    client, model = _client_with_mock_model()
    png_bytes = _create_image_bytes(".png")
    jpeg_bytes = _create_image_bytes(".jpg")

    with patch("src.vsl.service.extract_landmarks_from_image") as mock_extract:
        resp1 = client.post(
            "/predict",
            files={"file": ("fake.jpg", io.BytesIO(png_bytes), "image/jpeg")},
        )
        resp2 = client.post(
            "/predict",
            files={"file": ("fake.png", io.BytesIO(jpeg_bytes), "image/png")},
        )

    assert resp1.status_code == 415
    assert resp2.status_code == 415
    mock_extract.assert_not_called()
    model.assert_not_called()


def test_ac_009_02_image_20mb_returns_413_with_5mb_limit_message(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """AC-009-02: A 20 MB image must return HTTP 413 mentioning the 5 MB limit."""
    client, model = _client_with_mock_model()
    caplog.set_level(logging.WARNING, logger="vsl.service")
    oversized_jpeg = b"\xff\xd8\xff\xe0" + (b"\x00" * (20 * 1024 * 1024 - 4))

    with patch("src.vsl.service.extract_landmarks_from_image") as mock_extract:
        response = client.post(
            "/predict",
            files={"file": ("anh_20mb.jpg", io.BytesIO(oversized_jpeg), "image/jpeg")},
        )

    assert response.status_code == 413
    detail = response.json().get("detail", "")
    assert "5 MB" in detail
    mock_extract.assert_not_called()
    model.assert_not_called()
    _assert_rejection_warning_log(
        caplog,
        expected_status=413,
        expected_reason="payload_too_large",
    )


def test_br_010_size_boundary_5mb_plus_one_byte_returns_413() -> None:
    """5 MB + 1 byte is rejected with 413."""
    client, model = _client_with_mock_model()
    over_by_one = b"\xff\xd8\xff\xe0" + (b"\x00" * (MAX_UPLOAD_BYTES + 1 - 4))

    with patch("src.vsl.service.extract_landmarks_from_image") as mock_extract:
        response = client.post(
            "/predict",
            files={"file": ("over.jpg", io.BytesIO(over_by_one), "image/jpeg")},
        )

    assert response.status_code == 413
    assert "5 MB" in response.json().get("detail", "")
    mock_extract.assert_not_called()
    model.assert_not_called()


def test_br_010_exact_5mb_payload_passes_size_boundary() -> None:
    """Exactly 5 * 1024 * 1024 bytes passes size and signature checks into image decoding."""
    client, _ = _client_with_mock_model()
    exact_5mb_jpeg = b"\xff\xd8\xff\xe0" + (b"\x00" * (MAX_UPLOAD_BYTES - 4))

    with (
        patch(
            "src.vsl.service.extract_landmarks_from_image",
            return_value=([0.5] * 93, True, True),
        ) as mock_extract,
        patch("src.vsl.service.preprocess_heatmap", side_effect=lambda batch: batch),
    ):
        response = client.post(
            "/predict",
            files={"file": ("exact_5mb.jpg", io.BytesIO(exact_5mb_jpeg), "image/jpeg")},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    mock_extract.assert_called_once()
    assert len(mock_extract.call_args.args[0]) == MAX_UPLOAD_BYTES


@pytest.mark.parametrize(
    ("ext", "filename", "content_type"),
    [
        (".jpg", "sample.jpeg", "image/jpeg"),
        (".jpg", "sample.jpg", "image/jpg"),
        (".jpg", "upper.jpg", "IMAGE/JPG; charset=binary"),
        (".png", "sample.png", "image/png"),
    ],
)
def test_br_010_accepts_valid_jpeg_jpg_and_png_uploads(
    ext: str,
    filename: str,
    content_type: str,
) -> None:
    """Valid JPEG, JPG, and PNG uploads within 5 MB succeed with HTTP 200."""
    client, _ = _client_with_mock_model()
    img_bytes = _create_image_bytes(ext)

    with (
        patch(
            "src.vsl.service.extract_landmarks_from_image",
            return_value=([0.5] * 93, True, True),
        ),
        patch("src.vsl.service.preprocess_heatmap", side_effect=lambda batch: batch),
    ):
        response = client.post(
            "/predict",
            files={"file": (filename, io.BytesIO(img_bytes), content_type)},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.parametrize(
    ("filename", "content_type", "payload", "expected_reason"),
    [
        ("empty.jpg", "image/jpeg", b"", "empty_file"),
        ("empty.png", "image/png", b"", "empty_file"),
        ("short.jpg", "image/jpg", b"\xff\xd8", "corrupt_image_data"),
        ("short.png", "image/png", b"\x89PNG", "corrupt_image_data"),
        ("broken.jpg", "image/jpeg", b"\xff\xd8\xff\xe0corrupt-jpeg", "corrupt_image_data"),
        ("broken.png", "image/png", b"\x89PNG\r\n\x1a\ncorrupt-png", "corrupt_image_data"),
    ],
)
def test_br_010_corrupt_or_empty_declared_image_returns_400_and_logs(
    filename: str,
    content_type: str,
    payload: bytes,
    expected_reason: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Empty or corrupt payloads matching allowed image signatures return HTTP 400."""
    client, model = _client_with_mock_model()
    caplog.set_level(logging.WARNING, logger="vsl.service")

    response = client.post(
        "/predict",
        files={"file": (filename, io.BytesIO(payload), content_type)},
    )

    assert response.status_code == 400
    assert "detail" in response.json()
    model.assert_not_called()
    _assert_rejection_warning_log(
        caplog,
        expected_status=400,
        expected_reason=expected_reason,
    )


def test_br_010_oversized_upload_stops_reading_early_around_5mb() -> None:
    """Streaming upload reader must stop shortly after crossing 5 MB rather than buffering 20 MB."""
    from fastapi import UploadFile

    client, _ = _client_with_mock_model()
    oversized_jpeg = b"\xff\xd8\xff\xe0" + (b"\x00" * (20 * 1024 * 1024 - 4))
    original_read = UploadFile.read
    read_sizes: list[int] = []

    async def tracked_read(self: UploadFile, size: int = -1) -> bytes:
        chunk = await original_read(self, size)
        read_sizes.append(len(chunk))
        return chunk

    with patch.object(UploadFile, "read", new=tracked_read):
        response = client.post(
            "/predict",
            files={"file": ("anh_20mb.jpg", io.BytesIO(oversized_jpeg), "image/jpeg")},
        )

    assert response.status_code == 413
    assert sum(read_sizes) <= MAX_UPLOAD_BYTES + 128 * 1024
    assert len(read_sizes) > 1, "Expected chunked reading instead of a single unbounded read()"
