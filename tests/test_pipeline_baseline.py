"""Test hoi quy T7 cua US-001: toan pipeline van dung 23/23 ky tu.

Kiem chung sau khi tach create_heatmap ra module dung chung, ket qua model khong doi.
"""

import pathlib

import numpy as np
import pandas as pd
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "train" / "vsl_cnn_pose_keras.h5"

ALPHABET = ["a", "b", "c", "d", "đ", "e", "g", "h", "i", "k", "l", "m", "n",
            "o", "p", "q", "r", "s", "t", "u", "v", "x", "y"]


@pytest.fixture(scope="module")
def model():
    from tensorflow.keras.models import load_model

    assert MODEL_PATH.exists(), f"thieu model: {MODEL_PATH}"
    return load_model(str(MODEL_PATH))


def test_toan_pipeline_dung_23_23_ky_tu(model):
    from tensorflow.keras.applications.resnet50 import preprocess_input

    from src.vsl.heatmap import create_heatmap

    wrong = []
    for letter in ALPHABET:
        vector = pd.read_csv(
            ROOT / "data" / "anphabet" / letter / "1.csv"
        ).values.flatten().astype(np.float64)
        heatmap = create_heatmap(vector)
        batch = preprocess_input(np.expand_dims(heatmap, axis=0))
        prediction = model(batch, training=False).numpy()[0]
        predicted = ALPHABET[int(np.argmax(prediction))]
        if predicted != letter:
            wrong.append((letter, predicted, float(np.max(prediction) * 100)))

    assert not wrong, f"{len(wrong)}/23 sai: {wrong}"
