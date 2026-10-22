"""US-015: test the actual repository's training CSV contract."""
import csv
from pathlib import Path

import pytest
from src.vsl.schema import (
    FACE_KEYPOINTS, LANDMARK_COLUMNS, VIETNAMESE_ALPHABET,
    read_landmarks_csv, validate_landmarks,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "anphabet"


def test_contract_shape_order_and_labels():
    assert len(LANDMARK_COLUMNS) == 93
    assert len(set(LANDMARK_COLUMNS)) == 93
    assert len(FACE_KEYPOINTS) == 10
    assert len(VIETNAMESE_ALPHABET) == 23
    assert LANDMARK_COLUMNS[:6] == (
        "hand_x_0", "hand_y_0", "hand_z_0",
        "hand_x_1", "hand_y_1", "hand_z_1",
    )
    assert LANDMARK_COLUMNS[-3:] == ("face_x_199", "face_y_199", "face_z_199")


def test_all_real_csv_samples_respect_contract():
    assert DATA.is_dir(), "Repository data/anphabet is required"
    assert {p.name for p in DATA.iterdir() if p.is_dir()} == set(VIETNAMESE_ALPHABET)
    count = 0
    for letter in VIETNAMESE_ALPHABET:
        samples = list((DATA / letter).glob("*.csv"))
        assert samples, f"No samples for {letter}"
        for sample in samples:
            read_landmarks_csv(sample)
            count += 1
    assert count >= 23 * 50, "Dataset unexpectedly incomplete"


@pytest.mark.parametrize("values", [
    [], [0] * 92, [0] * 94,
    [0] * 92 + ["bad"],
    [0] * 92 + [float("nan")],
    [0] * 92 + [float("inf")],
])
def test_invalid_vectors_are_rejected(values):
    with pytest.raises(ValueError):
        validate_landmarks(values)


def test_negative_z_is_valid():
    values = [0] * 93
    values[2] = -0.25
    assert validate_landmarks(values)[2] == -0.25


def test_wrong_order_and_extra_row_are_rejected(tmp_path):
    csv_path = tmp_path / "invalid.csv"
    wrong = list(LANDMARK_COLUMNS)
    wrong[0], wrong[1] = wrong[1], wrong[0]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(wrong)
        writer.writerow([0] * 93)
    with pytest.raises(ValueError, match="column"):
        read_landmarks_csv(csv_path)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(LANDMARK_COLUMNS)
        writer.writerow([0] * 93)
        writer.writerow([0] * 93)
    with pytest.raises(ValueError, match="one header"):
        read_landmarks_csv(csv_path)
