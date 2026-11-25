"""Contract tests for the US-030 production approval gate."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    path = ROOT / relative_path
    assert path.is_file(), f"Missing US-030 file: {path}"
    return path.read_text(encoding="utf-8")


def _job_block(workflow: str, job_name: str) -> str:
    match = re.search(
        rf"(?ms)^  {re.escape(job_name)}:\n(?P<body>.*?)(?=^  [A-Za-z0-9_-]+:\n|\Z)",
        workflow,
    )
    assert match is not None, f"Missing workflow job: {job_name}"
    return match.group("body")


def test_production_job_waits_for_staging_and_production_environment() -> None:
    workflow = _read(".github/workflows/deploy-backend.yml")
    production_job = _job_block(workflow, "deploy")

    assert re.search(r"(?m)^    needs:\s*verify-staging\s*$", production_job)
    assert re.search(r"(?m)^    environment:\s*$", production_job)
    assert re.search(
        r"(?m)^      name:\s*\$\{\{\s*github\.ref_name.*'production'",
        production_job,
    )
    assert production_job.index("environment:") < production_job.index("steps:")


def test_staging_preflight_requires_success_for_the_exact_main_sha() -> None:
    workflow = _read(".github/workflows/deploy-backend.yml")
    staging_job = _job_block(workflow, "verify-staging")

    assert re.search(r"(?m)^    actions:\s*read\s*$", staging_job)
    assert "GITHUB_SHA" in staging_job
    assert "branch=develop" in staging_job
    assert "head_sha" in staging_job
    assert "status=success" in staging_job
    assert "workflow_runs" in staging_job
    assert re.search(r"(?m)^\s+exit 1\s*$", staging_job)


def test_staging_deploy_is_not_blocked_by_production_approval_preflight() -> None:
    workflow = _read(".github/workflows/deploy-backend.yml")
    staging_job = _job_block(workflow, "verify-staging")

    assert "GITHUB_REF_NAME" in staging_job
    assert "main" in staging_job
    assert "develop" in workflow
