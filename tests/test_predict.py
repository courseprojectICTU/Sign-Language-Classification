"""Test suite cho US-006 — "API /predict nhận ảnh và chạy pipeline MediaPipe Python server-side".

Bám theo:
- docs/api/US-006.md (hợp đồng API đã được duyệt tại CỔNG B)
- AC-006-01 (Happy path ảnh hợp lệ, schema đầy đủ, top_k, detected=False khi không thấy tay/mặt)
- AC-006-02 (Kiểm tra độ hợp lệ pipeline service trên 23/23 mẫu chuẩn)
- BR-001 (Landmark 93 cột), BR-006 (Caffe preprocessing), BR-007 (Mirror parity), BR-011 (Single model load)
"""

import io
import logging
import pathlib
import re
from datetime import datetime
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

ROOT = pathlib.Path(__file__).resolve().parents[1]
SERVICE_PATH = ROOT / "src" / "vsl" / "service.py"

from src.vsl.config import get_model_path
from src.vsl.labels import NUM_CLASSES, VIETNAMESE_ALPHABET


def _create_dummy_image_bytes(width: int = 100, height: int = 100, color: int = 0) -> bytes:
    """Tạo byte buffer của ảnh JPEG nhân tạo."""
    img = np.full((height, width, 3), color, dtype=np.uint8)
    success, encoded = cv2.imencode(".jpg", img)
    assert success, "Không thể mã hóa ảnh JPEG dummy"
    return encoded.tobytes()


# ---------------------------------------------------------------- AC-006-01: Happy Path & Schema
def test_ac_006_01_predict_anh_hop_le_tra_200_va_dung_schema():
    """AC-006-01: POST /predict nhận ảnh multipart hợp lệ, trả HTTP 200 kèm letter, confidence, top_k."""
    assert SERVICE_PATH.exists(), f"Module service chưa tồn tại: {SERVICE_PATH}"

    from src.vsl.service import create_app

    app = create_app()

    # Giả lập model đã nạp với kết quả dự đoán lớp 'a' (index 0)
    fake_probs = np.zeros((1, NUM_CLASSES), dtype=np.float32)
    fake_probs[0, 0] = 0.95  # 'a'
    fake_probs[0, 1] = 0.03  # 'b'
    fake_probs[0, 2] = 0.02  # 'c'

    mock_model = MagicMock()
    mock_model.return_value.numpy.return_value = fake_probs
    app.state.model = mock_model
    app.state.model_version = "v1.0"

    client = TestClient(app, raise_server_exceptions=False)

    # Giả lập pipeline trích xuất landmark trả về 93 toạ độ hợp lệ
    dummy_landmarks = [0.5] * 93
    with patch("src.vsl.service.extract_landmarks_from_image", return_value=(dummy_landmarks, True, True)), \
         patch("src.vsl.service.preprocess_heatmap", side_effect=lambda batch: batch):
        img_bytes = _create_dummy_image_bytes(200, 200)
        response = client.post(
            "/predict",
            files={"file": ("test.jpg", io.BytesIO(img_bytes), "image/jpeg")},
        )

    assert response.status_code == 200, f"Kỳ vọng 200 OK, thực tế: {response.status_code} - {response.text}"
    data = response.json()

    assert data.get("status") == "ok"
    assert data.get("detected") is True, f"Kỳ vọng detected=True: {data}"
    assert data.get("letter") == "a", f"Kỳ vọng letter='a': {data}"
    assert pytest.approx(data.get("confidence"), 0.001) == 0.95
    assert data.get("has_hand") is True
    assert data.get("has_face") is True
    assert data.get("model_version") == "v1.0"

    # Kiểm tra top_k mặc định là 3
    top_k = data.get("top_k", [])
    assert len(top_k) == 3, f"Kỳ vọng top_k có 3 phần tử, thực tế: {top_k}"
    assert top_k[0]["letter"] == "a"
    assert pytest.approx(top_k[0]["confidence"], 0.001) == 0.95
    assert top_k[1]["letter"] == "b"


def test_ac_006_01_predict_top_k_parameter_tuy_chinh():
    """AC-006-01: Query param top_k cho phép client nhận số lượng gợi ý mong muốn."""
    from src.vsl.service import create_app

    app = create_app()
    fake_probs = np.zeros((1, NUM_CLASSES), dtype=np.float32)
    for i in range(5):
        fake_probs[0, i] = 0.2

    mock_model = MagicMock()
    mock_model.return_value.numpy.return_value = fake_probs
    app.state.model = mock_model

    client = TestClient(app, raise_server_exceptions=False)
    dummy_landmarks = [0.5] * 93

    with patch("src.vsl.service.extract_landmarks_from_image", return_value=(dummy_landmarks, True, True)), \
         patch("src.vsl.service.preprocess_heatmap", side_effect=lambda batch: batch):
        img_bytes = _create_dummy_image_bytes(200, 200)
        response = client.post(
            "/predict?top_k=5",
            files={"file": ("test.jpg", io.BytesIO(img_bytes), "image/jpeg")},
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data.get("top_k", [])) == 5


# ---------------------------------------------------------------- Edge Cases & Validation
@pytest.mark.parametrize(
    (
        "has_hand",
        "has_face",
        "expected_status",
        "expected_message",
        "expected_reason",
    ),
    [
        (False, True, "no_hand", "bàn tay", "missing_hand"),
        (True, False, "no_face", "khuôn mặt", "missing_face"),
        (False, False, "no_hand", "bàn tay", "missing_hand_and_face"),
    ],
)
def test_predict_tra_trang_thai_cu_the_khi_thieu_landmark(
    has_hand: bool,
    has_face: bool,
    expected_status: str,
    expected_message: str,
    expected_reason: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Thiếu detection trả trạng thái riêng, không suy luận với vector thiếu."""
    from src.vsl.service import create_app

    app = create_app()
    app.state.model = MagicMock()
    caplog.set_level(logging.WARNING, logger="vsl.service")

    client = TestClient(app, raise_server_exceptions=False)
    image = _create_dummy_image_bytes(100, 100, color=0)
    with patch(
        "src.vsl.service.extract_landmarks_from_image",
        return_value=(None, has_hand, has_face),
    ):
        response = client.post(
            "/predict",
            files={"file": ("blank.jpg", io.BytesIO(image), "image/jpeg")},
        )

    assert response.status_code == 200, f"Kỳ vọng 200, nhận: {response.status_code} - {response.text}"
    data = response.json()
    assert data.get("status") == expected_status
    assert data.get("detected") is False, f"detected phải là False: {data}"
    assert data.get("letter") is None, f"letter phải là None: {data}"
    assert data.get("confidence") == 0.0
    assert data.get("has_hand") is has_hand
    assert data.get("has_face") is has_face
    assert data.get("top_k") == []
    assert expected_message in data.get("message", "")
    app.state.model.assert_not_called()

    warning_logs = [
        record.getMessage()
        for record in caplog.records
        if record.name == "vsl.service" and record.levelno == logging.WARNING
    ]
    assert len(warning_logs) == 1
    log_message = warning_logs[0]
    assert f"status={expected_status}" in log_message
    assert f"reason={expected_reason}" in log_message
    timestamp = re.search(r"timestamp=(\S+)", log_message)
    assert timestamp is not None, f"Log thiếu timestamp: {log_message}"
    parsed_timestamp = datetime.fromisoformat(
        timestamp.group(1).replace("Z", "+00:00")
    )
    assert parsed_timestamp.utcoffset() is not None, "Timestamp phải có timezone UTC"
    assert f"has_hand={has_hand}" in log_message
    assert f"has_face={has_face}" in log_message


def test_predict_file_khong_phai_anh_tra_400():
    """POST /predict nhận file byte rác không giải mã được ảnh trả 400 Bad Request."""
    from src.vsl.service import create_app

    app = create_app()
    app.state.model = MagicMock()

    client = TestClient(app, raise_server_exceptions=False)
    corrupt_bytes = b"This is not a valid JPEG/PNG image data"

    response = client.post(
        "/predict",
        files={"file": ("corrupt.bin", io.BytesIO(corrupt_bytes), "application/octet-stream")},
    )

    assert response.status_code == 400, f"Kỳ vọng 400 Bad Request, nhận: {response.status_code}"
    data = response.json()
    assert "detail" in data


def test_predict_model_chua_san_sang_tra_503():
    """POST /predict khi app.state.model là None trả 503 Service Unavailable (BR-011)."""
    from src.vsl.service import create_app

    app = create_app()
    app.state.model = None

    client = TestClient(app, raise_server_exceptions=False)
    img_bytes = _create_dummy_image_bytes(100, 100)

    response = client.post(
        "/predict",
        files={"file": ("test.jpg", io.BytesIO(img_bytes), "image/jpeg")},
    )

    assert response.status_code == 503, f"Kỳ vọng 503 khi model chưa nạp, nhận: {response.status_code}"
    assert "detail" in response.json()


def test_br_001_extract_landmarks_dung_93_cot_khi_nhan_dien():
    """BR-001: Hàm extract_landmarks_from_image phải trả đúng 93 toạ độ: 63 tay + 30 mặt."""
    from src.vsl.service import extract_landmarks_from_image

    img_bytes = _create_dummy_image_bytes(200, 200)

    # Mock hands_results có 21 landmarks
    fake_hand = MagicMock()
    fake_hand.landmark = [MagicMock(x=0.1 * i, y=0.2 * i, z=0.0) for i in range(21)]
    mock_hands_res = MagicMock()
    mock_hands_res.multi_hand_landmarks = [fake_hand]

    # Mock face_results có >= 454 landmarks
    fake_face = MagicMock()
    fake_face.landmark = {idx: MagicMock(x=0.5, y=0.5, z=0.1) for idx in range(468)}
    mock_face_res = MagicMock()
    mock_face_res.multi_face_landmarks = [fake_face]
    hands_processor = MagicMock()
    hands_processor.process.return_value = mock_hands_res
    face_mesh_processor = MagicMock()
    face_mesh_processor.process.return_value = mock_face_res

    with patch(
        "src.vsl.service._get_mediapipe_processors",
        return_value=(hands_processor, face_mesh_processor),
    ):
        landmarks, has_hand, has_face = extract_landmarks_from_image(img_bytes)

    assert has_hand is True
    assert has_face is True
    assert landmarks is not None
    assert len(landmarks) == 93, f"Kỳ vọng đúng 93 toạ độ (BR-001), thực tế: {len(landmarks)}"


def test_flip_parameter_tuy_chinh_lat_guong():
    """Kiểm tra tham số flip=True gọi cv2.flip và flip=False không gọi cv2.flip."""
    from src.vsl.service import extract_landmarks_from_image

    img_bytes = _create_dummy_image_bytes(100, 100)
    hands_processor = MagicMock()
    hands_processor.process.return_value = MagicMock(multi_hand_landmarks=None)
    face_mesh_processor = MagicMock()
    face_mesh_processor.process.return_value = MagicMock(multi_face_landmarks=None)

    with patch(
        "src.vsl.service._get_mediapipe_processors",
        return_value=(hands_processor, face_mesh_processor),
    ), patch("src.vsl.service.cv2.flip", wraps=cv2.flip) as mock_flip:
        extract_landmarks_from_image(img_bytes, flip=False)
        assert mock_flip.call_count == 0, "flip=False không được gọi cv2.flip"

    with patch(
        "src.vsl.service._get_mediapipe_processors",
        return_value=(hands_processor, face_mesh_processor),
    ), patch("src.vsl.service.cv2.flip", wraps=cv2.flip) as mock_flip:
        extract_landmarks_from_image(img_bytes, flip=True)
        assert mock_flip.call_count == 1, "flip=True phải gọi cv2.flip 1 lần"


def test_predict_endpoint_flip_parameter_truyen_dung():
    """Kiểm tra endpoint /predict nhận query flip và chuyển tiếp vào extract_landmarks_from_image."""
    from src.vsl.service import create_app

    app = create_app()
    app.state.model = MagicMock()
    client = TestClient(app, raise_server_exceptions=False)
    dummy_img = _create_dummy_image_bytes(100, 100)

    with patch("src.vsl.service.extract_landmarks_from_image", return_value=(None, False, False)) as mock_extract:
        client.post("/predict?flip=true", files={"file": ("test.jpg", io.BytesIO(dummy_img), "image/jpeg")})
        assert mock_extract.call_args.kwargs.get("flip") is True

    with patch("src.vsl.service.extract_landmarks_from_image", return_value=(None, False, False)) as mock_extract:
        client.post("/predict?flip=false", files={"file": ("test.jpg", io.BytesIO(dummy_img), "image/jpeg")})
        assert mock_extract.call_args.kwargs.get("flip") is False

    with patch("src.vsl.service.extract_landmarks_from_image", return_value=(None, False, False)) as mock_extract:
        client.post("/predict", files={"file": ("test.jpg", io.BytesIO(dummy_img), "image/jpeg")})
        assert mock_extract.call_args.kwargs.get("flip") is False





@pytest.mark.parametrize(
    ("has_hand", "has_face"),
    [(False, True), (True, False), (False, False)],
)
def test_extract_landmarks_early_return_khi_thieu_detection(
    has_hand: bool, has_face: bool
) -> None:
    """Chỉ dựng vector landmark khi cả hai detector đều tìm thấy dữ liệu."""
    from src.vsl.service import extract_landmarks_from_image

    image = _create_dummy_image_bytes(100, 100)
    hands_processor = MagicMock()
    hands_processor.process.return_value.multi_hand_landmarks = (
        [MagicMock()] if has_hand else None
    )
    face_mesh_processor = MagicMock()
    face_mesh_processor.process.return_value.multi_face_landmarks = (
        [MagicMock()] if has_face else None
    )

    with patch(
        "src.vsl.service._get_mediapipe_processors",
        return_value=(hands_processor, face_mesh_processor),
    ):
        landmarks, found_hand, found_face = extract_landmarks_from_image(image)

    assert landmarks is None
    assert found_hand is has_hand
    assert found_face is has_face
    hands_processor.process.assert_called_once()
    face_mesh_processor.process.assert_called_once()


# ---------------------------------------------------------------- AC-006-02: Pipeline Parity 23/23
def test_ac_006_02_pipeline_parity_23_23_ky_tu():
    """AC-006-02: Kiểm tra độ hợp lệ của pipeline service trên toàn bộ 23 mẫu 1.csv khớp 23/23 nhãn."""
    from keras.models import load_model

    from src.vsl.service import predict_from_landmarks

    model_path = get_model_path()
    assert model_path.exists(), f"Không tìm thấy model: {model_path}"
    model = load_model(str(model_path))

    wrong = []
    for letter in VIETNAMESE_ALPHABET:
        csv_file = ROOT / "data" / "anphabet" / letter / "1.csv"
        assert csv_file.exists(), f"Không tìm thấy file mẫu: {csv_file}"
        vector = pd.read_csv(csv_file).values.flatten().astype(np.float64).tolist()

        result = predict_from_landmarks(vector, model, top_k=3)
        predicted_letter = result["letter"]
        if predicted_letter != letter:
            wrong.append((letter, predicted_letter, result["confidence"]))

    assert not wrong, f"Pipeline dự đoán lệch {len(wrong)}/23 ký tự: {wrong}"
