"""Cau hinh pytest: dua repo root vao sys.path de import duoc `src.vsl`."""

import platform
import sys
from pathlib import Path

# Tranh crash 0xc06d007e khi platform.py goi WMI query tren sandbox Windows
if not getattr(platform, "_uname_cache", None):
    platform._uname_cache = platform.uname_result("Windows", "DESKTOP", "10", "10.0.19041", "AMD64")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FIXTURES = ROOT / "tests" / "fixtures"
