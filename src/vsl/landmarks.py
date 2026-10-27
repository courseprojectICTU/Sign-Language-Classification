"""Hợp đồng dữ liệu toạ độ landmark 93 cột (BR-001, US-015).

Nguồn chân lý duy nhất (Single Source of Truth) định nghĩa:
- FACE_KEYPOINTS: Thứ tự bất biến 10 điểm mốc khuôn mặt trích xuất từ MediaPipe FaceMesh.
- Cấu trúc vector 93 toạ độ: 63 toạ độ bàn tay trước, 30 toạ độ khuôn mặt sau.
- LANDMARK_COLUMN_NAMES: Tên 93 cột chuẩn trong dataset và pipeline suy luận.
"""

from typing import Optional, Sequence, Tuple

# -----------------------------------------------------------------------------
# Hằng số cấu hình hợp đồng landmark (BR-001)
# -----------------------------------------------------------------------------
# 10 điểm mốc MediaPipe FaceMesh cố định: trán, cằm, viền mặt, mắt, mũi, miệng
FACE_KEYPOINTS: Tuple[int, ...] = (10, 152, 234, 454, 33, 263, 1, 61, 291, 199)

NUM_HAND_LANDMARKS: int = 21
NUM_FACE_KEYPOINTS: int = len(FACE_KEYPOINTS)  # 10

HAND_COORDS_COUNT: int = NUM_HAND_LANDMARKS * 3  # 63
FACE_COORDS_COUNT: int = NUM_FACE_KEYPOINTS * 3  # 30
TOTAL_LANDMARK_COORDS: int = HAND_COORDS_COUNT + FACE_COORDS_COUNT  # 93


def build_expected_landmark_columns() -> Tuple[str, ...]:
    """Dựng tuple 93 tên cột theo đúng thứ tự quy định trong hợp đồng dữ liệu BR-001.

    Thứ tự:
    1. 63 toạ độ bàn tay: hand_{x,y,z}_{0..20}
    2. 30 toạ độ khuôn mặt: face_{x,y,z}_{idx} theo thứ tự FACE_KEYPOINTS
    """
    cols = []
    # 63 cột hand
    for i in range(NUM_HAND_LANDMARKS):
        cols.append(f"hand_x_{i}")
        cols.append(f"hand_y_{i}")
        cols.append(f"hand_z_{i}")

    # 30 cột face
    for idx in FACE_KEYPOINTS:
        cols.append(f"face_x_{idx}")
        cols.append(f"face_y_{idx}")
        cols.append(f"face_z_{idx}")

    return tuple(cols)


LANDMARK_COLUMN_NAMES: Tuple[str, ...] = build_expected_landmark_columns()


def validate_landmark_columns(columns: Sequence[str]) -> Tuple[bool, Optional[str]]:
    """Kiểm tra danh sách tên cột có tuân thủ đúng hợp đồng 93 cột BR-001 hay không.

    Tham số:
    - columns: Danh sách hoặc tuple tên các cột cần kiểm tra.

    Trả về:
    - (True, None) nếu hợp đồng được thoả mãn hoàn toàn.
    - (False, reason) nếu có bất kỳ vi phạm nào về số lượng hoặc thứ tự cột.
    """
    actual_count = len(columns)
    if actual_count != TOTAL_LANDMARK_COORDS:
        return (
            False,
            f"Số lượng cột thực tế ({actual_count}) khác {TOTAL_LANDMARK_COORDS} quy định tại BR-001.",
        )

    for i, (actual, expected) in enumerate(zip(columns, LANDMARK_COLUMN_NAMES)):
        if actual != expected:
            return (
                False,
                f"Lệch tên cột tại index {i} (cột thứ {i}): thực tế '{actual}', kỳ vọng '{expected}'.",
            )

    return True, None

