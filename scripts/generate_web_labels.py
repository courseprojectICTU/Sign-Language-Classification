"""Generate the frontend label asset from the project's single label source."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.vsl.labels import VIETNAMESE_ALPHABET

OUTPUT_PATH = ROOT / "web" / "labels.json"


def generate_web_labels() -> Path:
    """Write the ordered Python label tuple as a UTF-8 JSON asset."""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(
        list(VIETNAMESE_ALPHABET),
        ensure_ascii=False,
        indent=2,
    )
    OUTPUT_PATH.write_text(f"{content}\n", encoding="utf-8")
    return OUTPUT_PATH


if __name__ == "__main__":
    generated_path = generate_web_labels()
    print(f"Generated {generated_path.relative_to(ROOT)}")
