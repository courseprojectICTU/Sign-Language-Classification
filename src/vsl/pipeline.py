"""Inference pipeline matching train/train_cnn_pose_keras.ipynb."""
import numpy as np
from .schema import VIETNAMESE_ALPHABET, validate_landmarks


def create_heatmap(landmarks, img_size=(224, 224), sigma=5):
    """Gaussian accumulation, including uint8 truncation, from the notebook."""
    landmarks = validate_landmarks(landmarks)
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
                        heatmap[y_px + k, x_px + j] += np.exp(
                            -(j**2 + k**2) / (2 * sigma**2)
                        )
    if np.max(heatmap) > 0:
        heatmap = heatmap / np.max(heatmap)
    heatmap = (heatmap * 255).astype(np.uint8)
    return np.stack([heatmap] * 3, axis=2)


def predict_landmarks(model, landmarks, model_version="v1.0.0"):
    """Compare with notebook: ResNet50 Caffe preprocessing, not /255."""
    from tensorflow.keras.applications.resnet50 import preprocess_input

    batch = preprocess_input(np.expand_dims(create_heatmap(landmarks), axis=0))
    probabilities = np.asarray(model(batch, training=False).numpy()[0])
    if probabilities.shape != (len(VIETNAMESE_ALPHABET),):
        raise ValueError("Model must return 23 class probabilities")
    indices = np.argsort(probabilities)[::-1][:3]
    return {
        "status": "ok",
        "letter": VIETNAMESE_ALPHABET[int(indices[0])],
        "confidence": float(probabilities[indices[0]]),
        "top_k": [
            {"letter": VIETNAMESE_ALPHABET[int(i)], "confidence": float(probabilities[i])}
            for i in indices
        ],
        "model_version": model_version,
    }
