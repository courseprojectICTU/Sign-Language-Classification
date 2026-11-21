"""Contract tests for US-028: Frontend CI/CD pipeline on Cloudflare Pages."""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "frontend.yml"
API_DOC_PATH = ROOT / "docs" / "api" / "US-028.md"


def _read_workflow_raw() -> str:
    assert WORKFLOW_PATH.is_file(), f"Missing expected workflow file at {WORKFLOW_PATH}"
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def _read_workflow() -> dict:
    content = _read_workflow_raw()
    data = yaml.safe_load(content)
    assert isinstance(data, dict), "frontend.yml must parse as a valid YAML mapping"
    return data


def test_us028_api_doc_follows_17_section_template_and_is_ready() -> None:
    """Kiểm tra hợp đồng tài liệu US-028.md đạt ANALYSIS_READY và đủ 17 mục."""
    assert API_DOC_PATH.is_file(), f"Missing API doc at {API_DOC_PATH}"
    content = API_DOC_PATH.read_text(encoding="utf-8")

    assert "ANALYSIS_READY" in content
    for section_num in range(1, 18):
        assert re.search(
            rf"(?m)^## {section_num}\.\s+", content
        ), f"Missing section ## {section_num}. in docs/api/US-028.md"

    for token in ("AC-028-01", "AC-028-02", "TSK-053", "TSK-054", "BR-020", "BR-017"):
        assert token in content, f"Token {token} must be documented in docs/api/US-028.md"


def test_frontend_workflow_file_exists() -> None:
    """TSK-053: File .github/workflows/frontend.yml tồn tại và có tên định danh chuẩn."""
    workflow = _read_workflow()
    name = workflow.get("name", "")
    assert "Frontend" in name or "Pages" in name, f"Unexpected workflow name: {name}"


def test_ac_028_01_and_tsk_053_pr_and_push_triggers_with_path_filtering() -> None:
    """AC-028-01 & TSK-053: Triggers chỉ kích hoạt khi sửa đổi web/** hoặc workflow frontend."""
    workflow = _read_workflow()
    triggers = workflow.get("on") or workflow.get(True) or {}

    # 1. Pull Request Trigger
    assert "pull_request" in triggers, "Workflow phải có trigger pull_request"
    pr_config = triggers["pull_request"]
    pr_branches = pr_config.get("branches", [])
    assert "develop" in pr_branches, "pull_request phải kiểm tra nhánh develop"
    assert "main" in pr_branches, "pull_request phải kiểm tra nhánh main"

    pr_paths = pr_config.get("paths", [])
    assert "web/**" in pr_paths, "pull_request phải lọc đường dẫn web/**"
    assert (
        ".github/workflows/frontend.yml" in pr_paths
    ), "pull_request cần trigger khi chính workflow frontend.yml được cập nhật"

    # 2. Push Trigger (Staging / Production promotion)
    assert "push" in triggers, "Workflow phải có trigger push"
    push_config = triggers["push"]
    push_branches = push_config.get("branches", [])
    assert "develop" in push_branches, "push trigger phải hỗ trợ develop (staging)"
    assert "main" in push_branches, "push trigger phải hỗ trợ main (production)"

    push_paths = push_config.get("paths", [])
    assert "web/**" in push_paths, "push trigger chỉ được lọc đường dẫn web/**"


def test_ac_028_02_path_filtering_excludes_backend_and_infra_paths() -> None:
    """AC-028-02: Pipeline không dùng wildcard '*' và không bao quát các thư mục ngoài frontend."""
    workflow = _read_workflow()
    triggers = workflow.get("on") or workflow.get(True) or {}

    for event_name in ("pull_request", "push"):
        paths = triggers.get(event_name, {}).get("paths", [])
        assert "*" not in paths, f"{event_name} không được dùng wildcard '*' đơn thuần"
        assert "**" not in paths, f"{event_name} không được dùng wildcard '**' toàn repo"
        # Không được chứa các thư mục ngoài frontend
        for excluded in ("src/**", "infra/**", "docs/**", "tests/**", "scripts/**"):
            assert (
                excluded not in paths
            ), f"{event_name} không được kích hoạt khi sửa {excluded} (vi phạm AC-028-02)"


def test_frontend_workflow_permissions_and_concurrency() -> None:
    """Bảo mật và concurrency: cấp quyền tối thiểu và hủy job thừa khi PR có commit mới."""
    workflow = _read_workflow()

    permissions = workflow.get("permissions", {})
    assert permissions.get("contents") == "read", "permissions.contents phải là read"
    assert (
        permissions.get("pull-requests") == "write"
    ), "permissions.pull-requests phải là write để comment vào PR"

    concurrency = workflow.get("concurrency", {})
    assert "group" in concurrency, "Workflow phải khai báo concurrency group"
    assert concurrency.get(
        "cancel-in-progress"
    ) is True or "${{ github.event_name == 'pull_request' }}" in str(
        concurrency.get("cancel-in-progress")
    ), "concurrency phải cancel-in-progress khi có commit mới trên PR"


def test_tsk_054_wrangler_deployment_and_pr_comment_action() -> None:
    """TSK-054 & BR-020: Dùng wrangler-action với token bảo mật và comment URL xem trước vào PR."""
    raw_content = _read_workflow_raw()
    workflow = _read_workflow()

    # Xác thực Secret không bị hard-code (BR-020)
    assert "secrets.CLOUDFLARE_API_TOKEN" in raw_content
    assert "secrets.CLOUDFLARE_ACCOUNT_ID" in raw_content
    assert "sign-language-classification" in raw_content

    # Kiểm tra job deploy
    jobs = workflow.get("jobs", {})
    assert len(jobs) >= 1, "Workflow phải có ít nhất 1 job triển khai"
    job_key = next(iter(jobs))
    job = jobs[job_key]
    steps = job.get("steps", [])

    # 1. Bước wrangler pages deploy
    wrangler_step = next(
        (s for s in steps if "wrangler-action" in str(s.get("uses", ""))),
        None,
    )
    assert wrangler_step is not None, "Thiếu bước cloudflare/wrangler-action trong workflow"
    command = wrangler_step.get("with", {}).get("command", "")
    assert "pages deploy web" in command or "pages deploy" in command
    assert "--project-name=" in command

    # 2. Bước comment PR chứa marker HTML định danh
    comment_step = next(
        (
            s
            for s in steps
            if "github-script" in str(s.get("uses", ""))
            or "comment" in str(s.get("name", "")).lower()
        ),
        None,
    )
    assert comment_step is not None, "Thiếu bước comment URL preview vào Pull Request (TSK-054)"
    assert (
        "vsl-cloudflare-pages-preview" in raw_content
    ), "Phải có marker nhận diện comment để update tránh spam PR"
