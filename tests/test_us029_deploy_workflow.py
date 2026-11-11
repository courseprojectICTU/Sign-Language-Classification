"""Contract tests for the US-029 Azure Container Apps deployment workflow."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    path = ROOT / relative_path
    assert path.is_file(), f"Missing US-029 file: {path}"
    return path.read_text(encoding="utf-8")


def test_deploy_workflow_uses_main_push_and_azure_oidc() -> None:
    workflow = _read(".github/workflows/deploy-backend.yml")

    assert re.search(r"(?m)^on:\s*$", workflow)
    assert re.search(r"(?ms)^on:\s*\n\s+push:\s*\n\s+branches:\s*\n\s+- main", workflow)
    assert re.search(r"(?m)^\s+id-token:\s*write\s*$", workflow)
    assert "azure/login@v2" in workflow
    assert all(
        f"vars.{name}" in workflow
        for name in (
            "AZURE_CLIENT_ID",
            "AZURE_TENANT_ID",
            "AZURE_SUBSCRIPTION_ID",
            "AZURE_RESOURCE_GROUP",
            "AZURE_CONTAINER_APP_NAME",
            "AZURE_ACR_NAME",
        )
    )
    assert "secrets." not in workflow
    assert "cancel-in-progress: false" in workflow


def test_workflow_builds_smokes_candidate_then_shifts_and_recovers_traffic() -> None:
    workflow = _read(".github/workflows/deploy-backend.yml")

    assert "docker build" in workflow
    assert "docker push" in workflow
    assert "GIT_SHA: ${{ github.sha }}" in workflow
    assert "--no-traffic" in workflow
    smoke_position = workflow.index("scripts/smoke_test.py")
    shift_position = workflow.index("az containerapp ingress traffic set")
    assert smoke_position < shift_position
    assert "--expected-sha" in workflow
    assert "--revision-weight" in workflow
    assert "PREVIOUS_REVISION" in workflow
    assert "Candidate health/version smoke test failed" in workflow
    assert "Automatic traffic rollback failed" in workflow
    assert "trap rollback_on_failure EXIT" in workflow
    assert "promotion_attempted=true" in workflow
    assert "promotion_verified=true" in workflow


def test_main_branch_oidc_subject_is_provisioned_for_staging_deployer() -> None:
    identity = _read("infra/identity.tf")
    variables = _read("infra/variables.tf")
    staging = _read("infra/environments/staging.tfvars")

    assert 'resource "azuread_application_federated_identity_credential" "github_main"' in identity
    assert "var.github_oidc_main_subject" in identity
    assert 'variable "github_oidc_main_subject"' in variables
    assert 'ref:refs/heads/main"' in staging
