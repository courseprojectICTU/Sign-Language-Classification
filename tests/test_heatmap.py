"""NumPy-only unit tests for the create_heatmap numerical contract (US-014)."""
import numpy as np
import pytest

from src.vsl.heatmap import create_heatmap


def test_create_heatmap_shape() -> None:
    """The default output has exactly 224 rows, columns, and three channels."""
    landmarks = np.array([0.5, 0.5, 0.0], dtype=np.float32)

    result = create_heatmap(landmarks)

    assert result.shape == (224, 224, 3)


def test_create_heatmap_dtype() -> None:
    """The heatmap uses uint8 pixels for model-compatible image input."""
    landmarks = np.array([0.5, 0.5, 0.0], dtype=np.float32)

    result = create_heatmap(landmarks)

    assert result.dtype == np.uint8


def test_create_heatmap_pixel_range() -> None:
    """Every generated channel value stays in the valid uint8 range."""
    landmarks = np.array([0.25, 0.4, 0.0, 0.7, 0.6, -0.1], dtype=np.float64)

    result = create_heatmap(landmarks)

    assert int(result.min()) >= 0
    assert int(result.max()) <= 255


def test_create_heatmap_ignores_missing_origin_landmarks() -> None:
    """Appending a missing (0, 0) landmark does not change the heatmap."""
    valid_landmark = np.array([0.5, 0.5, 0.25], dtype=np.float64)
    with_missing_landmark = np.concatenate(
        [valid_landmark, np.array([0.0, 0.0, 0.9], dtype=np.float64)]
    )

    expected = create_heatmap(valid_landmark)
    result = create_heatmap(with_missing_landmark)

    np.testing.assert_array_equal(result, expected)


def test_create_heatmap_invalid_length_raises_value_error() -> None:
    """A coordinate vector not divisible into xyz triplets is rejected."""
    landmarks = np.zeros(92, dtype=np.float64)

    with pytest.raises(ValueError, match="multiple of 3"):
        create_heatmap(landmarks)


def test_create_heatmap_non_vector_input_raises_value_error() -> None:
    """A two-dimensional array is rejected instead of being flattened silently."""
    landmarks = np.zeros((31, 3), dtype=np.float64)

    with pytest.raises(ValueError, match="one-dimensional"):
        create_heatmap(landmarks)


def test_create_heatmap_non_numeric_input_raises_value_error() -> None:
    """Non-numeric landmark values are rejected with a clear exception."""
    landmarks = np.array(["x", "y", "z"])

    with pytest.raises(ValueError, match="numeric"):
        create_heatmap(landmarks)


def test_create_heatmap_non_finite_input_raises_value_error() -> None:
    """NaN and infinity are rejected before pixel-index calculations."""
    landmarks = np.array([np.nan, 0.5, 0.0], dtype=np.float64)

    with pytest.raises(ValueError, match="finite"):
        create_heatmap(landmarks)


def test_create_heatmap_empty_input_returns_zero_heatmap() -> None:
    """An empty but well-formed vector produces an empty heatmap without division by zero."""
    result = create_heatmap(np.array([], dtype=np.float64))

    assert result.shape == (224, 224, 3)
    assert result.dtype == np.uint8
    assert not np.any(result)
