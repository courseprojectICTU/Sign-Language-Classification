"""Optional GPU/TF parity run: TEST_KERAS_PARITY=1 python -m pytest ..."""
import os
from pathlib import Path

import numpy as np
import pytest

from src.vsl.pipeline import create_heatmap, predict_landmarks
from src.vsl.schema import VIETNAMESE_ALPHABET, read_landmarks_csv

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "train" / "vsl_cnn_pose_keras.h5"


@pytest.mark.skipif(os.getenv("TEST_KERAS_PARITY") != "1", reason="TF parity is opt-in")
def test_service_matches_known_notebook_predictions_23_letters():
    tf = pytest.importorskip("tensorflow")
    from tensorflow.keras.applications.resnet50 import preprocess_input

    assert MODEL.stat().st_size > 1_000_000, "Run git lfs pull for the real model"
    model = tf.keras.models.load_model(MODEL)
    for letter in VIETNAMESE_ALPHABET:
        sample = ROOT / "data" / "anphabet" / letter / "1.csv"
        vector = read_landmarks_csv(sample)
        # Golden labels: see AGENTS.md, 2026-10-15 notebook sanity check (23/23).
        notebook_input = preprocess_input(np.expand_dims(create_heatmap(vector), 0))
        notebook_probs = model(notebook_input, training=False).numpy()[0]
        actual = predict_landmarks(model, vector)
        assert actual["letter"] == VIETNAMESE_ALPHABET[int(np.argmax(notebook_probs))]
        assert actual["confidence"] == pytest.approx(float(np.max(notebook_probs)), abs=1e-6)
        assert actual["letter"] == letter, f"Known notebook prediction changed for {letter}"
