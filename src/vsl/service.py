"""Dịch vụ HTTP API cho Sign Language Classification (US-005, EPC-02).

Tuân thủ:
- BR-011: Single Model Load per Container (mô hình chỉ nạp 1 lần lúc startup qua Lifespan).
- BR-019: Warm-Up on Page Load (cung cấp endpoint /health nhận ping từ frontend).
"""

from contextlib import asynccontextmanager
import logging
from typing import Any, Dict
from fastapi import FastAPI, Response, status
from keras.models import load_model

from src.vsl.config import get_model_path

logger = logging.getLogger("vsl.service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Quản lý vòng đời ứng dụng — nạp mô hình một lần duy nhất lúc khởi động (BR-011)."""
    model_path = get_model_path()
    try:
        logger.info("Đang nạp mô hình từ: %s", model_path)
        app.state.model = load_model(str(model_path))
        app.state.model_version = "v1.0"
        logger.info("Nạp mô hình thành công vào app.state.")
    except Exception as exc:
        logger.error("Lỗi khi nạp mô hình lúc khởi động: %s", exc)
        app.state.model = None
        app.state.model_version = None

    yield

    # Giải phóng tài nguyên lúc tắt container
    app.state.model = None


def create_app() -> FastAPI:
    """Factory khởi tạo ứng dụng FastAPI và cấu hình các route."""
    app = FastAPI(
        title="Sign Language Classification API",
        version="1.0.0",
        description="Dịch vụ nhận diện ngôn ngữ ký hiệu tiếng Việt từ webcam",
        lifespan=lifespan,
    )

    # Khởi tạo trạng thái mặc định
    app.state.model = None
    app.state.model_version = None

    @app.get(
        "/health",
        summary="Kiểm tra sức khỏe dịch vụ và trạng thái nạp mô hình",
        tags=["Monitoring"],
        status_code=status.HTTP_200_OK,
    )
    async def health_check(response: Response) -> Dict[str, Any]:
        """Endpoint kiểm tra sức khỏe phản ánh trung thực trạng thái nạp mô hình (BR-011).

        - 200 OK: Mô hình đã nạp xong và sẵn sàng nhận dự đoán.
        - 503 Service Unavailable: Mô hình chưa nạp hoặc nạp thất bại.
        """
        is_model_loaded = (
            hasattr(app.state, "model") and app.state.model is not None
        )

        if is_model_loaded:
            return {
                "status": "ok",
                "model_loaded": True,
                "model_version": getattr(app.state, "model_version", "v1.0") or "v1.0",
            }

        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "degraded",
            "model_loaded": False,
            "model_version": None,
        }

    return app


# Instance ứng dụng mặc định cho ASGI runner (uvicorn src.vsl.service:app)
app = create_app()
