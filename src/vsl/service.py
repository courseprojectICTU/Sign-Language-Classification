"""Dịch vụ HTTP API cho Sign Language Classification (US-005, EPC-02).

Tuân thủ:
- BR-011: Single Model Load per Container (mô hình chỉ nạp 1 lần lúc startup qua Lifespan).
- BR-019: Warm-Up on Page Load (cung cấp endpoint /health nhận ping từ frontend).
"""

from contextlib import asynccontextmanager
import logging
from typing import Any, Dict, List, Optional, Tuple
import cv2
from fastapi import FastAPI, File, HTTPException, Query, Response, UploadFile, status
from keras.models import load_model
import numpy as np
from pydantic import BaseModel, Field

from src.vsl.config import get_model_path
from src.vsl.labels import NUM_CLASSES

logger = logging.getLogger("vsl.service")


# ---------------------------------------------------------------- Pydantic Schemas
class TopKPrediction(BaseModel):
    """Mỗi mục dự đoán trong danh sách gợi ý xác suất cao nhất."""
    letter: str
    confidence: float


class PredictResponse(BaseModel):
    """Hợp đồng JSON phản hồi từ endpoint POST /predict (US-006)."""
    detected: bool
    letter: Optional[str] = None
    confidence: float = 0.0
    top_k: List[TopKPrediction] = Field(default_factory=list)
    has_hand: bool = False
    has_face: bool = False
    message: Optional[str] = None
    model_version: Optional[str] = None


def extract_landmarks_from_image(image_bytes: bytes) -> Tuple[Optional[List[float]], bool, bool]:
    """Giải mã ảnh và trích xuất toạ độ landmark (khung TSK-009, hoàn thiện ở TSK-010)."""
    np_arr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Không thể giải mã tệp ảnh.")
    return None, False, False


def predict_from_landmarks(landmarks: List[float], model: Any, top_k: int = 3) -> Dict[str, Any]:
    """Suy luận nhãn ký hiệu từ vector landmark (khung TSK-009, hoàn thiện ở TSK-011)."""
    raise NotImplementedError("predict_from_landmarks sẽ được cài đặt ở TSK-011")


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

    @app.post(
        "/predict",
        summary="Dự đoán ký hiệu từ ảnh tải lên",
        tags=["Inference"],
        response_model=PredictResponse,
        status_code=status.HTTP_200_OK,
    )
    async def predict_endpoint(
        file: UploadFile = File(..., description="Tệp ảnh tải lên (JPEG, PNG...)"),
        top_k: int = Query(3, ge=1, le=NUM_CLASSES, description="Số lượng gợi ý xác suất cao nhất"),
    ) -> PredictResponse:
        """Endpoint nhận ảnh multipart và dự đoán ký hiệu ngôn ngữ ký hiệu tiếng Việt (US-006)."""
        # BR-011: Kiểm tra trạng thái nạp của model
        if getattr(app.state, "model", None) is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Mô hình nhận diện chưa sẵn sàng. Vui lòng kiểm tra lại sau.",
            )

        content = await file.read()
        try:
            landmarks, has_hand, has_face = extract_landmarks_from_image(content)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể giải mã dữ liệu ảnh tải lên. Vui lòng gửi tệp ảnh hợp lệ.",
            )

        if landmarks is None:
            return PredictResponse(
                detected=False,
                letter=None,
                confidence=0.0,
                top_k=[],
                has_hand=has_hand,
                has_face=has_face,
                message="Không nhận diện đủ 1 bàn tay và khuôn mặt trong ảnh.",
                model_version=getattr(app.state, "model_version", "v1.0") or "v1.0",
            )

        inference_result = predict_from_landmarks(landmarks, app.state.model, top_k=top_k)

        return PredictResponse(
            detected=True,
            letter=inference_result["letter"],
            confidence=inference_result["confidence"],
            top_k=[TopKPrediction(**item) for item in inference_result["top_k"]],
            has_hand=has_hand,
            has_face=has_face,
            model_version=getattr(app.state, "model_version", "v1.0") or "v1.0",
        )

    return app


# Instance ứng dụng mặc định cho ASGI runner (uvicorn src.vsl.service:app)
app = create_app()

