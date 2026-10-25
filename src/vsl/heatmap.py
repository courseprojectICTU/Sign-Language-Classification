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

import numpy as np


def create_heatmap(landmarks, img_size=(224, 224), sigma=5):
    """Tra ve heatmap uint8 shape (img_size[0], img_size[1], 3).

    Tham so:
        landmarks: day so, do dai chia het cho 3, moi bo 3 la (x, y, z) chuan hoa 0..1.
        img_size: kich thuoc anh, mac dinh (224, 224).
        sigma: do rong Gaussian, mac dinh 5.

    Dau vao sai (do dai khong chia het cho 3) -> in canh bao va tra mang 0,
    giu nguyen hanh vi cu de khong pha notebook dang chay.
    """
    if len(landmarks) % 3 != 0:
        print(f"Warning: Invalid landmark data length {len(landmarks)}. Expected multiple of 3.")
        return np.zeros((img_size[0], img_size[1], 3), dtype=np.uint8)

    heatmap = np.zeros(img_size, dtype=np.float32)
    for i in range(0, len(landmarks), 3):
        x, y = landmarks[i], landmarks[i + 1]
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
