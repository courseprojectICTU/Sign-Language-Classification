"""Bộ kiểm thử hợp đồng dữ liệu 93 cột (BR-001, US-015).

Bao phủ:
- AC-015-01: Happy Path — Kiểm tra file CSV thật trong data/anphabet/, xác nhận
  đúng 93 cột, header đúng thứ tự hand trước face sau.
- AC-015-02: Negative Path — Khi face_keypoints hoặc thứ tự cột bị đảo lộn,
  kiểm thử thất bại và chỉ rõ cột vi phạm.
- TSK-024: Test hợp đồng 93 cột trên dữ liệu CSV thật.
- TSK-025: Test danh sách face_keypoints.
"""

from pathlib import Path
from typing import List, Tuple
import pytest
import pandas as pd

from src.vsl.config import get_data_dir
from src.vsl.labels import VIETNAMESE_ALPHABET
from src.vsl.landmarks import (
    FACE_KEYPOINTS,
    NUM_HAND_LANDMARKS,
    NUM_FACE_KEYPOINTS,
    HAND_COORDS_COUNT,
    FACE_COORDS_COUNT,
    TOTAL_LANDMARK_COORDS,
    LANDMARK_COLUMN_NAMES,
    build_expected_landmark_columns,
    validate_landmark_columns,
)


# -----------------------------------------------------------------------------
# AC-015-01: Happy Path — Kiểm tra cấu trúc header 93 cột trên dữ liệu thật
# -----------------------------------------------------------------------------
def test_ac_015_01_csv_header_has_exact_93_columns():
    """AC-015-01: File CSV dữ liệu thật bắt buộc có đúng 93 cột (BR-001)."""
    data_dir = get_data_dir()
    sample_csv = data_dir / "a" / "1.csv"
    assert sample_csv.is_file(), f"Không tìm thấy file mẫu: {sample_csv}"

    df = pd.read_csv(sample_csv)
    columns = list(df.columns)

    assert len(columns) == TOTAL_LANDMARK_COORDS == 93, (
        f"Số lượng cột thực tế ({len(columns)}) khác 93 quy định tại BR-001."
    )


def test_ac_015_01_csv_header_order_hand_first_face_second():
    """AC-015-01: Header phải theo thứ tự hand (63 cột) trước, face (30 cột) sau."""
    data_dir = get_data_dir()
    sample_csv = data_dir / "a" / "1.csv"
    df = pd.read_csv(sample_csv)
    columns = list(df.columns)

    hand_cols = columns[:HAND_COORDS_COUNT]
    face_cols = columns[HAND_COORDS_COUNT:]

    assert len(hand_cols) == 63 == HAND_COORDS_COUNT
    assert len(face_cols) == 30 == FACE_COORDS_COUNT

    # 1. 63 cột đầu bắt buộc là hand_{x,y,z}_{0..20}
    for i in range(NUM_HAND_LANDMARKS):
        expected_x = f"hand_x_{i}"
        expected_y = f"hand_y_{i}"
        expected_z = f"hand_z_{i}"
        actual_x = hand_cols[i * 3]
        actual_y = hand_cols[i * 3 + 1]
        actual_z = hand_cols[i * 3 + 2]
        assert actual_x == expected_x, f"Lệch toạ độ hand x tại điểm {i}: {actual_x} != {expected_x}"
        assert actual_y == expected_y, f"Lệch toạ độ hand y tại điểm {i}: {actual_y} != {expected_y}"
        assert actual_z == expected_z, f"Lệch toạ độ hand z tại điểm {i}: {actual_z} != {expected_z}"

    # 2. 30 cột sau bắt buộc là face_{x,y,z}_{idx} theo thứ tự FACE_KEYPOINTS
    for i, idx in enumerate(FACE_KEYPOINTS):
        expected_x = f"face_x_{idx}"
        expected_y = f"face_y_{idx}"
        expected_z = f"face_z_{idx}"
        actual_x = face_cols[i * 3]
        actual_y = face_cols[i * 3 + 1]
        actual_z = face_cols[i * 3 + 2]
        assert actual_x == expected_x, f"Lệch toạ độ face x tại điểm index {idx}: {actual_x} != {expected_x}"
        assert actual_y == expected_y, f"Lệch toạ độ face y tại điểm index {idx}: {actual_y} != {expected_y}"
        assert actual_z == expected_z, f"Lệch toạ độ face z tại điểm index {idx}: {actual_z} != {expected_z}"


def test_ac_015_01_dataset_samples_match_exact_contract():
    """AC-015-01: Mẫu đại diện từ tất cả 23 thư mục ký tự đều khớp 100% hợp đồng 93 cột."""
    data_dir = get_data_dir()
    expected_columns = LANDMARK_COLUMN_NAMES

    for letter in VIETNAMESE_ALPHABET:
        letter_dir = data_dir / letter
        assert letter_dir.is_dir(), f"Thư mục ký tự không tồn tại: {letter_dir}"

        csv_files = list(letter_dir.glob("*.csv"))
        assert len(csv_files) >= 50, f"Thư mục {letter} có ít hơn 50 file CSV ({len(csv_files)})"

        # Đọc file đầu tiên của mỗi ký tự để kiểm tra
        first_csv = csv_files[0]
        df = pd.read_csv(first_csv)
        columns = tuple(df.columns)

        is_valid, reason = validate_landmark_columns(columns)
        assert is_valid, (
            f"File {first_csv} vi phạm hợp đồng dữ liệu BR-001: {reason}"
        )
        assert columns == expected_columns, (
            f"Header file {first_csv} không khớp hoàn toàn với LANDMARK_COLUMN_NAMES."
        )


# -----------------------------------------------------------------------------
# AC-015-02 & TSK-025: Bắt sai lệch thứ tự và kiểm tra FACE_KEYPOINTS bất biến
# -----------------------------------------------------------------------------
def test_ac_015_02_face_keypoints_immutable_tuple():
    """TSK-025 & AC-015-02: FACE_KEYPOINTS phải là tuple bất biến đúng 10 số cố định."""
    assert isinstance(FACE_KEYPOINTS, tuple), "FACE_KEYPOINTS bắt buộc phải là kiểu tuple bất biến."
    assert len(FACE_KEYPOINTS) == NUM_FACE_KEYPOINTS == 10
    assert FACE_KEYPOINTS == (10, 152, 234, 454, 33, 263, 1, 61, 291, 199), (
        f"Thứ tự FACE_KEYPOINTS bị sai: {FACE_KEYPOINTS}"
    )


def test_ac_015_02_detects_swapped_face_indices_with_clear_error():
    """AC-015-02: Hoán đổi vị trí bất kỳ điểm mốc mặt nào phải bị phát hiện ngay và chỉ rõ tên cột."""
    # Giả lập danh sách cột bị tráo đổi điểm mặt 10 và 152
    corrupted_columns = list(LANDMARK_COLUMN_NAMES)
    idx_10_x = corrupted_columns.index("face_x_10")
    idx_152_x = corrupted_columns.index("face_x_152")

    # Tráo toạ độ x của điểm 10 và 152
    corrupted_columns[idx_10_x], corrupted_columns[idx_152_x] = (
        corrupted_columns[idx_152_x],
        corrupted_columns[idx_10_x],
    )

    is_valid, reason = validate_landmark_columns(corrupted_columns)
    assert not is_valid, "Hàm validate_landmark_columns phải trả về False khi toạ độ mặt bị tráo đổi."
    assert reason is not None
    assert "face_x_152" in reason or "face_x_10" in reason, (
        f"Thông báo lỗi phải chỉ rõ tên cột bị sai lệch: {reason}"
    )
    assert f"cột thứ {idx_10_x}" in reason or f"index {idx_10_x}" in reason or str(idx_10_x) in reason, (
        f"Thông báo lỗi phải chỉ ra vị trí cột bị sai: {reason}"
    )


def test_ac_015_02_detects_hand_face_swapped_or_wrong_column_count():
    """AC-015-02: Phát hiện khi tráo thứ tự tay/mặt hoặc khi số cột khác 93."""
    # 1. Tráo đưa 30 cột mặt lên trước 63 cột tay
    swapped_blocks = list(LANDMARK_COLUMN_NAMES[63:]) + list(LANDMARK_COLUMN_NAMES[:63])
    is_valid, reason = validate_landmark_columns(swapped_blocks)
    assert not is_valid
    assert reason is not None
    assert "0" in reason or "hand" in reason or "face" in reason

    # 2. Thiếu cột (chỉ có 63 cột tay)
    is_valid, reason = validate_landmark_columns(LANDMARK_COLUMN_NAMES[:63])
    assert not is_valid
    assert "63" in reason and "93" in reason

    # 3. Thừa cột (94 cột)
    extra_cols = list(LANDMARK_COLUMN_NAMES) + ["extra_col"]
    is_valid, reason = validate_landmark_columns(extra_cols)
    assert not is_valid
    assert "94" in reason and "93" in reason


def test_ac_015_02_service_extract_landmarks_parity_with_contract():
    """AC-015-02: Hàm extract_landmarks_from_image trong service phải dùng đúng FACE_KEYPOINTS từ module hợp đồng."""
    from src.vsl import service
    assert hasattr(service, "FACE_KEYPOINTS"), "service.py phải sử dụng hằng số FACE_KEYPOINTS."
    assert service.FACE_KEYPOINTS == FACE_KEYPOINTS, (
        "service.FACE_KEYPOINTS không trùng khớp với FACE_KEYPOINTS trong src.vsl.landmarks."
    )

