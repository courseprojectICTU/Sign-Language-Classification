"""Verify service predictions against a direct replay of notebook inference."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from keras.applications.resnet50 import preprocess_input
from keras.models import load_model

from src.vsl.config import get_data_dir, get_model_path
from src.vsl.heatmap import create_heatmap
from src.vsl.labels import VIETNAMESE_ALPHABET

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_PATH = ROOT / "tests" / "fixtures" / "notebook_prediction_reference.json"
CONFIDENCE_TOLERANCE = 0.0001


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@pytest.fixture(scope="module")
def reference():
    payload = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    samples = payload["samples"]
    assert "run_realtime.ipynb" in payload["source"]
    assert len(samples) == len(VIETNAMESE_ALPHABET) == 23

    by_letter = {sample["sample"].split("/")[0]: sample for sample in samples}
    assert len(by_letter) == len(samples), "Duplicate sample in notebook reference"
    assert set(by_letter) == set(VIETNAMESE_ALPHABET)
    return payload, by_letter


@pytest.fixture(scope="module")
def model(reference):
    payload, _ = reference
    model_path = get_model_path()
    assert model_path.is_file(), f"Model file not found: {model_path}"

    actual_sha256 = _sha256_file(model_path)
    expected_sha256 = payload["model_sha256"]
    assert actual_sha256 == expected_sha256, (
        "Current model does not match the direct notebook reference: "
        f"expected SHA-256 {expected_sha256}, got {actual_sha256}"
    )
    return load_model(str(model_path))


def _load_sample(letter: str, expected_sha256: str) -> list[float]:
    csv_path = get_data_dir() / letter / "1.csv"
    assert csv_path.is_file(), f"Landmark sample not found: {csv_path}"

    actual_sha256 = _sha256_file(csv_path)
    assert actual_sha256 == expected_sha256, (
        f"CSV does not match the notebook reference for {letter}/1.csv: "
        f"expected SHA-256 {expected_sha256}, got {actual_sha256}"
    )

    landmarks = pd.read_csv(csv_path).values.flatten().astype(np.float64).tolist()
    assert len(landmarks) == 93, f"{csv_path}: expected 93 coordinates"
    return landmarks


def test_notebook_and_service_match_23_samples_and_hashes(model, reference):
    from src.vsl.service import predict_from_landmarks

    _, references = reference
    notebook_mismatches = []
    service_mismatches = []
    confidence_mismatches = []

    for expected_letter in VIETNAMESE_ALPHABET:
        expected = references[expected_letter]
        assert expected["sample"] == f"{expected_letter}/1.csv"
        landmarks = _load_sample(expected_letter, expected["csv_sha256"])

        # Match the preprocessing and model call sequence in run_realtime.ipynb.
        heatmap = create_heatmap(landmarks)
        notebook_input = preprocess_input(np.expand_dims(heatmap, axis=0))
        notebook_probabilities = model(notebook_input, training=False).numpy()[0]
        notebook_index = int(np.argmax(notebook_probabilities))
        notebook_letter = VIETNAMESE_ALPHABET[notebook_index]
        notebook_confidence = float(notebook_probabilities[notebook_index])

        if notebook_letter != expected_letter:
            notebook_mismatches.append(
                (expected["sample"], expected_letter, notebook_letter)
            )
        if notebook_letter != expected["letter"]:
            notebook_mismatches.append(
                (expected["sample"], expected["letter"], notebook_letter)
            )
        if abs(notebook_confidence - expected["confidence"]) > CONFIDENCE_TOLERANCE:
            confidence_mismatches.append(
                (
                    expected["sample"],
                    "notebook/reference",
                    expected["confidence"],
                    notebook_confidence,
                )
            )

        service_result = predict_from_landmarks(landmarks, model, top_k=3)
        if service_result["letter"] != notebook_letter:
            service_mismatches.append(
                (expected["sample"], notebook_letter, service_result["letter"])
            )
        confidence_delta = abs(service_result["confidence"] - notebook_confidence)
        if confidence_delta > CONFIDENCE_TOLERANCE:
            confidence_mismatches.append(
                (
                    expected["sample"],
                    "service/notebook",
                    notebook_confidence,
                    service_result["confidence"],
                )
            )

    assert not notebook_mismatches, (
        f"Direct notebook replay did not predict all 23 labeled samples: "
        f"{notebook_mismatches}"
    )
    assert not service_mismatches, (
        f"Service predictions differ from direct notebook inference: "
        f"{service_mismatches}"
    )
    assert not confidence_mismatches, (
        f"Confidence differences exceeded {CONFIDENCE_TOLERANCE}: "
        f"{confidence_mismatches}"
    )
