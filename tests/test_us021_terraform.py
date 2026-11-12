"""Contract tests for US-021 staging/production environment isolation on root infra/."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INFRA = ROOT / "infra"
STAGING_TFVARS = INFRA / "environments" / "staging.tfvars"
PRODUCTION_TFVARS = INFRA / "environments" / "production.tfvars"
US021_DOC = ROOT / "docs" / "api" / "US-021.md"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def _read(path: Path) -> str:
    assert path.is_file(), f"Missing expected file: {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8")


def _extract_hcl_assignments(tfvars_text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in tfvars_text.splitlines():
        stripped = line.split("#", 1)[0].strip()
        if "=" not in stripped:
            continue
        key, raw_val = stripped.split("=", 1)
        values[key.strip()] = raw_val.strip()
    return values


def test_us021_api_doc_follows_17_section_template_and_is_ready() -> None:
    content = _read(US021_DOC)

    assert "ANALYSIS_READY" in content
    for section_num in range(1, 18):
        assert re.search(
            rf"(?m)^## {section_num}\.\s+", content
        ), f"Missing section ## {section_num}. in docs/api/US-021.md"
    for token in ("AC-021-01", "TSK-037", "TSK-038", "BR-016", "BR-017"):
        assert token in content


def test_duplicate_module_and_environment_subroots_are_removed() -> None:
    assert not (INFRA / "modules" / "container_app").exists()
    assert not (INFRA / "environments" / "staging").exists()
    assert not (INFRA / "environments" / "production").exists()
    assert STAGING_TFVARS.is_file()
    assert PRODUCTION_TFVARS.is_file()


def test_environments_isolate_config_and_share_vslacr3795_without_duplication() -> None:
    staging_text = _read(STAGING_TFVARS)
    production_text = _read(PRODUCTION_TFVARS)
    staging = _extract_hcl_assignments(staging_text)
    production = _extract_hcl_assignments(production_text)

    assert staging.get("environment") == '"staging"'
    assert production.get("environment") == '"production"'

    assert staging.get("manage_registry") == "true"
    assert production.get("manage_registry") == "false"

    assert staging.get("acr_name") == '"vslacr3795"'
    assert production.get("acr_name") == '"vslacr3795"'
    assert "registry_subscription_id" in production
    assert production.get("registry_resource_group_name") == '"rg-vsl-staging"'

    assert staging.get("log_level") == '"INFO"'
    assert production.get("log_level") == '"WARNING"'
    assert re.search(r"tags\s*=\s*\{[^}]*workload\s*=", staging_text, re.DOTALL)
    assert re.search(r"tags\s*=\s*\{[^}]*workload\s*=", production_text, re.DOTALL)

    for isolated_key in (
        "subscription_id",
        "resource_group_name",
        "container_app_name",
        "log_analytics_workspace_name",
        "container_app_environment_name",
        "github_oidc_subject",
        "allowed_origins",
    ):
        assert staging.get(isolated_key) != production.get(isolated_key)


def test_br016_scale_to_zero_enforced_in_both_environments_and_precondition() -> None:
    staging = _extract_hcl_assignments(_read(STAGING_TFVARS))
    production = _extract_hcl_assignments(_read(PRODUCTION_TFVARS))

    assert staging.get("container_min_replicas") == "0"
    assert production.get("container_min_replicas") == "0"
    assert staging.get("container_max_replicas") == "3"
    assert production.get("container_max_replicas") == "3"

    container_app_tf = _read(INFRA / "container_app.tf")
    assert re.search(
        r"condition\s*=\s*var\.container_min_replicas\s*==\s*0\b",
        container_app_tf,
    )
    assert 'var.environment != "staging" || var.container_min_replicas == 0' not in container_app_tf
    assert 'revision_mode                = "Multiple"' in container_app_tf or re.search(
        r'revision_mode\s*=\s*"Multiple"',
        container_app_tf,
    )


def test_shared_acr_and_multi_environment_wiring_in_root_infra() -> None:
    provider_tf = _read(INFRA / "provider.tf")
    registry_tf = _read(INFRA / "registry.tf")
    identity_tf = _read(INFRA / "identity.tf")
    container_app_tf = _read(INFRA / "container_app.tf")
    outputs_tf = _read(INFRA / "outputs.tf")
    variables_tf = _read(INFRA / "variables.tf")

    assert 'alias                         = "registry"' in provider_tf or re.search(
        r'alias\s*=\s*"registry"',
        provider_tf,
    )
    assert "coalesce(trimspace(var.registry_subscription_id), var.subscription_id)" in provider_tf

    assert re.search(r"count\s*=\s*var\.manage_registry\s*\?\s*1\s*:\s*0", registry_tf)
    assert re.search(r'data\s+"azurerm_container_registry"\s+"shared"\s*\{', registry_tf)
    assert re.search(r"provider\s*=\s*azurerm\.registry", registry_tf)
    for moved_name in ("vsl", "registry_cleanup", "cleanup_delete", "cleanup"):
        assert f"{moved_name}[0]" in registry_tf

    assert re.search(r"\bacr_id\s*=", registry_tf)
    assert re.search(r"\bacr_login_server\s*=", registry_tf)
    assert re.search(r"provider\s*=\s*azurerm\.registry", identity_tf)
    assert re.search(r"scope\s*=\s*local\.acr_id", identity_tf)

    assert re.search(r"provider\s*=\s*azurerm\.registry", container_app_tf)
    assert re.search(r"scope\s*=\s*local\.acr_id", container_app_tf)
    assert re.search(r'name\s*=\s*"LOG_LEVEL"', container_app_tf)
    assert "var.log_level" in container_app_tf
    assert "local.common_tags" in container_app_tf

    assert 'output "image_reference"' in outputs_tf
    assert 'output "shared_acr_login_server"' in outputs_tf
    for var_name in (
        "manage_registry",
        "registry_subscription_id",
        "registry_resource_group_name",
        "log_level",
        "tags",
    ):
        assert f'variable "{var_name}"' in variables_tf


def test_root_infra_docs_and_ci_validate_single_root_and_no_static_secrets() -> None:
    infra_readme = _read(INFRA / "README.md")
    assert "staging.tfstate" in infra_readme
    assert "production.tfstate" in infra_readme
    assert "vslacr3795" in infra_readme

    ci_text = _read(CI_WORKFLOW)
    assert "terraform fmt -check -recursive infra" in ci_text
    assert "terraform -chdir=infra init -backend=false -input=false" in ci_text
    assert "terraform -chdir=infra validate -no-color" in ci_text
    assert "infra/environments/staging init" not in ci_text
    assert "infra/environments/production init" not in ci_text

    production_text = _read(PRODUCTION_TFVARS)
    assert "client_secret" not in production_text
    assert "REPLACE_WITH_PRODUCTION_" in production_text
