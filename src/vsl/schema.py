"""Authoritative 93-value landmark contract from the training notebook."""
import csv
import math
from pathlib import Path

FACE_KEYPOINTS = (10, 152, 234, 454, 33, 263, 1, 61, 291, 199)
VIETNAMESE_ALPHABET = (
    "a", "b", "c", "d", "đ", "e", "g", "h", "i", "k", "l", "m",
    "n", "o", "p", "q", "r", "s", "t", "u", "v", "x", "y",
)
LANDMARK_COLUMNS = tuple(
    f"hand_{axis}_{point}" for point in range(21) for axis in "xyz"
) + tuple(
    f"face_{axis}_{point}" for point in FACE_KEYPOINTS for axis in "xyz"
)


def validate_landmarks(values):
    """Validate shape and numeric finiteness; z is allowed to be negative."""
    try:
        values = tuple(float(v) for v in values)
    except (TypeError, ValueError) as exc:
        raise ValueError("All landmarks must be numeric") from exc
    if len(values) != 93:
        raise ValueError(f"Expected exactly 93 landmark values, got {len(values)}")
    if not all(math.isfinite(v) for v in values):
        raise ValueError("Landmarks contain NaN or infinity")
    return values


def read_landmarks_csv(path):
    """Read one sample: exactly one header and one 93-value data row."""
    with Path(path).open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.reader(source))
    if len(rows) != 2:
        raise ValueError(f"Expected one header and one data row in {path}")
    if tuple(rows[0]) != LANDMARK_COLUMNS:
        raise ValueError(f"Incorrect landmark column names or order in {path}")
    return validate_landmarks(rows[1])
