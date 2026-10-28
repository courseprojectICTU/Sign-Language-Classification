"""Generate frozen prediction results by replaying the notebook inference path."""

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from keras.applications.resnet50 import preprocess_input
from keras.models import load_model

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.vsl.config import get_data_dir, get_model_path
from src.vsl.heatmap import create_heatmap
from src.vsl.labels import VIETNAMESE_ALPHABET

OUTPUT = ROOT / "tests" / "fixtures" / "notebook_prediction_reference.json"


def main() -> None:
    model_path = get_model_path()
    if not model_path.is_file():
        raise FileNotFoundError(f"Model file not found: {model_path}")

    model = load_model(str(model_path))
    samples = []

    for expected_letter in VIETNAMESE_ALPHABET:
        csv_path = get_data_dir() / expected_letter / "1.csv"
        if not csv_path.is_file():
            raise FileNotFoundError(f"Landmark sample not found: {csv_path}")

        landmarks = pd.read_csv(csv_path).values.flatten().astype(np.float64)
        if landmarks.shape != (93,):
            raise ValueError(f"{csv_path}: expected 93 coordinates, got {landmarks.shape}")

        heatmap = create_heatmap(landmarks)
        batch = preprocess_input(np.expand_dims(heatmap, axis=0))
        probabilities = model(batch, training=False).numpy()[0]
        predicted_index = int(np.argmax(probabilities))
        predicted_letter = VIETNAMESE_ALPHABET[predicted_index]
        if predicted_letter != expected_letter:
            raise RuntimeError(
                f"Notebook inference mismatch for {csv_path}: "
                f"expected {expected_letter!r}, got {predicted_letter!r}"
            )

        samples.append(
            {
                "sample": f"{expected_letter}/1.csv",
                "letter": predicted_letter,
                "confidence_percent": round(float(probabilities[predicted_index]) * 100, 2),
            }
        )

    payload = {
        "source": "run_realtime.ipynb inference sequence replayed on the 23 labeled 1.csv samples",
        "model_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
        "interpretation": "Training-sample validity check only; not real-world accuracy.",
        "samples": samples,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(samples)} reference predictions to {OUTPUT}")


if __name__ == "__main__":
    main()
