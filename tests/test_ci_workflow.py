"""Contract tests for the GitHub Actions pull-request CI workflow."""

import re
from pathlib import Path

WORKFLOW_PATH = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"


def _workflow_text() -> str:
    assert WORKFLOW_PATH.is_file(), "Missing .github/workflows/ci.yml"
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def test_ci_runs_on_pull_requests() -> None:
    content = _workflow_text()

    assert re.search(r"(?m)^on:\s*$", content)
    assert re.search(r"(?m)^\s+pull_request:\s*$", content)


def test_ci_installs_cached_python_dependencies_and_runs_quality_gates() -> None:
    content = _workflow_text()

    assert "actions/setup-python@" in content
    assert re.search(r"(?m)^\s+cache:\s*[\"']?pip", content)
    assert re.search(r"(?m)^\s+run:.*ruff check", content) or "ruff check" in content
    assert "black --check" in content
    assert "pytest" in content


def test_ci_installs_playwright_browsers_for_browser_acceptance_tests() -> None:
    content = _workflow_text()

    assert "python -m playwright install --with-deps chromium firefox" in content


def test_ci_builds_without_pushing_and_uses_github_actions_cache() -> None:
    content = _workflow_text()

    assert "docker/build-push-action@" in content
    assert re.search(r"(?m)^\s+push:\s*false\s*$", content)
    assert "cache-from: type=gha" in content
    assert "cache-to: type=gha" in content


def test_ci_records_docker_build_duration_and_image_size() -> None:
    content = _workflow_text()

    assert "BUILD_START" in content
    assert "docker image inspect" in content
    assert "IMAGE_SIZE" in content
    assert "BUILD_DURATION" in content or "DURATION" in content


def test_ci_playwright_install_has_apt_resilience_and_timeouts() -> None:
    content = _workflow_text()

    assert "timeout-minutes:" in content
    assert "~/.cache/ms-playwright" in content
    assert 'Acquire::ForceIPv4 "true"' in content
    assert "/etc/apt/apt-mirrors.txt" in content
    assert "azure.archive.ubuntu.com/ubuntu" in content
    assert "archive.ubuntu.com/ubuntu" in content
    assert "timeout " in content
