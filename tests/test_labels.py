"""Test cho US-002 — "Trich xuat VIETNAMESE_ALPHABET thanh nguon chan ly duy nhat".

Bam theo AC-002-01 va AC-002-02 trong docs/api/US-002.md va BR-003.
File nay duoc viet TRUOC khi tao src/vsl/labels.py (TDD) — luc dau phai DO (FAIL).
"""

import json
import pathlib
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "vsl" / "labels.py"

EXPECTED_ALPHABET = (
    "a", "b", "c", "d", "đ", "e", "g", "h", "i", "k", "l", "m", "n",
    "o", "p", "q", "r", "s", "t", "u", "v", "x", "y"
)

SKIP_DIRS = {
    ".git", ".venv", "__pycache__", ".pytest_cache",
    ".jupyter-config", ".jupyter-data", ".jupyter-runtime", ".ipynb_checkpoints",
}


def _iter_source_files():
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in {".py", ".ipynb"}:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


# ---------------------------------------------------------------- AC-002-01
def test_ac_002_01_labels_module_ton_tai_va_dung_23_ky_tu():
    """AC-002-01: Module src/vsl/labels.py ton tai, dinh nghia dung 23 ky tu."""
    assert MODULE_PATH.exists(), f"Module chua ton tai: {MODULE_PATH}"

    from src.vsl.labels import VIETNAMESE_ALPHABET, NUM_CLASSES

    # Kiem tra kieu tuple (bat bien)
    assert isinstance(VIETNAMESE_ALPHABET, tuple), (
        f"VIETNAMESE_ALPHABET phai la tuple bat bien, nhan duoc: {type(VIETNAMESE_ALPHABET)}"
    )

    # Kiem tra so luong
    assert len(VIETNAMESE_ALPHABET) == 23, (
        f"Do dai phai la 23, thuc te: {len(VIETNAMESE_ALPHABET)}"
    )

    # Kiem tra ky tu d va cac ky tu ngoai le
    assert "đ" in VIETNAMESE_ALPHABET, "VIETNAMESE_ALPHABET phai chua ky tu 'đ'"
    for invalid_char in ("f", "j", "w", "z"):
        assert invalid_char not in VIETNAMESE_ALPHABET, (
            f"VIETNAMESE_ALPHABET khong duoc chua ky tu '{invalid_char}'"
        )

    # Kiem tra thu tu chinh xac tung ky tu
    assert VIETNAMESE_ALPHABET == EXPECTED_ALPHABET, (
        f"Thu tu nhan khong khop voi BR-003.\nNhan: {VIETNAMESE_ALPHABET}\nKy vong: {EXPECTED_ALPHABET}"
    )

    # Kiem tra NUM_CLASSES suy ra tu do dai
    assert NUM_CLASSES == 23, f"NUM_CLASSES phai bang 23, thuc te: {NUM_CLASSES}"
    assert NUM_CLASSES == len(VIETNAMESE_ALPHABET)


def test_ac_002_01_re_export_qua_vsl_package():
    """Kiem tra re-export tu src/vsl/__init__.py."""
    import src.vsl as vsl

    assert hasattr(vsl, "VIETNAMESE_ALPHABET"), "src.vsl phai re-export VIETNAMESE_ALPHABET"
    assert hasattr(vsl, "NUM_CLASSES"), "src.vsl phai re-export NUM_CLASSES"

    from src.vsl import VIETNAMESE_ALPHABET, NUM_CLASSES
    assert VIETNAMESE_ALPHABET == EXPECTED_ALPHABET
    assert NUM_CLASSES == 23


# ---------------------------------------------------------------- AC-002-02
def test_ac_002_02_khong_con_np_eye_23_hardcode():
    """AC-002-02: Toan bo repository khong con chuoi np.eye(23)."""
    needle = "np.eye(" + "23)"
    violations = []

    for path in _iter_source_files():
        # Bo qua file test va docs/api
        if "tests" in path.parts or "docs" in path.parts:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        if needle in content:
            violations.append(str(path.relative_to(ROOT)))

    assert not violations, (
        f"Con sot np.eye(23) hard-code tai cac file: {violations}. "
        f"Phai thay bang np.eye(NUM_CLASSES) theo BR-003."
    )


# ---------------------------------------------------------------- Single Source of Truth
def test_single_source_of_truth_cho_vietnamese_alphabet():
    """Kiem tra khong con ban sao literal VIETNAMESE_ALPHABET o file khac."""
    # Pattern can tim la phep gan literal vao VIETNAMESE_ALPHABET
    needle_list = "VIETNAMESE_ALPHABET = ["
    needle_tuple = "VIETNAMESE_ALPHABET = ("
    violations = []

    for path in _iter_source_files():
        # Bo qua file test va chinh module labels.py
        if "tests" in path.parts or path == MODULE_PATH:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        if needle_list in content or needle_tuple in content:
            violations.append(str(path.relative_to(ROOT)))

    assert not violations, (
        f"Phat hien dinh nghia literal VIETNAMESE_ALPHABET tai cac file: {violations}. "
        f"Moi noi deu phai import tu src.vsl.labels theo BR-003."
    )
