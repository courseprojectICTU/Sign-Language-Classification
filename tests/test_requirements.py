"""Test cho US-004 — "Chuẩn hóa requirements.txt cho môi trường Linux container".

Bám theo AC-004-01 trong docs/api/US-004.md và BR-005.
File này được viết TRƯỚC khi sửa requirements.txt (TDD) — lúc đầu phải ĐỎ (FAIL).
"""

import pathlib
import re
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
REQUIREMENTS_PATH = ROOT / "requirements.txt"


def _read_requirements_lines():
    assert REQUIREMENTS_PATH.exists(), f"Không tìm thấy {REQUIREMENTS_PATH}"
    lines = REQUIREMENTS_PATH.read_text(encoding="ascii", errors="strict").splitlines()
    # Loại bỏ comment và dòng trống
    clean_lines = [
        line.strip() for line in lines
        if line.strip() and not line.strip().startswith("#")
    ]
    return clean_lines


# ---------------------------------------------------------------- AC-004-01
def test_ac_004_01_requirements_la_thuan_ascii():
    """BR-005: requirements.txt bắt buộc phải 100% thuần ASCII (không chứa UTF-8 có dấu)."""
    assert REQUIREMENTS_PATH.exists(), f"Không tìm thấy {REQUIREMENTS_PATH}"
    raw_bytes = REQUIREMENTS_PATH.read_bytes()

    non_ascii_bytes = [(idx, b) for idx, b in enumerate(raw_bytes) if b >= 128]
    assert not non_ascii_bytes, (
        f"requirements.txt chứa {len(non_ascii_bytes)} byte không phải ASCII! "
        f"Ví dụ: byte tại vị trí {non_ascii_bytes[:5]}"
    )


def test_ac_004_01_requirements_dung_opencv_headless_khong_dung_gui():
    """AC-004-01: requirements.txt phải dùng opencv-python-headless và loại bỏ các gói GUI desktop."""
    clean_lines = _read_requirements_lines()

    # Phải có opencv-python-headless
    has_headless = any(line.startswith("opencv-python-headless==") for line in clean_lines)
    assert has_headless, "requirements.txt thiếu gói 'opencv-python-headless=='"

    # Không được có opencv-python bản desktop
    has_desktop_gui = any(
        re.match(r"^opencv-python\s*==", line)
        for line in clean_lines
    )
    assert not has_desktop_gui, (
        "requirements.txt vẫn còn chứa 'opencv-python' (bản GUI desktop vi phạm container slim)"
    )

    # Không được có opencv-contrib-python
    has_contrib_gui = any(line.startswith("opencv-contrib-python") for line in clean_lines)
    assert not has_contrib_gui, (
        "requirements.txt vẫn còn chứa 'opencv-contrib-python' (không cần thiết và chứa thư viện GUI)"
    )


def test_br_005_verified_dependency_pins():
    """BR-005: Phiên bản phụ thuộc phải giữ đúng tổ hợp đã kiểm chứng."""
    clean_lines = _read_requirements_lines()
    req_dict = {}
    for line in clean_lines:
        if "==" in line:
            pkg, ver = line.split("==", 1)
            req_dict[pkg.strip()] = ver.strip()

    # 1. mediapipe phải thuộc nhánh 0.10.x (từ 1.0.0 đã xóa mp.solutions)
    assert "mediapipe" in req_dict, "Thiếu mediapipe trong requirements.txt"
    assert req_dict["mediapipe"].startswith("0.10."), (
        f"mediapipe phải là 0.10.x theo BR-005, thực tế: {req_dict['mediapipe']}"
    )

    # 2. numpy phải nhỏ hơn 2 (mediapipe 0.10.x yêu cầu numpy<2)
    assert "numpy" in req_dict, "Thiếu numpy trong requirements.txt"
    np_ver = req_dict["numpy"]
    assert np_ver.startswith("1."), f"numpy phải là 1.x.x (< 2.0) theo BR-005, thực tế: {np_ver}"

    # 3. tensorflow và keras phải tương thích Python 3.12
    assert "tensorflow" in req_dict, "Thiếu tensorflow trong requirements.txt"
    assert req_dict["tensorflow"] == "2.19.1", f"tensorflow phải ghim 2.19.1, thực tế: {req_dict['tensorflow']}"

    assert "keras" in req_dict, "Thiếu keras trong requirements.txt"
    assert req_dict["keras"] == "3.15.1", f"keras phải ghim 3.15.1, thực tế: {req_dict['keras']}"
