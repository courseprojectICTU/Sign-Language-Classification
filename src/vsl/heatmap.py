"""Sinh heatmap tu vector landmark — BAN DUY NHAT cua du an (BR-002).

Ham nay duoc notebook huan luyen, notebook realtime va run_realtime.py cung import.
Khong duoc tao ban sao thu hai o bat ky dau.

Cong thuc giu nguyen 100% tu notebook train cu:
    img_size 224x224, sigma=5, hat nhan -15..15, cong don, chia cho max, nhan 255,
    np.stack thanh 3 kenh giong het nhau.

Luu y bat bien:
    - Truc z KHONG duoc dung (chi lay x, y).
    - he so nhan la x * img_size[1] va y * img_size[0] (giu nguyen, khong "sua").
    - Diem (0, 0) duoc coi la landmark thieu va bi bo qua.
"""

from typing import Sequence, Tuple, Union

import numpy as np


def create_heatmap(
    landmarks: Union[Sequence[float], np.ndarray],
    img_size: Tuple[int, int] = (224, 224),
    sigma: Union[int, float] = 5,
) -> np.ndarray:
    """Return a uint8 heatmap and reject malformed landmark vectors.

    Landmarks must be a one-dimensional real numeric vector of finite xyz
    coordinates. Invalid shape, values, or a length not divisible by three
    raises ValueError instead of silently returning a blank heatmap.
    """
    try:
        landmark_array = np.asarray(landmarks)
    except (TypeError, ValueError) as exc:
        raise ValueError("Landmarks must be a one-dimensional numeric vector.") from exc

    if landmark_array.ndim != 1:
        raise ValueError("Landmarks must be a one-dimensional numeric vector.")
    if landmark_array.size % 3 != 0:
        raise ValueError(
            f"Landmark data length {landmark_array.size} must be a multiple of 3."
        )
    if not np.issubdtype(landmark_array.dtype, np.number) or np.issubdtype(
        landmark_array.dtype, np.complexfloating
    ):
        raise ValueError("Landmarks must contain real numeric coordinates.")

    landmark_array = landmark_array.astype(np.float64, copy=False)
    if not np.all(np.isfinite(landmark_array)):
        raise ValueError("Landmarks must contain only finite coordinates.")

    heatmap = np.zeros(img_size, dtype=np.float32)
    for i in range(0, landmark_array.size, 3):
        x, y = landmark_array[i], landmark_array[i + 1]
        if x == 0 and y == 0:
            continue
        x_px = int(x * img_size[1])
        y_px = int(y * img_size[0])
        if 0 <= x_px < img_size[1] and 0 <= y_px < img_size[0]:
            for j in range(-sigma * 3, sigma * 3 + 1):
                for k in range(-sigma * 3, sigma * 3 + 1):
                    if 0 <= y_px + k < img_size[0] and 0 <= x_px + j < img_size[1]:
                        heatmap[y_px + k, x_px + j] += np.exp(-(j**2 + k**2) / (2 * sigma**2))

    if np.max(heatmap) > 0:
        heatmap = heatmap / np.max(heatmap)
    heatmap = (heatmap * 255).astype(np.uint8)
    return np.stack([heatmap] * 3, axis=2)
