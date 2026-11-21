"""Contract and validation tests for US-032: Frontend rollback to previous deployment."""

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "api" / "US-032.md"
RUNBOOK_PATH = ROOT / "docs" / "RUNBOOK.md"


def test_us032_design_doc_exists_and_is_analysis_ready():
    """Verify that docs/api/US-032.md adheres to the 17-section template and is ANALYSIS_READY."""
    assert DOC_PATH.is_file(), f"Missing design document at {DOC_PATH}"
    content = DOC_PATH.read_text(encoding="utf-8")

    assert "ANALYSIS_READY" in content, "US-032 document must be in ANALYSIS_READY status"

    for section_idx in range(1, 18):
        pattern = rf"(?m)^## {section_idx}\.\s+"
        assert re.search(
            pattern, content
        ), f"Missing section ## {section_idx}. in docs/api/US-032.md"

    for required_token in (
        "AC-032-01",
        "TSK-060",
        "BR-022",
        "EPC-08",
        "Cloudflare Pages",
        "sign-language-classification",
    ):
        assert (
            required_token in content
        ), f"Missing required token '{required_token}' in docs/api/US-032.md"


def test_runbook_contains_frontend_rollback_section():
    """Verify that docs/RUNBOOK.md includes Section 5.3 for Cloudflare Pages rollback."""
    assert RUNBOOK_PATH.is_file(), f"Missing runbook at {RUNBOOK_PATH}"
    content = RUNBOOK_PATH.read_text(encoding="utf-8")

    # Verify presence of section 5.3
    assert (
        "5.3" in content and "Rollback" in content and "Cloudflare" in content
    ), "RUNBOOK.md must contain Section 5.3 for Cloudflare Pages rollback"

    # Verify procedure steps: Dashboard and CLI
    assert (
        "sign-language-classification" in content
    ), "RUNBOOK.md must reference project sign-language-classification"
    assert "Deployments" in content, "RUNBOOK.md must guide operator to inspect the Deployments tab"
    assert (
        "Rollback to this deployment" in content or "Rollback" in content
    ), "RUNBOOK.md must document the rollback action"

    # Verify zero-build instant recovery requirement (AC-032-01)
    assert re.search(
        r"(không cần build|zero-build|không phải build|without rebuilding)",
        content,
        re.IGNORECASE,
    ), "RUNBOOK.md must highlight zero-build instant recovery"

    # Verify BR-022 Rehearsed Rollback requirement
    assert (
        "BR-022" in content or "Rehearsal" in content or "diễn tập" in content.lower()
    ), "RUNBOOK.md must document rehearsal evidence under BR-022"
