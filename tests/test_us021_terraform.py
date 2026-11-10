"""Contract tests for the US-021 staging and production Container Apps."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INFRA = ROOT / "infra"
MODULE = INFRA / "modules" / "container_app"
ENVIRONMENTS = INFRA / "environments"


def _read(path: Path) -> str:
    assert path.is_file(), f"Missing US-021 configuration: {path}"
    return path.read_text(encoding="utf-8")


def test_container_app_module_uses_shared_acr_and_managed_identity() -> None:
    main = _read(MODULE / "main.tf")

    assert re.search(r'data\s+"azurerm_container_registry"\s+"shared"\s*\{', main)
    assert re.search(r'resource\s+"azurerm_container_app_environment"\s+"this"\s*\{', main)
    assert re.search(r'resource\s+"azurerm_container_app"\s+"this"\s*\{', main)
    assert re.search(r'resource\s+"azurerm_user_assigned_identity"\s+"acr_pull"\s*\{', main)
    assert re.search(r'resource\s+"azurerm_role_assignment"\s+"acr_pull"\s*\{', main)
    assert re.search(r'role_definition_name\s*=\s*"AcrPull"', main)
    assert re.search(
        r"registry\s*\{[^}]*identity\s*=\s*azurerm_user_assigned_identity\.acr_pull\.id",
        main,
        re.DOTALL,
    )
    assert "azurerm_role_assignment.acr_pull" in main
    assert re.search(r'logs_destination\s*=\s*"azure-monitor"', main)
    assert "admin_username" not in main
    assert "admin_password" not in main


def test_staging_and_production_have_independent_parameterized_roots() -> None:
    for environment in ("staging", "production"):
        root = ENVIRONMENTS / environment
        main = _read(root / "main.tf")
        variables = _read(root / "variables.tf")
        values = _read(root / f"{environment}.tfvars.example")
        backend = _read(root / "backend.tf")

        assert 'source = "../../modules/container_app"' in main
        assert re.search(rf'environment\s*=\s*"{environment}"', values)
        assert re.search(r"environment\s*=\s*var\.environment", main)
        for name in ("cpu", "memory", "min_replicas", "max_replicas"):
            assert re.search(rf"{name}\s*=\s*var\.{name}", main)
        assert re.search(r"environment_variables\s*=\s*var\.environment_variables", main)
        for variable in (
            "environment",
            "subscription_id",
            "registry_subscription_id",
            "resource_group_name",
            "registry_resource_group_name",
            "registry_name",
            "image_tag",
            "cpu",
            "memory",
            "min_replicas",
            "max_replicas",
            "environment_variables",
        ):
            assert f'variable "{variable}"' in variables
        assert 'backend "azurerm" {}' in backend


def test_environment_defaults_differ_and_do_not_embed_credentials() -> None:
    staging = _read(ENVIRONMENTS / "staging" / "staging.tfvars.example")
    production = _read(ENVIRONMENTS / "production" / "production.tfvars.example")

    assert re.search(r'container_app_name\s*=\s*"vsl-api-staging"', staging)
    assert re.search(r'container_app_name\s*=\s*"vsl-api-production"', production)
    assert re.search(r'LOG_LEVEL\s*=\s*"INFO"', staging)
    assert re.search(r'LOG_LEVEL\s*=\s*"WARNING"', production)
    assert "REPLACE_WITH_PUBLISHED_IMAGE_TAG" in staging
    assert "REPLACE_WITH_PUBLISHED_IMAGE_TAG" in production

    for source in (staging, production):
        assert "client_secret" not in source.lower()
        assert "password" not in source.lower()


def test_ci_formats_and_validates_each_terraform_root() -> None:
    workflow = _read(ROOT / ".github" / "workflows" / "ci.yml")

    assert "hashicorp/setup-terraform@" in workflow
    assert "staging.tfvars.example infra/environments/staging/staging.tfvars" in workflow
    assert "production.tfvars.example infra/environments/production/production.tfvars" in workflow
    assert "terraform fmt -check -recursive infra" in workflow
    for environment in ("staging", "production"):
        root = f"infra/environments/{environment}"
        assert f"terraform -chdir={root} init -backend=false" in workflow
        assert f"terraform -chdir={root} validate" in workflow


def test_us021_documentation_describes_isolation_and_shared_registry() -> None:
    document = _read(ROOT / "docs" / "infrastructure" / "US-021.md")

    for required in (
        "Azure Container Registry",
        "vsl-api-staging",
        "vsl-api-production",
        "AcrPull",
        "terraform -chdir=infra/environments/staging plan",
        "terraform apply",
        "LOG_LEVEL",
    ):
        assert required in document
    assert "state" in document.lower()
    assert "client secret" in document.lower()
    assert re.search(r"không chạy\s+`terraform apply`", document.lower())
