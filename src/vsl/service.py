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
from keras.applications.resnet50 import preprocess_input
import numpy as np
from pydantic import BaseModel, Field

from src.vsl.config import get_model_path
from src.vsl.heatmap import create_heatmap
from src.vsl.labels import NUM_CLASSES, VIETNAMESE_ALPHABET
from src.vsl.landmarks import FACE_KEYPOINTS, TOTAL_LANDMARK_COORDS

import mediapipe as mp

logger = logging.getLogger("vsl.service")

# ---------------------------------------------------------------- MediaPipe Singletons
# Tái sử dụng instance để tránh re-init tốn tài nguyên (R-4)
if hasattr(mp, 'solutions'):
    _mp_hands = mp.solutions.hands.Hands(
        static_image_mode=True,
        max_num_hands=1,
        min_detection_confidence=0.5,
    )
    _mp_face_mesh = mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        min_detection_confidence=0.5,
    )
else:
    _mp_hands = None
    _mp_face_mesh = None
# FACE_KEYPOINTS được định nghĩa duy nhất tại src.vsl.landmarks (BR-001, US-015)


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


def extract_landmarks_from_image(
    image_bytes: bytes,
    flip: bool = False,
) -> Tuple[Optional[List[float]], bool, bool]:
    """Giải mã ảnh, tuỳ chọn lật gương (BR-007) và trích xuất 93 toạ độ landmark qua MediaPipe (BR-001).

    Tham số:
    - image_bytes: Dữ liệu byte nhị phân của tệp ảnh.
    - flip: Nếu True, lật gương ảnh ngang (cv2.flip) cho ảnh chụp webcam/selfie;
            nếu False, giữ nguyên chiều cho ảnh chụp từ camera điện thoại/máy ảnh thông thường.

    Trả về:
    - (all_landmarks_93, has_hand, has_face) nếu nhận diện đủ 1 tay và mặt.
    - (None, has_hand, has_face) nếu thiếu tay hoặc thiếu mặt.
    - Ném ValueError nếu dữ liệu byte không thể giải mã thành ảnh.
    """
    np_arr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Không thể giải mã tệp ảnh.")

    # Lật gương ảnh nếu client yêu cầu (BR-007)
    if flip:
        image = cv2.flip(image, 1)

    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # 1. Trích xuất landmark bàn tay (21 điểm x 3 = 63 toạ độ)
    hands_results = _mp_hands.process(image_rgb)
    has_hand = bool(hands_results.multi_hand_landmarks)
    hand_landmarks: List[float] = []
    if has_hand and hands_results.multi_hand_landmarks:
        first_hand = hands_results.multi_hand_landmarks[0]
        for lm in first_hand.landmark:
            hand_landmarks.extend([float(lm.x), float(lm.y), float(lm.z)])

    # 2. Trích xuất landmark khuôn mặt (10 điểm cố định x 3 = 30 toạ độ)
    face_results = _mp_face_mesh.process(image_rgb)
    has_face = bool(face_results.multi_face_landmarks)
    face_landmarks: List[float] = []
    if has_face and face_results.multi_face_landmarks:
        first_face = face_results.multi_face_landmarks[0]
        for idx in FACE_KEYPOINTS:
            lm = first_face.landmark[idx]
            face_landmarks.extend([float(lm.x), float(lm.y), float(lm.z)])

    # 3. Hợp đồng landmark: đúng 93 toạ độ (BR-001)
    all_landmarks = hand_landmarks + face_landmarks
    if len(all_landmarks) == 93:
        return all_landmarks, has_hand, has_face

    return None, has_hand, has_face



def predict_from_landmarks(landmarks: List[float], model: Any, top_k: int = 3) -> Dict[str, Any]:
    """Suy luận nhãn ký hiệu từ vector landmark theo chuẩn Caffe và ResNet50 (BR-002, BR-003, BR-006).

    Tuân thủ:
    - BR-001: landmarks đúng 93 toạ độ.
    - BR-002: create_heatmap bản duy nhất.
    - BR-006: preprocess_input Caffe style (trừ mean BGR), nghiêm cấm chia 255.
    - BR-003: ánh xạ nhãn qua VIETNAMESE_ALPHABET.
    """
    if len(landmarks) != 93:
        raise ValueError(f"Landmarks phải có đúng 93 toạ độ (BR-001), thực tế: {len(landmarks)}")

    # 1. Sinh heatmap 224x224x3 (BR-002)
    heatmap = create_heatmap(landmarks)

    # 2. Mở rộng chiều batch: (1, 224, 224, 3)
    heatmap_batch = np.expand_dims(heatmap, axis=0)

    # 3. Tiền xử lý ResNet50 kiểu Caffe (BR-006: trừ mean BGR, KHÔNG chia 255)
    heatmap_batch = preprocess_input(heatmap_batch)

    # 4. Suy luận qua mô hình
    predictions = model(heatmap_batch, training=False)
    if hasattr(predictions, "numpy"):
        probs = predictions.numpy()[0]
    else:
        probs = np.array(predictions)[0]

    predicted_class = int(np.argmax(probs))
    predicted_letter = VIETNAMESE_ALPHABET[predicted_class]
    confidence = float(probs[predicted_class])

    # 5. Trích xuất top_k theo xác suất giảm dần
    top_indices = np.argsort(probs)[::-1][:top_k]
    top_k_list = [
        {"letter": VIETNAMESE_ALPHABET[int(i)], "confidence": float(probs[i])}
        for i in top_indices
    ]

    return {
        "letter": predicted_letter,
        "confidence": confidence,
        "top_k": top_k_list,
    }


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
        flip: bool = Query(False, description="Lật gương ảnh ngang (True nếu là ảnh webcam/selfie gương, False nếu là ảnh chụp trực tiếp)"),
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
            landmarks, has_hand, has_face = extract_landmarks_from_image(content, flip=flip)
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

