"""Tests for US-018 Azure Terraform scaffolding and remote state."""

import pathlib
import re


ROOT = pathlib.Path(__file__).resolve().parents[1]
INFRA = ROOT / "infra"


def _read(relative_path):
    path = INFRA / relative_path
    assert path.is_file(), f"Missing Terraform configuration: {path}"
    return path.read_text(encoding="utf-8")


def test_tsk_030_uses_azurerm_and_separates_environment_inputs():
    versions = _read("versions.tf")
    provider = _read("provider.tf")
    variables = _read("variables.tf")

    assert re.search(
        r'azurerm\s*=\s*\{[^}]*source\s*=\s*"hashicorp/azurerm"',
        versions,
        re.DOTALL,
    )
    assert re.search(r'provider\s+"azurerm"\s*\{', provider)
    assert re.search(r"subscription_id\s*=\s*var\.subscription_id", provider)

    for variable in ("subscription_id", "resource_group_name", "location", "environment"):
        assert re.search(rf'variable\s+"{variable}"', variables)

    for environment in ("staging", "production"):
        tfvars = _read(f"environments/{environment}.tfvars")
        assert re.search(rf'environment\s*=\s*"{environment}"', tfvars)
        for field in ("subscription_id", "resource_group_name", "location"):
            assert re.search(rf'^\s*{field}\s*=\s*"[^"]+"\s*$', tfvars, re.MULTILINE)


def test_tsk_031_uses_azure_blob_backend_and_documents_state_locking():
    backend = _read("backend.tf")
    gitignore = _read(".gitignore")
    readme = _read("README.md")

    assert re.search(r'backend\s+"azurerm"\s*\{', backend)
    assert re.search(r'^\s*\.terraform/?\s*$', gitignore, re.MULTILINE)
    assert re.search(r'^\s*\*\.tfstate\*?\s*$', gitignore, re.MULTILINE)
    assert "use_azuread_auth=true" in readme
    assert "staging.tfstate" in readme
    assert "production.tfstate" in readme
    assert "lease" in readme.lower()
    assert "terraform init" in readme
    assert "terraform plan" in readme


def test_azure_state_bootstrap_is_private_versioned_and_protected():
    bootstrap = INFRA / "bootstrap-azure"
    main = bootstrap / "main.tf"
    variables = bootstrap / "variables.tf"
    readme = bootstrap / "README.md"

    assert main.is_file(), f"Missing Azure bootstrap configuration: {main}"
    assert variables.is_file(), f"Missing Azure bootstrap variables: {variables}"
    assert readme.is_file(), f"Missing Azure bootstrap instructions: {readme}"

    config = main.read_text(encoding="utf-8")
    variable_config = variables.read_text(encoding="utf-8")
    instructions = readme.read_text(encoding="utf-8")

    assert re.search(r'resource\s+"azurerm_storage_account"\s+"terraform_state"\s*\{', config)
    assert re.search(r'resource\s+"azurerm_storage_container"\s+"terraform_state"\s*\{', config)
    assert re.search(r'container_access_type\s*=\s*"private"', config)
    assert re.search(r'allow_nested_items_to_be_public\s*=\s*false', config)
    assert re.search(r'https_traffic_only_enabled\s*=\s*true', config)
    assert re.search(r'min_tls_version\s*=\s*"TLS1_2"', config)
    assert re.search(r'versioning\s*\{\s*enabled\s*=\s*true\s*\}', config, re.DOTALL)
    assert len(re.findall(r'prevent_destroy\s*=\s*true', config)) >= 2
    for variable in (
        "subscription_id",
        "resource_group_name",
        "location",
        "storage_account_name",
        "container_name",
    ):
        assert re.search(rf'variable\s+"{variable}"', variable_config)
    assert "terraform plan" in instructions
    assert "terraform apply" in instructions
    assert "local state" in instructions.lower()


def test_terraform_configuration_no_longer_declares_google_cloud_resources():
    terraform_files = [
        path
        for path in INFRA.rglob("*.tf")
        if ".terraform" not in path.parts
    ]

    assert terraform_files
    for path in terraform_files:
        content = path.read_text(encoding="utf-8")
        assert 'hashicorp/google' not in content, path
        assert 'backend "gcs"' not in content, path
        assert 'google_storage_bucket' not in content, path
