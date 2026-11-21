#!/usr/bin/env bash
# ==============================================================================
# Script Rollback Cloud Run Service (US-031, BR-022)
# Chức năng: Tự động hoàn tác traffic về revision ổn định trước đó trong < 5 phút.
# ==============================================================================

set -euo pipefail

SERVICE_NAME="${1:-${SERVICE_NAME:-vsl-api}}"
REGION="${REGION:-asia-southeast1}"
PROJECT_ID="${PROJECT_ID:-}"

START_TIME=$(date +%s)

echo "=========================================================="
echo "🔄 BẮT ĐẦU QUY TRÌNH ROLLBACK BACKEND: ${SERVICE_NAME}"
echo "Region: ${REGION}"
echo "=========================================================="

GCLOUD_CMD="gcloud run"
if [ -n "${PROJECT_ID}" ]; then
  GCLOUD_CMD="gcloud --project=${PROJECT_ID} run"
fi

# 1. Lấy danh sách 2 revision gần nhất
echo "1. Đang truy vấn các revision của service..."
REVISIONS=$(${GCLOUD_CMD} revisions list \
  --service="${SERVICE_NAME}" \
  --region="${REGION}" \
  --format="value(metadata.name)" \
  --limit=2)

CURRENT_REV=$(echo "${REVISIONS}" | sed -n '1p')
PREV_REV=$(echo "${REVISIONS}" | sed -n '2p')

if [ -z "${PREV_REV}" ]; then
  echo "❌ LỖI: Không tìm thấy revision trước đó để rollback!"
  exit 1
fi

echo "   - Revision hiện tại (lỗi): ${CURRENT_REV}"
echo "   - Revision đích (ổn định): ${PREV_REV}"

# 2. Chuyển 100% traffic về revision trước đó
echo "2. Đang chuyển 100% traffic sang revision ${PREV_REV}..."
${GCLOUD_CMD} services update-traffic "${SERVICE_NAME}" \
  --region="${REGION}" \
  --to-revisions="${PREV_REV}=100"

# 3. Tính toán thời gian thực thi
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo "=========================================================="
echo "✅ ROLLBACK THÀNH CÔNG!"
echo "Traffic đã chuyển 100% về revision: ${PREV_REV}"
echo "Thời gian hoàn thành: ${DURATION} giây (Mục tiêu: < 300 giây / 5 phút)"
echo "=========================================================="

