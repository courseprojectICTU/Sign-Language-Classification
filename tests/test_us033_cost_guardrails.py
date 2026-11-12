"""Contract tests for US-033 Azure billing budget, MFA, and cost guardrails."""

import pathlib
import re
import shutil
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
INFRA = ROOT / "infra"
RUNBOOK_PATH = ROOT / "docs" / "RUNBOOK.md"
INFRA_README_PATH = INFRA / "README.md"
API_DOC_PATH = ROOT / "docs" / "api" / "US-033.md"


def _read(path: pathlib.Path) -> str:
    assert path.is_file(), f"Missing file required for US-033: {path}"
    return path.read_text(encoding="utf-8")


def test_us033_contract_doc_exists_with_17_sections() -> None:
    content = _read(API_DOC_PATH)
    for section_number in range(1, 18):
        assert re.search(
            rf"(?m)^##\s+{section_number}\.\s+", content
        ), f"docs/api/US-033.md missing section {section_number}"
    assert "ANALYSIS_READY" in content
    assert "azurerm_consumption_budget_subscription" in content


def test_us033_terraform_declares_azure_budget_with_1_and_5_usd_thresholds() -> None:
    budget_tf = _read(INFRA / "budget.tf")
    variables_tf = _read(INFRA / "variables.tf")
    outputs_tf = _read(INFRA / "outputs.tf")

    assert re.search(
        r'resource\s+"azurerm_consumption_budget_subscription"\s+"monthly"\s*\{',
        budget_tf,
    )
    assert re.search(r"count\s*=\s*var\.enable_billing_budget\s*\?\s*1\s*:\s*0", budget_tf)
    assert re.search(r"amount\s*=\s*5\b", budget_tf)
    assert re.search(r'time_grain\s*=\s*"Monthly"', budget_tf)
    assert re.search(r"threshold\s*=\s*20\b", budget_tf)
    assert re.search(r"threshold\s*=\s*100\b", budget_tf)
    assert re.search(r'threshold_type\s*=\s*"Actual"', budget_tf)
    assert re.search(r'contact_roles\s*=\s*\["Owner"\]', budget_tf)
    assert "var.budget_alert_emails" in budget_tf
    assert "ignore_changes" in budget_tf
    assert "time_period" in budget_tf

    for var_name in ("enable_billing_budget", "budget_start_date", "budget_alert_emails"):
        assert re.search(rf'variable\s+"{var_name}"\s*\{{', variables_tf)
    assert re.search(r'output\s+"billing_budget_id"\s*\{', outputs_tf)


def test_us033_removes_legacy_google_cloud_budget_and_runbook_files() -> None:
    assert not (INFRA / "billing-budget").exists()
    assert not (ROOT / "docs" / "runbook").exists()

    all_infra_files = [
        path
        for pattern in ("*.tf", "*.hcl")
        for path in INFRA.rglob(pattern)
        if ".terraform" not in path.parts
    ]
    assert all_infra_files
    for path in all_infra_files:
        text = path.read_text(encoding="utf-8")
        assert "google_billing_budget" not in text, path
        assert "hashicorp/google" not in text, path


def test_us033_runbook_covers_azure_budget_mfa_prohibited_services_and_alert_response() -> None:
    runbook = _read(RUNBOOK_PATH)
    infra_readme = _read(INFRA_README_PATH)

    # Required Azure cost & sponsorship references
    assert "Azure Cost Management" in runbook
    assert "microsoftazuresponsorships.com" in runbook
    assert "$1" in runbook and "$5" in runbook
    assert "20%" in runbook and "100%" in runbook
    assert "azurerm_consumption_budget_subscription" in runbook
    assert "Microsoft.Consumption" in runbook
    assert "Microsoft.Consumption" in infra_readme

    # Required Entra ID MFA coverage
    assert "Entra ID" in runbook
    assert "MFA" in runbook
    assert "US-019" in runbook

    # Prohibited and conditional Azure services (BR-016)
    for required_term in (
        "GPU",
        "AKS",
        "Azure SQL",
        "NAT Gateway",
        "minReplicas",
        "BR-016",
    ):
        assert required_term in runbook, f"Missing {required_term!r} in docs/RUNBOOK.md"

    # Must not prescribe legacy GCP tooling in operational guidance
    for legacy_gcp in ("google_billing_budget", "Google Workspace", "Artifact Registry", "GKE"):
        assert legacy_gcp not in runbook, f"Legacy GCP term {legacy_gcp!r} found in RUNBOOK.md"


def test_us033_terraform_fmt_and_validate_when_initialized() -> None:
    terraform = shutil.which("terraform")
    if terraform is None:
        return

    fmt_result = subprocess.run(
        [terraform, "fmt", "-check", "-recursive", "-diff", str(INFRA)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert fmt_result.returncode == 0, fmt_result.stdout + fmt_result.stderr

    if (INFRA / ".terraform").is_dir():
        validate_result = subprocess.run(
            [terraform, f"-chdir={INFRA}", "validate"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert validate_result.returncode == 0, validate_result.stdout + validate_result.stderr
