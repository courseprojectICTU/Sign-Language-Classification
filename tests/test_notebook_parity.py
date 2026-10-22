"""US-016: compare the new pipeline directly against notebook function source."""
import ast
import json
from pathlib import Path

import numpy as np
import pytest

from src.vsl.pipeline import create_heatmap
from src.vsl.schema import VIETNAMESE_ALPHABET, read_landmarks_csv

ROOT = Path(__file__).resolve().parents[1]


def notebook_heatmap(path):
    notebook = json.loads(path.read_text(encoding="utf-8"))
    for cell in notebook["cells"]:
        if cell["cell_type"] != "code":
            continue
        tree = ast.parse("".join(cell["source"]))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == "create_heatmap":
                namespace = {"np": np}
                isolated = ast.Module(body=[node], type_ignores=[])
                exec(compile(isolated, str(path), "exec"), namespace)
                return namespace["create_heatmap"]
    raise AssertionError(f"Missing create_heatmap in {path}")


@pytest.mark.parametrize("notebook", [
    "train/train_cnn_pose_keras.ipynb", "run_realtime.ipynb",
])
def test_heatmap_matches_notebook_for_real_samples(notebook):
    reference = notebook_heatmap(ROOT / notebook)
    for letter in VIETNAMESE_ALPHABET:
        landmarks = read_landmarks_csv(ROOT / "data" / "anphabet" / letter / "1.csv")
        assert np.array_equal(
            create_heatmap(landmarks), reference(landmarks)
        ), f"Heatmap mismatch for letter {letter} in {notebook}"


def test_heatmap_missing_points_and_shape():
    vector = [0.0] * 93
    image = create_heatmap(vector)
    assert image.shape == (224, 224, 3)
    assert image.dtype == np.uint8
    assert np.count_nonzero(image) == 0
    vector[0:3] = [0.5, 0.5, -0.2]
    assert np.count_nonzero(create_heatmap(vector)) > 0
