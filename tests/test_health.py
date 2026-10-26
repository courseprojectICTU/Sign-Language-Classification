"""Test cho US-005 — "API kiểm tra sức khỏe /health phản ánh trạng thái model".

Bám theo AC-005-01, AC-005-02 trong docs/api/US-005.md và BR-011, BR-019.
"""

from unittest.mock import MagicMock, patch
import pathlib
import pytest
from starlette.testclient import TestClient

ROOT = pathlib.Path(__file__).resolve().parents[1]
SERVICE_PATH = ROOT / "src" / "vsl" / "service.py"


# ---------------------------------------------------------------- AC-005-01
def test_ac_005_01_health_tra_200_khi_model_da_nap():
    """AC-005-01: GET /health trả 200 OK kèm model_loaded: true khi model đã sẵn sàng trong bộ nhớ."""
    assert SERVICE_PATH.exists(), f"Module service chưa tồn tại: {SERVICE_PATH}"

    from src.vsl.service import create_app

    # Tạo app và giả lập model đã nạp vào app.state
    app = create_app()
    app.state.model = MagicMock(name="loaded_keras_model")
    app.state.model_version = "v1.0"

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/health")

    assert response.status_code == 200, f"Kỳ vọng 200 OK, thực tế: {response.status_code}"
    data = response.json()
    assert data.get("status") == "ok", f"Trường status không đúng: {data}"
    assert data.get("model_loaded") is True, f"model_loaded phải là True: {data}"
    assert data.get("model_version") == "v1.0", f"model_version không đúng: {data}"


# ---------------------------------------------------------------- AC-005-02
def test_ac_005_02_health_tra_503_khi_model_chua_san_sang():
    """AC-005-02: GET /health trả 503 Service Unavailable với model_loaded: false khi model chưa nạp."""
    assert SERVICE_PATH.exists(), f"Module service chưa tồn tại: {SERVICE_PATH}"

    from src.vsl.service import create_app

    # Tạo app với app.state.model là None (chưa nạp hoặc nạp lỗi)
    app = create_app()
    app.state.model = None
    app.state.model_version = None

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/health")

    assert response.status_code == 503, (
        f"Kỳ vọng 503 Service Unavailable khi model chưa nạp, thực tế: {response.status_code}"
    )
    data = response.json()
    assert data.get("status") == "degraded", f"Trường status không đúng: {data}"
    assert data.get("model_loaded") is False, f"model_loaded phải là False: {data}"
    assert data.get("model_version") is None, f"model_version phải là None: {data}"


# ---------------------------------------------------------------- BR-011
def test_br_011_single_model_load_khong_nap_lai_khi_goi_request():
    """BR-011: Mô hình chỉ được nạp 1 lần duy nhất lúc khởi động, không nạp lại trong từng request."""
    assert SERVICE_PATH.exists(), f"Module service chưa tồn tại: {SERVICE_PATH}"

    from src.vsl.service import create_app

    with patch("keras.models.load_model") as mock_load_model:
        mock_model = MagicMock(name="mock_resnet50")
        mock_load_model.return_value = mock_model

        app = create_app()

        # Giả lập model đã nạp xong ở startup
        app.state.model = mock_model
        app.state.model_version = "v1.0"

        client = TestClient(app, raise_server_exceptions=False)

        # Gửi 5 request liên tiếp tới /health
        for _ in range(5):
            res = client.get("/health")
            assert res.status_code == 200

        # Khẳng định: Trong quá trình xử lý 5 request /health, không có lệnh load_model nào được gọi thêm
        assert mock_load_model.call_count == 0, (
            f"Vi phạm BR-011: load_model bị gọi bên trong request handler! Số lần: {mock_load_model.call_count}"
        )
