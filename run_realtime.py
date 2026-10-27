import os
import sys

# Tu dong nap thu vien tu .venv neu nguoi dung chay bang Python ngoai
_project_root = os.path.dirname(os.path.abspath(__file__))
_venv_site = os.path.join(_project_root, '.venv', 'Lib', 'site-packages')
if os.path.exists(_venv_site) and _venv_site not in sys.path:
    sys.path.insert(0, _venv_site)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import cv2
import numpy as np
import mediapipe as mp
from keras.models import load_model
from keras.applications.resnet50 import preprocess_input
from PIL import Image, ImageDraw, ImageFont

from src.vsl.heatmap import create_heatmap  # BR-002: ban duy nhat
from src.vsl.labels import VIETNAMESE_ALPHABET  # BR-003: ban duy nhat
from src.vsl.config import get_model_path  # BR-004: doc tu env / fallback tuong doi

# Khởi tạo MediaPipe
mp_hands = mp.solutions.hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
mp_face_mesh = mp.solutions.face_mesh.FaceMesh(max_num_faces=1, min_detection_confidence=0.7)
mp_drawing = mp.solutions.drawing_utils

MODEL_PATH = str(get_model_path())

print(f"Đang nạp mô hình từ: {MODEL_PATH}")
model = load_model(MODEL_PATH)
print("Nạp mô hình thành công!\n")

def draw_vietnamese_text(image, text, position, font_size=30, color=(0, 255, 0)):
    image_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(image_pil)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except IOError:
        font = ImageFont.load_default()
    draw.text(position, text, font=font, fill=color)
    return cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)

def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Không thể mở webcam (index 0). Thử camera index 1...")
        cap = cv2.VideoCapture(1)
        if not cap.isOpened():
            print("Lỗi: Không tìm thấy camera khả dụng!")
            return

    print("================================================================")
    print("  Đang chạy nhận diện ký hiệu tiếng Việt realtime.")
    print("  - Đưa cả 1 BÀN TAY và KHUÔN MẶT vào khung hình.")
    print("  - Nhấn phím 'q' trên cửa sổ camera để DỪNG.")
    print("================================================================\n")

    try:
        while cap.isOpened():
            success, image = cap.read()
            if not success:
                print("Không thể đọc frame.")
                break

            image = cv2.flip(image, 1)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Nhận diện tay
            hands_results = mp_hands.process(image_rgb)
            hand_landmarks = []
            if hands_results.multi_hand_landmarks:
                for hand_landmark in hands_results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(image, hand_landmark, mp.solutions.hands.HAND_CONNECTIONS)
                    for landmark in hand_landmark.landmark:
                        hand_landmarks.extend([landmark.x, landmark.y, landmark.z])

            # Nhận diện mặt
            face_results = mp_face_mesh.process(image_rgb)
            face_landmarks = []
            if face_results.multi_face_landmarks:
                for face_landmark in face_results.multi_face_landmarks:
                    key_points = [10, 152, 234, 454, 33, 263, 1, 61, 291, 199]
                    for idx in key_points:
                        landmark = face_landmark.landmark[idx]
                        face_landmarks.extend([landmark.x, landmark.y, landmark.z])

            all_landmarks = hand_landmarks + face_landmarks
            has_hand = bool(hands_results.multi_hand_landmarks)
            has_face = bool(face_results.multi_face_landmarks)

            if all_landmarks and len(all_landmarks) == 93:
                heatmap = create_heatmap(all_landmarks)
                heatmap_input = np.expand_dims(heatmap, axis=0)
                heatmap_input = preprocess_input(heatmap_input)

                predictions = model(heatmap_input, training=False).numpy()
                predicted_class = np.argmax(predictions, axis=1)[0]
                predicted_letter = VIETNAMESE_ALPHABET[predicted_class]
                confidence = np.max(predictions) * 100

                text = f"Letter: {predicted_letter} ({confidence:.2f}%)"
                image = draw_vietnamese_text(image, text, position=(10, 30), font_size=32, color=(0, 255, 0))
            else:
                status = f"Dang tim: Tay [{'OK' if has_hand else 'X'}] | Mat [{'OK' if has_face else 'X'}]"
                cv2.putText(image, status, (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)

            cv2.imshow("Nhan dien ngon ngu ky hieu (Nhan 'q' de thoat)", image)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("Đã nhận phím 'q'. Dừng camera.")
                break

    except KeyboardInterrupt:
        print("Dừng camera.")
    finally:
        cap.release()
        cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
