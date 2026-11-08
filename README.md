# Vietnamese Sign Language Classification

This repository classifies 23 Vietnamese sign-language alphabet characters from
images. The Python service extracts hand and face landmarks with MediaPipe,
converts them to a heatmap, and runs a ResNet50-based Keras model.

## Architecture and current delivery status

- **Backend:** FastAPI in `src/vsl/service.py`; the Docker container listens on
  port `8080`. The API provides `GET /health`, `GET /version`, and `POST
  /predict`.
- **Model pipeline:** 93 hand/face coordinates → `create_heatmap` → ResNet50
  inference. The model file is stored with Git LFS at
  `train/vsl_cnn_pose_keras.h5`.
- **Cloud target:** project infrastructure documents describe Azure Container
  Apps (ACA), not Cloud Run. The repository has no frontend source and no
  deployment automation in `develop`.
- **Feature branches:** CI (US-026), smoke test (US-017), CORS (US-025), and
  guarded ACA rollback (US-031) are separate PR branches. Their behavior is
  not part of `develop` until those PRs are reviewed and merged. The existing
  `feature/US-038` branch was not changed because it already contains a mixed
  changeset; multi-stage image optimization is therefore not available here.
- The infrastructure handoff document reports a staging environment, but its
  current health, revision state, URL, and permissions were not verified as
  part of this documentation update. Do not treat examples below as proof of a
  successful deployment.

## Repository map

| Path | Purpose |
|---|---|
| `src/vsl/` | Shared labels, configuration, landmarks, heatmap, and FastAPI service |
| `tests/` | Unit, API-contract, and regression tests |
| `scripts/` | Benchmark and operational CLIs; branch-only scripts are identified below |
| `data/anphabet/` | Landmark CSV training data |
| `train/` | Training notebook and Git-LFS model |
| `process_images/` | Data collection notebook |
| `docs/architecture/` | Architecture decisions |
| `docs/api/` | Per-story API and CLI contracts |
| `docs/infrastructure/` | Azure deployment and handoff material |
| `docs/RUNBOOK.md` | Operational troubleshooting and recovery |
| `docs/implementation/US-IMPLEMENTATION-STATUS.md` | Requested-story progress, evidence, and branch dependencies |

## Run locally

Use Python 3.12. Clone the model from Git LFS before starting the API:

```powershell
git lfs install
git lfs pull
py -3.12 -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
& ".\.venv\Scripts\python.exe" -m uvicorn src.vsl.service:app --host 127.0.0.1 --port 8000
```

Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) to try the API.
`GET /health` reports model readiness; use the Swagger UI to submit an image to
`POST /predict`. The repository does not include a verified sample image.

For webcam inference, see [HUONG-DAN-CHAY.md](HUONG-DAN-CHAY.md) and
[`run_realtime.py`](run_realtime.py).

## Tests and lint

Run the complete test suite:

```powershell
& ".\.venv\Scripts\python.exe" -m pytest tests -v
```

The NumPy-only heatmap and repository contract tests can be run separately:

```powershell
& ".\.venv\Scripts\python.exe" -m pytest -v tests/test_heatmap.py tests/test_heatmap_contract.py
```

The PR workflow and Ruff/Black configuration are on `feature/US-026`; they are
not yet present on `develop`. After US-026 is merged and its dev dependencies
are installed, run:

```powershell
ruff check src tests scripts
black --check src tests scripts
```

That workflow runs on pull requests, executes selected tests, and builds—but
does not push—the Docker image. See
[`docs/implementation/US-IMPLEMENTATION-STATUS.md`](docs/implementation/US-IMPLEMENTATION-STATUS.md)
for the branch and verification status.

## Build and run Docker locally

The current Dockerfile is single-stage and is not pinned by digest. US-038
optimization has not been applied to this branch.

```powershell
$sha = (git rev-parse HEAD).Trim()
docker build --build-arg "GIT_SHA=$sha" --tag vsl-api:local .
docker run --detach --publish 8080:8080 --name vsl-api-local vsl-api:local
curl.exe --fail http://localhost:8080/health
curl.exe --fail http://localhost:8080/version
docker logs vsl-api-local
docker stop vsl-api-local
docker rm vsl-api-local
```

Docker must be running. Do not publish an image from the pull-request CI
workflow; publishing/deployment is not currently automated.

## Deploy and operate

The documented cloud target is **Azure Container Apps**, not Cloud Run.
Deployment is not automated in `develop`. Review
[`docs/infrastructure/HUONG-DAN-TRIEN-KHAI-AZURE.md`](docs/infrastructure/HUONG-DAN-TRIEN-KHAI-AZURE.md)
and [`docs/RUNBOOK.md`](docs/RUNBOOK.md) before changing a cloud resource.
Use a unique immutable image tag and verify `/health` and `/version` after
deployment. Do not copy credentials or subscription identifiers into source
control.

The following variables are supported by the current application or Docker
build:

| Name | Purpose | Default/notes |
|---|---|---|
| `VSL_MODEL_PATH` | Model file path | `train/vsl_cnn_pose_keras.h5` under the repository root |
| `VSL_DATA_DIR` | Landmark data directory | `data/anphabet` under the repository root |
| `VSL_MODEL_VERSION` | Model version returned by the API | `v1.0` |
| `GIT_SHA` | Source revision returned by `/version` | Docker build argument; `unknown` if unavailable |
| `BUILD_TIME` | Build time returned by `/version` | Docker build argument; service startup time if unset/invalid |
| `VSL_ALLOWED_ORIGINS` | Exact browser origins allowed by CORS | Implemented on `feature/US-025`; no default allowlist, no wildcard |

No application secret is required for local inference. Azure authentication
must use the operator's approved Azure identity. The current CI branch does not
push to a registry and requires no cloud credentials. The CORS origin is
configuration, not a secret; only configure a verified frontend origin.

## Smoke test, CORS, and rollback availability

These are **branch-only** until their PRs merge:

- **Smoke test (US-017):** `feature/US-017` provides
  `scripts/smoke_test.py`, which checks `/health`, the expected `/version`
  SHA, and `/predict` using a caller-supplied valid image. It has not been run
  against a deployed revision in this task. Usage and prerequisites are in the
  [US-017 contract](https://github.com/courseprojectICTU/Sign-Language-Classification/blob/feature/US-017/docs/api/US-017.md)
  on that branch.
- **CORS (US-025):** `feature/US-025` provides an exact-origin
  `VSL_ALLOWED_ORIGINS` allowlist and preflight support. There is no frontend
  source or verified Cloudflare Pages hostname in this repository. Do not
  invent an origin.
- **Rollback (US-031):** `feature/US-031` provides a dry-run-first Azure
  Container Apps script. No production rollback rehearsal or automatic
  rollback integration has been performed. See
  [the US-031 contract](https://github.com/courseprojectICTU/Sign-Language-Classification/blob/feature/US-031/docs/api/US-031.md)
  on that branch and
  [`docs/RUNBOOK.md`](docs/RUNBOOK.md).

## Operations and troubleshooting

Use [the runbook](docs/RUNBOOK.md) for CI failures, cold starts, unavailable
backend, CORS, smoke-test failures, rollback safeguards, and cloud-cost checks.
Do not claim production health, smoke-test success, or rollback readiness
without current runtime evidence.
=======
**Sign-Language-Classification-v1.0**

Sign-Language-Classification-v1.0 là một dự án phân loại ngôn ngữ ký hiệu sử dụng các kỹ thuật học sâu và xử lý ảnh. Dự án tập trung vào việc nhận diện các ký tự trong bảng chữ cái tiếng Việt (23 ký tự không dấu) từ cử chỉ tay và một số điểm mốc trên khuôn mặt. Dự án bao gồm các công đoạn từ thu thập dữ liệu, huấn luyện mô hình CNN (dựa trên ResNet50), đến ứng dụng thời gian thực qua webcam.

<img width="700" height="862" alt="image" src="https://github.com/user-attachments/assets/c5e5c51d-ed29-48ee-890c-a12198716ef2" />

CẤU TRÚC THƯ MỤC

<img width="571" height="155" alt="image" src="https://github.com/user-attachments/assets/8239c40a-7165-4473-add0-3bba081cfa41" />


CÁC THƯ MỤC CHÍNH

data/: Chứa dữ liệu thu thập được, bao gồm các thư mục con cho từng ký tự (a, b, ..., y), mỗi thư mục chứa 50 file CSV lưu trữ landmarks của tay và mặt.

train/: Chứa các tệp mã nguồn cho việc huấn luyện mô hình, mô hình đã được huấn luyện và biểu đồ trực quan  (train_cnn_pose_keras.ipynb , vsl_cnn_pose_keras.h5, training_plot_keras.png).

process_images/: Chứa tệp Jupyter Notebook cho việc thu thập dữ liệu (capture_and_process_images.ipynb) 

run_realtime.ipynb: ứng dụng thời gian thực.

YÊU CẦU HỆ THỐNG

Phần mềm:
Python 3.8 trở lên, 
TensorFlow 2.x, 
OpenCV, 
MediaPipe, 
Pandas, NumPy, Scikit-learn, 
Matplotlib, 
Jupyter Notebook (để chạy các tệp .ipynb)


Phần cứng:
Webcam (để thu thập dữ liệu và chạy ứng dụng thời gian thực), 
GPU (khuyến nghị để huấn luyện mô hình nhanh hơn)



CÀI ĐẶT

Clone repository:
git clone https://github.com/your-repo/Sign-Language-Classification-v1.0.git
cd Sign-Language-Classification-v1.0


CÀI ĐẶT CÁC GÓI

Đảm bảo bạn đã cài đặt Python 3.8+. Bạn có thể sử dụng virtualenv hoặc conda để tạo môi trường ảo.


pip install -r requirements.txt


Nếu không có tệp requirements.txt, bạn có thể cài đặt các gói thủ công:

pip install opencv-python mediapipe pandas numpy scikit-learn tensorflow matplotlib pillow




THIẾT LẬP ĐƯỜNG DẪN

Đảm bảo rằng đường dẫn đến thư mục dữ liệu (BASE_PATH) trong các tệp mã nguồn là chính xác.

Mặc định là D:\file\project\Sign-Language-Classification-v1.0\data\anphabet.

Bạn có thể cần thay đổi đường dẫn này cho phù hợp với hệ thống của mình.



SỬ DỤNG
1. Thu thập dữ liệu

Chạy tệp capture_and_process_images.ipynb để thu thập dữ liệu landmarks cho từng ký tự.

Mỗi ký tự sẽ được thu thập 50 mẫu, lưu dưới dạng file CSV trong thư mục tương ứng (data/anphabet/<ký tự>/).

Để thu thập dữ liệu cho một ký tự cụ thể, thay đổi tham số trong hàm capture_for_letter('a') (ví dụ: 'a', 'b', ...).


2. Huấn luyện mô hình


Chạy tệp train_cnn_pose_keras.ipynb để huấn luyện mô hình CNN dựa trên ResNet50.

Dữ liệu sẽ được tải từ thư mục data/anphabet, chuyển thành heatmap, và chia thành các tập train/val/test.

Mô hình sẽ được huấn luyện với hai giai đoạn:

Giai đoạn 1: Đóng băng ResNet50 và huấn luyện các lớp tùy chỉnh.

Giai đoạn 2: Fine-tune 10 tầng cuối của ResNet50.



Mô hình đã huấn luyện sẽ được lưu vào vsl_cnn_pose_keras.h5.


3. Chạy ứng dụng thời gian thực


Chạy tệp run_realtime.ipynb để khởi động ứng dụng nhận diện ngôn ngữ ký hiệu qua webcam.

Ứng dụng sẽ hiển thị hình ảnh từ webcam và dự đoán ký tự dựa trên cử chỉ tay và khuôn mặt.

Nhấn Ctrl+C để dừng ứng dụng.


DỮ LIỆU

<img width="1024" height="657" alt="image" src="https://github.com/user-attachments/assets/925910c4-0e91-4eed-8c0d-230a4b5e6924" />


Dữ liệu bao gồm landmarks của tay (21 điểm) và mặt (10 điểm cố định) cho 23 ký tự tiếng Việt không dấu.

Mỗi ký tự có 50 mẫu, được lưu dưới dạng file CSV trong thư mục data/anphabet/<ký tự>/.

Heatmap được tạo từ landmarks và sử dụng làm đầu vào cho mô hình CNN.


MÔ HÌNH

<img width="1024" height="1024" alt="ChatGPT Image 09_36_01 3 thg 8, 2025" src="https://github.com/user-attachments/assets/a905d33c-1b2b-4a81-bc4d-9d9c0b09f90c" />



Mô hình sử dụng ResNet50 làm backbone, với các lớp tùy chỉnh bao gồm GlobalAveragePooling2D và hai lớp Dense (256 units và 23 units).

Mô hình được huấn luyện với dữ liệu heatmap và đạt độ chính xác 90% trên tập kiểm tra (cập nhật sau khi huấn luyện).


KẾT QUẢ

<img width="1200" height="400" alt="training_plot_keras" src="https://github.com/user-attachments/assets/15a2d742-499b-4b94-af1e-58fde8d8bd2a" />



Mô hình đạt độ chính xác 90% trên tập kiểm tra (cập nhật sau khi huấn luyện).

Biểu đồ huấn luyện (loss và accuracy) được lưu trong training_plot_keras.png.


GÓP Ý PHÁT TRIỂN

Chúng tôi hoan nghênh mọi đóng góp và đề xuất cải tiến cho dự án. Vui lòng gửi pull request hoặc mở issue trên GitHub để chia sẻ ý tưởng hoặc báo lỗi.



---

## DỊCH VỤ WEB API & CONTAINER HÓA (US-005, US-006, US-038)

Hệ thống cung cấp dịch vụ HTTP API hiệu năng cao xây dựng trên FastAPI, phục vụ suy luận ký hiệu từ ảnh tải lên:

- **Khởi chạy API cục bộ:**
  ```powershell
  python -m uvicorn src.vsl.service:app --host 0.0.0.0 --port 8080 --reload
  ```
- **Khởi chạy qua Docker:**
  ```bash
  docker build --platform linux/amd64 -t vsl-api:latest .
  docker run -p 8080:8080 vsl-api:latest
  ```
- **Kiểm thử khói tự động (Smoke Test - US-017):**
  ```bash
  python scripts/smoke_test.py --url http://localhost:8080
  ```
- **Tài liệu triển khai & Runbook xử lý sự cố:** Xem chi tiết tại [docs/RUNBOOK.md](docs/RUNBOOK.md).