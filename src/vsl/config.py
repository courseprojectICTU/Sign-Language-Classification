"""Module quan ly cau hinh va duong dan tap trung cho du an VSL (US-003, BR-004).

Thoa man:
- BR-004: Khong chua duong dan tuyet doi hard-code.
- Uu tien doc duong dan tu bien moi truong: VSL_MODEL_PATH va VSL_DATA_DIR.
- Fallback mac dinh la duong dan tuong doi tinh tu goc repository (PROJECT_ROOT).
"""

from pathlib import Path
import os

# Thu muc goc cua repository (3 cap tren so voi src/vsl/config.py)
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent


def get_model_path() -> Path:
    """Tra ve duong dan toi file mo hinh Keras (.h5).

    Uu tien bien moi truong VSL_MODEL_PATH.
    Neu khong dat, fallback ve <PROJECT_ROOT>/train/vsl_cnn_pose_keras.h5.
    """
    env_val = os.environ.get("VSL_MODEL_PATH")
    if env_val:
        return Path(env_val)
    return PROJECT_ROOT / "train" / "vsl_cnn_pose_keras.h5"


def get_data_dir() -> Path:
    """Tra ve duong dan toi thu muc du lieu landmark CSV.

    Uu tien bien moi truong VSL_DATA_DIR.
    Neu khong dat, fallback ve <PROJECT_ROOT>/data/anphabet.
    """
    env_val = os.environ.get("VSL_DATA_DIR")
    if env_val:
        return Path(env_val)
    return PROJECT_ROOT / "data" / "anphabet"


# Hang so mac dinh tai thoi diem import
MODEL_PATH: Path = get_model_path()
DATA_DIR: Path = get_data_dir()
BASE_PATH: Path = DATA_DIR  # Alias tuong thich nguoc cho cac notebook cu
