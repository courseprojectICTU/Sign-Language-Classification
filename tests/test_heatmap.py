"""Test cho US-001 — "Mot ban create_heatmap duy nhat".

Bam theo AC-001-01 va AC-001-02 trong docs/api/US-001.md.
File nay duoc viet TRUOC khi co src/vsl/heatmap.py (TDD) — luc dau phai DO.
"""

import json
import pathlib

import numpy as np
import pandas as pd
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "fixtures" / "heatmap_golden.npz"
MODULE = ROOT / "src" / "vsl" / "heatmap.py"

ALPHABET = ["a", "b", "c", "d", "đ", "e", "g", "h", "i", "k", "l", "m", "n",
            "o", "p", "q", "r", "s", "t", "u", "v", "x", "y"]

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


def _definition_hits():
    # Ghep chuoi de chinh file test nay khong tao ra literal can dem.
    needle = "def " + "create_heatmap"
    hits = []
    for path in _iter_source_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        count = text.count(needle)
        if count:
            hits.append((path.relative_to(ROOT).as_posix(), count))
    return hits


def _load_function():
    assert MODULE.exists(), (
        f"Chua co module dung chung: {MODULE.relative_to(ROOT).as_posix()} — TSK-001 chua lam"
    )
    from src.vsl.heatmap import create_heatmap

    return create_heatmap


def _landmarks(letter):
    values = pd.read_csv(ROOT / "data" / "anphabet" / letter / "1.csv").values.flatten()
    values = values.astype(np.float64)
    assert values.shape == (93,)
    return values


# ---------------------------------------------------------------- AC-001-01
def test_ac_001_01_chi_con_mot_dinh_nghia_tren_toan_repo():
    hits = _definition_hits()
    total = sum(count for _, count in hits)

    assert total == 1, (
        "Phai co dung 1 dinh nghia ham, thuc te "
        f"{total} tai: {hits}"
    )
    assert hits[0][0] == "src/vsl/heatmap.py", (
        f"Dinh nghia duy nhat phai nam trong src/vsl/heatmap.py, thuc te: {hits[0][0]}"
    )


# ---------------------------------------------------------------- AC-001-02
@pytest.mark.parametrize("golden_key,letter", [
    ("a", "a"),
    ("m", "m"),
    ("d", "đ"),
    ("random", None),
])
def test_ac_001_02_khop_golden_tung_diem_anh(golden_key, letter):
    create_heatmap = _load_function()
    golden = np.load(GOLDEN)

    vector = golden["landmarks_random"] if letter is None else _landmarks(letter)
    result = create_heatmap(vector)
    expected = golden[golden_key]

    assert result.shape == expected.shape == (224, 224, 3)
    assert result.dtype == expected.dtype == np.uint8
    assert np.array_equal(result, expected), (
        f"{golden_key}: {int(np.count_nonzero(result != expected))} diem anh lech golden"
    )


def test_ac_001_02_golden_co_nguon_goc_tu_notebook_cu():
    golden = np.load(GOLDEN)
    meta = [str(x) for x in golden["meta"]]

    assert any("train/train_cnn_pose_keras.ipynb" in item for item in meta), meta
    for key in ("a", "m", "d", "random", "a_sigma3"):
        assert key in golden.files, f"golden thieu key {key}"
        assert golden[key].shape == (224, 224, 3)
        assert golden[key].dtype == np.uint8


# ---------------------------------------------------------------- bien / loi
def test_dau_vao_khong_chia_het_cho_3_tra_mang_khong(capsys):
    create_heatmap = _load_function()

    out = create_heatmap(np.zeros(92, dtype=np.float64))

    assert out.shape == (224, 224, 3)
    assert out.dtype == np.uint8
    assert not out.any(), "dau vao sai phai tra ve mang toan 0"
    assert "Warning" in capsys.readouterr().out


def test_toan_bo_landmark_bang_0_tra_mang_khong():
    create_heatmap = _load_function()

    out = create_heatmap(np.zeros(93, dtype=np.float64))

    assert out.shape == (224, 224, 3)
    assert out.dtype == np.uint8
    assert not out.any(), "khong co landmark hop le phai tra ve mang 0 (khong chia cho 0)"


def test_sigma_tuy_chinh_van_dung_cong_thuc():
    create_heatmap = _load_function()
    golden = np.load(GOLDEN)

    result = create_heatmap(_landmarks("a"), sigma=3)

    assert result.dtype == np.uint8
    assert np.array_equal(result, golden["a_sigma3"])
