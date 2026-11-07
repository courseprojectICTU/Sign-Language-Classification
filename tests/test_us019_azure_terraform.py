"""Tests for US-019 Azure registry, RBAC, and GitHub OIDC configuration."""

import pathlib
import re


ROOT = pathlib.Path(__file__).resolve().parents[1]
INFRA = ROOT / "infra"


def _read(relative_path):
    path = INFRA / relative_path
    assert path.is_file(), f"Missing Terraform configuration: {path}"
    return path.read_text(encoding="utf-8")


def _terraform_sources():
    paths = sorted(
        path
        for path in INFRA.rglob("*.tf")
        if ".terraform" not in path.parts
    )
    assert paths, "No Terraform configuration found"
    return "\n".join(path.read_text(encoding="utf-8") for path in paths)


def _role_assignment_body(source, name):
    match = re.search(
        rf'resource\s+"azurerm_role_assignment"\s+"{re.escape(name)}"\s*\{{([^}}]*)\}}',
        source,
        re.DOTALL,
    )
    assert match, f"Missing role assignment: {name}"
    return match.group(1)


def test_tsk_032_adopts_existing_registry_and_configures_three_tag_cleanup():
    registry = _read("registry.tf")
    readme = _read("README.md")
    staging = _read("environments/staging.tfvars")

    assert re.search(
        r'resource\s+"azurerm_container_registry"\s+"vsl"\s*\{',
        registry,
    )
    assert "acr_name" in registry
    assert re.search(r'\bacr_name\s*=\s*"vslacr3795"', staging)
    assert re.search(r'\bsku\s*=\s*"Basic"', registry)
    assert re.search(r"\badmin_enabled\s*=\s*true", registry)
    assert "prevent_destroy = true" in registry
    assert "terraform -chdir=infra import" in readme
    assert "azurerm_container_registry.vsl" in readme

    assert re.search(
        r'resource\s+"azurerm_container_registry_task"\s+"cleanup"\s*\{',
        registry,
    )
    for required in ("timer_trigger", "schedule", "acr purge", "--filter", "vsl-api", "--ago 0d", "--keep 3"):
        assert required in registry
    assert re.search(
        r'resource\s+"azurerm_user_assigned_identity"\s+"registry_cleanup"\s*\{',
        registry,
    )

    assignment = _role_assignment_body(registry, "cleanup_delete")
    assert re.search(r'role_definition_name\s*=\s*"AcrDelete"', assignment)
    assert re.search(
        r"scope\s*=\s*azurerm_container_registry\.vsl\.id",
        assignment,
    )


def test_tsk_033_limits_deployment_roles_to_registry_and_container_app():
    identity = _read("identity.tf")

    push = _role_assignment_body(identity, "deployment_push")
    assert re.search(r'role_definition_name\s*=\s*"AcrPush"', push)
    assert re.search(
        r"scope\s*=\s*azurerm_container_registry\.vsl\.id",
        push,
    )

    deploy = _role_assignment_body(identity, "deployment_app")
    assert re.search(
        r'role_definition_name\s*=\s*"Container Apps Contributor"',
        deploy,
    )
    assert re.search(
        r"scope\s*=\s*data\.azurerm_container_app\.vsl_api\.id",
        deploy,
    )

    roles = re.findall(r'role_definition_name\s*=\s*"([^"]+)"', identity)
    assert "Owner" not in roles
    assert "Contributor" not in roles
    assert not re.search(
        r"scope\s*=\s*data\.azurerm_subscription|scope\s*=\s*var\.subscription_id",
        identity,
    )


def test_tsk_034_creates_github_federation_without_service_principal_password():
    versions = _read("versions.tf")
    identity = _read("identity.tf")
    outputs = _read("outputs.tf")
    staging = _read("environments/staging.tfvars")
    sources = _terraform_sources()

    assert re.search(
        r'azuread\s*=\s*\{[^}]*source\s*=\s*"hashicorp/azuread"',
        versions,
        re.DOTALL,
    )
    assert re.search(r'resource\s+"azuread_application"\s+"github_deploy"\s*\{', identity)
    assert re.search(r'resource\s+"azuread_service_principal"\s+"github_deploy"\s*\{', identity)
    assert re.search(
        r'resource\s+"azuread_application_federated_identity_credential"\s+"github_develop"\s*\{',
        identity,
    )
    assert re.search(
        r'issuer\s*=\s*"https://token\.actions\.githubusercontent\.com"',
        identity,
    )
    assert '"api://AzureADTokenExchange"' in identity
    assert re.search(r"subject\s*=\s*var\.github_oidc_subject", identity)
    assert (
        'github_oidc_subject = '
        '"repo:courseprojectICTU/Sign-Language-Classification:ref:refs/heads/develop"'
    ) in staging
    for output_name in (
        "github_oidc_client_id",
        "github_oidc_tenant_id",
        "github_oidc_subscription_id",
    ):
        assert re.search(rf'output\s+"{output_name}"\s*\{{', outputs)
    assert "azuread_service_principal_password" not in sources
    assert not re.search(r'resource\s+"azuread_application_password"', sources)


def test_oidc_smoke_workflow_uses_dispatch_and_github_oidc_without_secrets():
    path = ROOT / ".github" / "workflows" / "azure-oidc-smoke.yml"
    assert path.is_file(), f"Missing GitHub OIDC smoke workflow: {path}"
    workflow = path.read_text(encoding="utf-8")

    assert re.search(r"(?m)^\s*workflow_dispatch\s*:", workflow)
    assert re.search(r"(?m)^\s*id-token:\s*write\s*$", workflow)
    assert "azure/login@v2" in workflow
    for name in ("AZURE_CLIENT_ID", "AZURE_TENANT_ID", "AZURE_SUBSCRIPTION_ID"):
        assert f"vars.{name}" in workflow
    assert "secrets." not in workflow
