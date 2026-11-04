# Base image Linux x86_64 tuân thủ BR-005 và BR-025
FROM --platform=linux/amd64 python:3.12-slim

# Thiết lập môi trường không tương tác cho apt
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Cài đặt các thư viện hệ thống cần thiết cho OpenCV, MediaPipe và healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Thiết lập thư mục làm việc chuẩn
WORKDIR /app

# Tối ưu hóa Docker layer caching (BR-025): Cài đặt dependencies trước khi copy mã nguồn
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Hỗ trợ build arguments truy vết commit bất biến theo BR-009
ARG GIT_SHA=unknown
ARG BUILD_TIME=""
ENV GIT_SHA=${GIT_SHA}
ENV BUILD_TIME=${BUILD_TIME}

# Sao chép mã nguồn dịch vụ và mô hình đã huấn luyện
COPY src/ /app/src/
COPY train/vsl_cnn_pose_keras.h5 /app/train/vsl_cnn_pose_keras.h5

# Mở cổng phục vụ theo chuẩn Cloud Run
EXPOSE 8080

# Cấu hình kiểm tra sức khỏe tự động qua endpoint /health theo BR-011
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Lệnh khởi chạy dịch vụ FastAPI qua Uvicorn
CMD ["uvicorn", "src.vsl.service:app", "--host", "0.0.0.0", "--port", "8080"]
