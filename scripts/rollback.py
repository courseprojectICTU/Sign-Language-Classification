#!/usr/bin/env python3
"""Script Rollback Cloud Run Service cross-platform (US-031, BR-022).

Chức năng:
- Liệt kê các revision của Cloud Run service qua gcloud CLI.
- Chuyển 100% traffic về revision ổn định liền trước trong < 5 phút.
- Ghi lại thời gian hoàn thành.

Sử dụng:
    python scripts/rollback.py --service vsl-api --region asia-southeast1
"""

import argparse
import subprocess
import sys
import time

# Bảo đảm hiển thị tiếng Việt an toàn trên console Windows không bị UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def main():
    parser = argparse.ArgumentParser(description="Cloud Run Service Rollback (US-031)")
    parser.add_argument("--service", default="vsl-api", help="Tên Cloud Run service")
    parser.add_argument("--region", default="asia-southeast1", help="GCP Region")
    parser.add_argument("--project", default="", help="GCP Project ID (tùy chọn)")
    parser.add_argument("--target-rev", default="", help="Revision chỉ định để rollback (mặc định lấy revision trước)")
    args = parser.parse_args()

    start_time = time.time()
    print("=" * 60)
    print(f"🔄 BẮT ĐẦU QUY TRÌNH ROLLBACK BACKEND: {args.service}")
    print(f"Region: {args.region}")
    print("=" * 60)

    project_arg = [f"--project={args.project}"] if args.project else []

    target_revision = args.target_rev
    if not target_revision:
        print("1. Đang truy vấn danh sách revision...")
        cmd_list = [
            "gcloud", "run", "revisions", "list",
            f"--service={args.service}",
            f"--region={args.region}",
            "--format=value(metadata.name)",
            "--limit=2",
        ] + project_arg

        try:
            res = subprocess.run(cmd_list, capture_output=True, text=True, check=True)
            revisions = [line.strip() for line in res.stdout.strip().splitlines() if line.strip()]
            if len(revisions) < 2:
                print(f"❌ LỖI: Không tìm thấy đủ 2 revision để rollback (tìm thấy: {len(revisions)}).")
                sys.exit(1)
            current_rev, target_revision = revisions[0], revisions[1]
            print(f"   - Revision hiện tại: {current_rev}")
            print(f"   - Revision ổn định trước đó: {target_revision}")
        except subprocess.CalledProcessError as exc:
            print(f"❌ LỖI khi gọi gcloud revisions list: {exc.stderr}")
            sys.exit(1)

    print(f"2. Đang chuyển 100% traffic sang revision {target_revision}...")
    cmd_traffic = [
        "gcloud", "run", "services", "update-traffic", args.service,
        f"--region={args.region}",
        f"--to-revisions={target_revision}=100",
    ] + project_arg

    try:
        subprocess.run(cmd_traffic, check=True)
    except subprocess.CalledProcessError as exc:
        print(f"❌ LỖI khi cập nhật traffic: {exc}")
        sys.exit(1)

    duration = time.time() - start_time
    print("=" * 60)
    print("✅ ROLLBACK THÀNH CÔNG!")
    print(f"Traffic đã chuyển 100% về revision: {target_revision}")
    print(f"Thời gian hoàn thành: {duration:.1f} giây (Mục tiêu: < 300 giây / 5 phút)")
    print("=" * 60)


if __name__ == "__main__":
    main()
