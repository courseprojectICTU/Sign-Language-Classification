"""Compatibility entry point for exporting the US-016 notebook reference."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from _export_us016_from_notebook import main


if __name__ == "__main__":
    main()
