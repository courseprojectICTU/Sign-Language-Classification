"""Test cho US-003 — "Loại bỏ đường dẫn tuyệt đối hard-code".

Bám theo AC-003-01, AC-003-02 trong docs/api/US-003.md và BR-004.
File này được viết TRƯỚC khi tạo src/vsl/config.py (TDD) — lúc đầu phải ĐỎ (FAIL).
"""

import json
import os
import pathlib
import re
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "vsl" / "config.py"

SKIP_DIRS = {
    ".git", ".venv", "__pycache__", ".pytest_cache",
    ".jupyter-config", ".jupyter-data", ".jupyter-runtime", ".ipynb_checkpoints",
}

# Các phần mở rộng mã nguồn và script thực thi
SOURCE_EXTENSIONS = {".py", ".ipynb", ".cmd", ".sh", ".bat"}


def _iter_source_files():
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in SOURCE_EXTENSIONS:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.resolve() == pathlib.Path(__file__).resolve():
            continue
        yield path


# ---------------------------------------------------------------- AC-003-01
def test_ac_003_01_khong_con_duong_dan_tuyet_doi_d_trong_ma_nguon():
    """AC-003-01: Quét toàn bộ repository, không còn chuỗi D:\\ hoặc D:/ trong mã nguồn."""
    d_drive_pattern = re.compile(r'[dD]:[\\/]')
    violations = []

    for path in _iter_source_files():
        rel_path = path.relative_to(ROOT).as_posix()
        try:
            if path.suffix == ".ipynb":
                content = json.loads(path.read_text(encoding="utf-8"))
                for cell_idx, cell in enumerate(content.get("cells", [])):
                    # Kiểm tra source code cell
                    cell_source = "".join(cell.get("source", []))
                    for line_no, line in enumerate(cell_source.splitlines(), 1):
                        if d_drive_pattern.search(line):
                            violations.append(f"{rel_path} (cell {cell_idx}, line {line_no}): {line.strip()}")
                    # Kiểm tra outputs của cell (nếu có lưu print cũ)
                    for out in cell.get("outputs", []):
                        out_text = "".join(out.get("text", []))
                        for line_no, line in enumerate(out_text.splitlines(), 1):
                            if d_drive_pattern.search(line):
                                violations.append(f"{rel_path} (output cell {cell_idx}, line {line_no}): {line.strip()}")
            else:
                lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
                for line_no, line in enumerate(lines, 1):
                    if d_drive_pattern.search(line):
                        violations.append(f"{rel_path}:{line_no}: {line.strip()}")
        except Exception as e:
            violations.append(f"Lỗi khi đọc file {rel_path}: {e}")

    assert not violations, (
        f"Vi phạm BR-004: Phát hiện {len(violations)} vị trí chứa đường dẫn ổ D:\\ trong mã nguồn:\n"
        + "\n".join(f"  - {v}" for v in violations[:20])
        + (f"\n  ... và {len(violations) - 20} vị trí khác" if len(violations) > 20 else "")
    )


# ---------------------------------------------------------------- AC-003-02
def test_ac_003_02_config_module_ton_tai_va_fallback_mac_dinh():
    """AC-003-02: Module src/vsl/config.py tồn tại, cung cấp fallback tương đối trỏ tới file thật."""
    assert MODULE_PATH.exists(), f"Module cấu hình chưa tồn tại: {MODULE_PATH}"

    from src.vsl.config import (
        PROJECT_ROOT,
        MODEL_PATH,
        DATA_DIR,
        BASE_PATH,
        get_model_path,
        get_data_dir,
    )

    # PROJECT_ROOT phải trỏ đúng gốc repo
    assert PROJECT_ROOT == ROOT, f"PROJECT_ROOT không khớp ROOT: {PROJECT_ROOT} vs {ROOT}"

    # Khi không có env var, get_model_path() trả về đường dẫn tương đối từ PROJECT_ROOT
    default_model = get_model_path()
    assert default_model == ROOT / "train" / "vsl_cnn_pose_keras.h5"
    assert default_model.exists(), f"File model mặc định không tồn tại: {default_model}"

    # Khi không có env var, get_data_dir() trả về đường dẫn tương đối từ PROJECT_ROOT
    default_data = get_data_dir()
    assert default_data == ROOT / "data" / "anphabet"
    assert default_data.is_dir(), f"Thư mục data mặc định không tồn tại: {default_data}"

    # BASE_PATH alias phải khớp DATA_DIR
    assert BASE_PATH == default_data, f"BASE_PATH alias không khớp: {BASE_PATH} vs {default_data}"
    assert MODEL_PATH == default_model


def test_ac_003_02_doc_duong_dan_tu_bien_moi_truong(monkeypatch):
    """AC-003-02: Cho phép override đường dẫn qua biến môi trường VSL_MODEL_PATH và VSL_DATA_DIR."""
    assert MODULE_PATH.exists(), f"Module cấu hình chưa tồn tại: {MODULE_PATH}"

    custom_model_path = "/app/models/custom_model.h5"
    custom_data_dir = "/app/data/custom_alphabet"

    monkeypatch.setenv("VSL_MODEL_PATH", custom_model_path)
    monkeypatch.setenv("VSL_DATA_DIR", custom_data_dir)

    from src.vsl.config import get_model_path, get_data_dir

    resolved_model = get_model_path()
    resolved_data = get_data_dir()

    assert resolved_model == pathlib.Path(custom_model_path), (
        f"get_model_path() không đọc đúng VSL_MODEL_PATH: {resolved_model}"
    )
    assert resolved_data == pathlib.Path(custom_data_dir), (
        f"get_data_dir() không đọc đúng VSL_DATA_DIR: {resolved_data}"
    )


def test_ac_003_02_re_export_qua_src_vsl():
    """BR-004: Package src.vsl phải re-export các hằng số và hàm cấu hình."""
    assert MODULE_PATH.exists(), f"Module cấu hình chưa tồn tại: {MODULE_PATH}"

    import src.vsl

    for symbol in ("PROJECT_ROOT", "MODEL_PATH", "DATA_DIR", "BASE_PATH", "get_model_path", "get_data_dir"):
        assert hasattr(src.vsl, symbol), f"src.vsl thiếu export '{symbol}'"
