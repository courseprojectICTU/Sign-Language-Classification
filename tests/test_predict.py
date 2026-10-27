"""Test suite cho US-006 — "API /predict nhận ảnh và chạy pipeline MediaPipe Python server-side".

Bám theo:
- docs/api/US-006.md (hợp đồng API đã được duyệt tại CỔNG B)
- AC-006-01 (Happy path ảnh hợp lệ, schema đầy đủ, top_k, detected=False khi không thấy tay/mặt)
- AC-006-02 (Kiểm tra độ hợp lệ pipeline service trên 23/23 mẫu chuẩn)
- BR-001 (Landmark 93 cột), BR-006 (Caffe preprocessing), BR-007 (Mirror parity), BR-011 (Single model load)
"""

from unittest.mock import MagicMock, patch
import io
import pathlib
import cv2
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

ROOT = pathlib.Path(__file__).resolve().parents[1]
SERVICE_PATH = ROOT / "src" / "vsl" / "service.py"

from src.vsl.labels import VIETNAMESE_ALPHABET, NUM_CLASSES
from src.vsl.config import get_model_path


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
    with patch("src.vsl.service.extract_landmarks_from_image", return_value=(dummy_landmarks, True, True)):
        img_bytes = _create_dummy_image_bytes(200, 200)
        response = client.post(
            "/predict",
            files={"file": ("test.jpg", io.BytesIO(img_bytes), "image/jpeg")},
        )

    assert response.status_code == 200, f"Kỳ vọng 200 OK, thực tế: {response.status_code} - {response.text}"
    data = response.json()

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

    with patch("src.vsl.service.extract_landmarks_from_image", return_value=(dummy_landmarks, True, True)):
        img_bytes = _create_dummy_image_bytes(200, 200)
        response = client.post(
            "/predict?top_k=5",
            files={"file": ("test.jpg", io.BytesIO(img_bytes), "image/jpeg")},
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data.get("top_k", [])) == 5


# ---------------------------------------------------------------- Edge Cases & Validation
def test_ac_006_01_predict_khong_thay_tay_hoac_mat_tra_200_detected_false():
    """Khi ảnh không có bàn tay hoặc khuôn mặt, trả HTTP 200 với detected=False mà không ném lỗi 5xx."""
    from src.vsl.service import create_app

    app = create_app()
    app.state.model = MagicMock()

    client = TestClient(app, raise_server_exceptions=False)

    # Ảnh đen hoàn toàn, MediaPipe tự nhiên không tìm thấy tay/mặt
    black_img = _create_dummy_image_bytes(100, 100, color=0)
    response = client.post(
        "/predict",
        files={"file": ("blank.jpg", io.BytesIO(black_img), "image/jpeg")},
    )

    assert response.status_code == 200, f"Kỳ vọng 200, nhận: {response.status_code} - {response.text}"
    data = response.json()
    assert data.get("detected") is False, f"detected phải là False: {data}"
    assert data.get("letter") is None, f"letter phải là None: {data}"
    assert data.get("confidence") == 0.0
    assert data.get("has_hand") is False
    assert data.get("top_k") == []
    assert "message" in data


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
    from src.vsl.service import extract_landmarks_from_image, _mp_hands, _mp_face_mesh

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

    with patch.object(_mp_hands, "process", return_value=mock_hands_res), \
         patch.object(_mp_face_mesh, "process", return_value=mock_face_res):
        landmarks, has_hand, has_face = extract_landmarks_from_image(img_bytes)

    assert has_hand is True
    assert has_face is True
    assert landmarks is not None
    assert len(landmarks) == 93, f"Kỳ vọng đúng 93 toạ độ (BR-001), thực tế: {len(landmarks)}"


def test_flip_parameter_tuy_chinh_lat_guong():
    """Kiểm tra tham số flip=True gọi cv2.flip và flip=False không gọi cv2.flip."""
    from src.vsl.service import extract_landmarks_from_image

    img_bytes = _create_dummy_image_bytes(100, 100)

    with patch("cv2.flip", wraps=cv2.flip) as mock_flip:
        extract_landmarks_from_image(img_bytes, flip=False)
        assert mock_flip.call_count == 0, "flip=False không được gọi cv2.flip"

    with patch("cv2.flip", wraps=cv2.flip) as mock_flip:
        extract_landmarks_from_image(img_bytes, flip=True)
        assert mock_flip.call_count == 1, "flip=True phải gọi cv2.flip 1 lần"




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
