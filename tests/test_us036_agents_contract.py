"""
Tests for US-036: Cập nhật AGENTS.md theo cấu trúc mới (AC-036-01, BR-024).

Verifies that AGENTS.md remains the accurate, up-to-date single source of truth
for agent memory, architecture, directory structure, operational traps, and progress.
"""

import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AGENTS_MD_PATH = PROJECT_ROOT / "AGENTS.md"


@pytest.fixture(scope="module")
def agents_content() -> str:
    assert AGENTS_MD_PATH.exists(), f"AGENTS.md does not exist at {AGENTS_MD_PATH}"
    return AGENTS_MD_PATH.read_text(encoding="utf-8")


def test_agents_md_exists_and_utf8():
    """Verify AGENTS.md exists and is readable as valid UTF-8 without decoding errors."""
    assert AGENTS_MD_PATH.is_file()
    raw = AGENTS_MD_PATH.read_bytes()
    decoded = raw.decode("utf-8")
    assert len(decoded) > 1000
    assert not decoded.startswith("\ufeff"), "AGENTS.md must not have UTF-8 BOM"


def test_agents_md_metadata_freshness(agents_content: str):
    """Verify AGENTS.md has current date (2026-11-21) and baseline commit (8d3f15e)."""
    assert "2026-11-21" in agents_content, "AGENTS.md last update date must be 2026-11-21"
    assert "8d3f15e" in agents_content, "AGENTS.md must reference baseline commit 8d3f15e"
    assert "v1.0.0" in agents_content, "AGENTS.md must reference release v1.0.0 on main"


def test_agents_md_reflects_new_architecture(agents_content: str):
    """AC-036-01: Verify AGENTS.md describes new architecture and not notebook-only."""
    assert "src/vsl/service.py" in agents_content
    assert "Cloudflare Pages" in agents_content
    assert "sign-language-classification.pages.dev" in agents_content
    assert "Azure Container Apps" in agents_content
    assert "cae-vsl-staging-std" in agents_content


def test_agents_md_directory_structure(agents_content: str):
    """Verify Section 3 includes recent files from US-032 and US-036."""
    assert "test_us032_frontend_rollback.py" in agents_content
    assert "docs/api/US-032.md" in agents_content
    assert "docs/reports/US-032-BAO-CAO-THUC-HIEN.md" in agents_content
    assert "test_us036_agents_contract.py" in agents_content
    assert "docs/api/US-036.md" in agents_content


def test_agents_md_contains_operational_traps(agents_content: str):
    """Verify Section 5 contains recently discovered operational traps."""
    # Trap: Azure Entra ID OIDC Subject claim with org/repo id
    assert "AADSTS700213" in agents_content or "courseprojectICTU@343123217" in agents_content
    # Trap: Windows Sandbox Python 3.12 DLL failure 0xC0000142 and Python 3.14 workaround
    assert "0xC0000142" in agents_content
    assert "py -3.14" in agents_content or "pythoncore-3.14" in agents_content
    # Trap: CORS preview domain allowlist
    assert "develop.sign-language-classification.pages.dev" in agents_content


def test_agents_md_progress_table(agents_content: str):
    """Verify Section 10 progress table records US-032 as merged."""
    pattern = r"\|\s*\*\*US-032\*\*\s*\|.*?\|\s*(?:PR\s*#57|PR\s*#58|MERGED).*?\|"
    assert re.search(
        pattern, agents_content, re.IGNORECASE | re.DOTALL
    ), "AGENTS.md Section 10 must record US-032 as merged into develop"
