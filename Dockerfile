# syntax=docker/dockerfile:1.7
# ==============================================================================
# Dockerfile cho Sign Language Classification API (US-038, BR-025, EPC-03)
# 
# Tuân thủ:
# - BR-025: Reproducible Image Build (multi-stage, digest ghim cố định, --platform linux/amd64).
# - Tối ưu layer cache: copy requirements.txt trước, mã nguồn copy sau.
# - Image gầy: Runtime stage chỉ chứa virtualenv và dependencies tối thiểu, không compiler.
# ==============================================================================

# =========================
# Stage 1: Builder
# =========================
FROM --platform=linux/amd64 python:3.12.7-slim-bookworm@sha256:60d9996b6a8a3689d36db740b49f4327be3be09a21122bd02fb8895abb38b50d AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /build

# Cài đặt phụ thuộc biên dịch cần thiết cho OpenCV/C/C++ packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv

# Tối ưu layer cache: copy requirements trước
COPY requirements.txt ./

RUN pip install --upgrade pip setuptools wheel && \
    pip install --only-binary=:all: -r requirements.txt


# =========================
# Stage 2: Runtime
# =========================
FROM --platform=linux/amd64 python:3.12.7-slim-bookworm@sha256:60d9996b6a8a3689d36db740b49f4327be3be09a21122bd02fb8895abb38b50d AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8080

WORKDIR /app

# Cài đặt thư viện runtime dùng chung cho MediaPipe và OpenCV (libGL, glib, libSM...)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Sao chép virtualenv từ stage builder
COPY --from=builder /opt/venv /opt/venv

# Sao chép mã nguồn ứng dụng và model đã huấn luyện
COPY src ./src
COPY train/vsl_cnn_pose_keras.h5 ./train/vsl_cnn_pose_keras.h5
COPY requirements.txt ./requirements.txt
COPY README.md ./README.md

# Tạo user không đặc quyền để tăng cường bảo mật container
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

CMD ["uvicorn", "src.vsl.service:app", "--host", "0.0.0.0", "--port", "8080"]

