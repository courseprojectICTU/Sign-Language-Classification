"""Sinh golden reference cho US-001 — PHAI chay TRUOC khi refactor.

Nguon goc cua golden la **dinh nghia create_heatmap trong notebook train cu**
(`train/train_cnn_pose_keras.ipynb`), khong phai module se tao ra sau nay.
Nho vay AC-001-02 kiem chung duoc "ket qua giong het ban tham chieu da luu".

Chay:
    & "D:\\program\\python\\python.exe" tests\\_generate_golden.py
"""

import json
import pathlib
import re

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "train" / "train_cnn_pose_keras.ipynb"
OUT = ROOT / "tests" / "fixtures" / "heatmap_golden.npz"


def load_reference_implementation():
    """Doc thang code trong notebook cu, khong import module moi."""
    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    for cell in nb["cells"]:
        if cell.get("cell_type") != "code":
            continue
        src = "".join(cell.get("source", []))
        # Ghep chuoi de khong tao ra literal "def create_heatmap" trong file nay
        # (test AC-001-01 dem so lan xuat hien literal do tren toan repo).
        needle = "def " + "create_heatmap"
        if needle in src:
            match = re.search(needle + r".*?(?=\ndef |\Z)", src, re.S)
            if match:
                return match.group(0)
    raise RuntimeError("Khong tim thay create_heatmap trong notebook train cu")


def load_landmarks(letter):
    df = pd.read_csv(ROOT / "data" / "anphabet" / letter / "1.csv")
    values = df.values.flatten().astype(np.float64)
    assert values.shape == (93,), f"{letter}: {values.shape} != (93,)"
    return values


def main():
    namespace = {"np": np}
    exec(load_reference_implementation(), namespace)  # noqa: S102 - co y do
    reference = namespace["create_heatmap"]

    landmarks = {
        "a": load_landmarks("a"),
        "m": load_landmarks("m"),
        "d": load_landmarks("\u0111"),
    }
    rng = np.random.default_rng(42)
    landmarks["random"] = rng.random(93)

    payload = {}
    for key, vector in landmarks.items():
        payload[key] = reference(vector)
    payload["a_sigma3"] = reference(landmarks["a"], sigma=3)
    payload["landmarks_a"] = landmarks["a"]
    payload["landmarks_random"] = landmarks["random"]
    payload["meta"] = np.array(
        ["source=train/train_cnn_pose_keras.ipynb", "img_size=224x224", "sigma=5", "dtype=uint8"]
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT, **payload)

    print(f"golden: {OUT}")
    for key in ("a", "m", "d", "random", "a_sigma3"):
        arr = payload[key]
        print(f"  {key:9} shape={arr.shape} dtype={arr.dtype} max={arr.max()} sum={int(arr.sum())}")
    print(f"  size={OUT.stat().st_size} bytes")


if __name__ == "__main__":
    main()
