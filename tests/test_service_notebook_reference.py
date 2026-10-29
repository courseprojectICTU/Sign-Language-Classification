"""Regression tests for service parity with the frozen notebook inference output."""

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from src.vsl.config import get_data_dir, get_model_path
from src.vsl.heatmap import create_heatmap as notebook_create_heatmap
from src.vsl.labels import VIETNAMESE_ALPHABET

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_PATH = ROOT / "tests" / "fixtures" / "notebook_prediction_reference.json"


@pytest.fixture(scope="module")
def notebook_reference():
    payload = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    samples = payload["samples"]

    assert "run_realtime.ipynb" in payload["source"]
    assert len(samples) == len(VIETNAMESE_ALPHABET) == 23
    assert len(payload["model_sha256"]) == 64
    assert all(
        character in "0123456789abcdef"
        for character in payload["model_sha256"]
    )
    return payload


@pytest.fixture(scope="module")
def reference_predictions(notebook_reference):
    samples = notebook_reference["samples"]
    references = {sample["sample"].split("/")[0]: sample for sample in samples}

    assert len(references) == len(samples), "Duplicate sample in notebook reference"
    assert set(references) == set(VIETNAMESE_ALPHABET)
    assert all(
        references[letter]["sample"] == f"{letter}/1.csv"
        for letter in VIETNAMESE_ALPHABET
    )
    return references


@pytest.fixture(scope="module")
def model(notebook_reference):
    from keras.models import load_model

    model_path = get_model_path()
    assert model_path.is_file(), f"Model file not found: {model_path}"

    digest = hashlib.sha256()
    with model_path.open("rb") as model_file:
        for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
            digest.update(chunk)

    actual_sha256 = digest.hexdigest()
    expected_sha256 = notebook_reference["model_sha256"]
    assert actual_sha256 == expected_sha256, (
        "Current model does not match the model used for the notebook reference: "
        f"expected SHA-256 {expected_sha256}, got {actual_sha256}. "
        "Review the model change and regenerate the reference intentionally if needed."
    )

    return load_model(str(model_path))


def _load_landmarks(letter):
    csv_path = get_data_dir() / letter / "1.csv"
    assert csv_path.is_file(), f"Landmark sample not found: {csv_path}"
    landmarks = pd.read_csv(csv_path).values.flatten().astype(np.float64).tolist()
    assert len(landmarks) == 93, f"{csv_path}: expected 93 coordinates"
    return landmarks


def test_ac_016_01_service_matches_notebook_reference(model, reference_predictions):
    from src.vsl.service import predict_from_landmarks

    mismatches = []
    for letter in VIETNAMESE_ALPHABET:
        expected = reference_predictions[letter]
        result = predict_from_landmarks(_load_landmarks(letter), model, top_k=3)
        confidence_percent = round(result["confidence"] * 100, 2)

        if (
            result["letter"] != expected["letter"]
            or confidence_percent != expected["confidence_percent"]
        ):
            mismatches.append(
                (
                    expected["sample"],
                    expected["letter"],
                    result["letter"],
                    expected["confidence_percent"],
                    confidence_percent,
                )
            )

    assert not mismatches, f"Service differs from notebook reference: {mismatches}"
    assert all(
        reference_predictions[letter]["letter"] == letter
        for letter in VIETNAMESE_ALPHABET
    ), "Frozen notebook reference is not 23/23 on the labeled training samples"


def test_ac_016_02_reference_detects_sigma_3_regression(
    model, reference_predictions
):
    from src.vsl.service import predict_from_landmarks

    expected = reference_predictions["a"]
    with patch(
        "src.vsl.service.create_heatmap",
        side_effect=lambda landmarks: notebook_create_heatmap(landmarks, sigma=3),
    ):
        result = predict_from_landmarks(_load_landmarks("a"), model, top_k=3)

    actual_confidence = round(result["confidence"] * 100, 2)
    assert (
        result["letter"] != expected["letter"]
        or actual_confidence != expected["confidence_percent"]
    ), "sigma=3 unexpectedly matched the frozen notebook reference"
