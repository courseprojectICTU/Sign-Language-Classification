"""Contract tests for US-020 Azure Container Apps service (min-instances = 0)."""

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
INFRA = ROOT / "infra"


def _read_infra(relative_path: str) -> str:
    path = INFRA / relative_path
    assert path.is_file(), f"Missing Terraform file: {path}"
    return path.read_text(encoding="utf-8")


def _all_infra_tf_sources() -> str:
    paths = sorted(path for path in INFRA.rglob("*.tf") if ".terraform" not in path.parts)
    assert paths, "No Terraform files found under infra/"
    return "\n".join(path.read_text(encoding="utf-8") for path in paths)


def _extract_hcl_block(source: str, header_pattern: str) -> str:
    match = re.search(header_pattern, source)
    assert match, f"Missing HCL block matching: {header_pattern}"
    brace_start = source.find("{", match.start())
    assert brace_start != -1, f"Malformed HCL block without opening brace: {header_pattern}"

    depth = 0
    in_string = False
    escaped = False
    for index in range(brace_start, len(source)):
        char = source[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[brace_start + 1 : index]

    raise AssertionError(f"Unclosed HCL block for pattern: {header_pattern}")


def test_us020_design_contract_exists_and_is_analysis_ready():
    doc = (ROOT / "docs" / "api" / "US-020.md").read_text(encoding="utf-8")
    assert "**Trạng thái:** `ANALYSIS_READY`" in doc
    for section_number in range(1, 18):
        assert re.search(
            rf"(?m)^## {section_number}\.\s+", doc
        ), f"Missing section {section_number}"
    for marker in ("AC-020-01", "AC-020-02", "BR-016", "TSK-035", "TSK-036"):
        assert marker in doc


def test_tsk_035_environment_pull_identity_and_cost_guardrails():
    container_app_tf = _read_infra("container_app.tf")
    all_tf = _all_infra_tf_sources()

    workspace = _extract_hcl_block(
        container_app_tf,
        r'resource\s+"azurerm_log_analytics_workspace"\s+"vsl"\s*\{',
    )
    assert re.search(r"name\s*=\s*var\.log_analytics_workspace_name", workspace)
    assert re.search(r'sku\s*=\s*"PerGB2018"', workspace)
    assert re.search(r"retention_in_days\s*=\s*30\b", workspace)

    env_block = _extract_hcl_block(
        container_app_tf,
        r'resource\s+"azurerm_container_app_environment"\s+"vsl"\s*\{',
    )
    assert re.search(r"name\s*=\s*var\.container_app_environment_name", env_block)
    assert re.search(
        r"log_analytics_workspace_id\s*=\s*azurerm_log_analytics_workspace\.vsl\.id",
        env_block,
    )
    assert re.search(r'logs_destination\s*=\s*"log-analytics"', env_block)
    assert "infrastructure_subnet_id" not in env_block
    assert "internal_load_balancer_enabled" not in env_block
    assert "zone_redundancy_enabled" not in env_block
    workload_profile = _extract_hcl_block(env_block, r"workload_profile\s*\{")
    assert re.search(r'name\s*=\s*"Consumption"', workload_profile)
    assert re.search(r'workload_profile_type\s*=\s*"Consumption"', workload_profile)

    pull_identity = _extract_hcl_block(
        container_app_tf,
        r'resource\s+"azurerm_user_assigned_identity"\s+"vsl_api_pull"\s*\{',
    )
    assert re.search(r'name\s*=\s*"id-\$\{var\.container_app_name\}-pull"', pull_identity)

    pull_role = _extract_hcl_block(
        container_app_tf,
        r'resource\s+"azurerm_role_assignment"\s+"vsl_api_acr_pull"\s*\{',
    )
    assert re.search(
        r"scope\s*=\s*(?:azurerm_container_registry\.vsl(?:\[0\])?\.id|local\.acr_id)",
        pull_role,
    )
    assert re.search(r'role_definition_name\s*=\s*"AcrPull"', pull_role)
    assert re.search(
        r"principal_id\s*=\s*azurerm_user_assigned_identity\.vsl_api_pull\.principal_id",
        pull_role,
    )

    for prohibited in (
        "azurerm_lb",
        "azurerm_application_gateway",
        "azurerm_nat_gateway",
        "azurerm_cdn_endpoint",
        "azurerm_frontdoor",
        "azurerm_cdn_frontdoor_profile",
        "azurerm_kubernetes_cluster",
        "azurerm_linux_virtual_machine",
        "azurerm_windows_virtual_machine",
    ):
        assert not re.search(rf'resource\s+"{prohibited}"', all_tf), f"BR-016 forbids {prohibited}"


def test_tsk_035_container_app_scale_to_zero_and_revision_mode():
    container_app_tf = _read_infra("container_app.tf")
    staging = _read_infra("environments/staging.tfvars")

    app_block = _extract_hcl_block(
        container_app_tf,
        r'resource\s+"azurerm_container_app"\s+"vsl_api"\s*\{',
    )
    assert re.search(r"name\s*=\s*var\.container_app_name", app_block)
    assert re.search(
        r"container_app_environment_id\s*=\s*azurerm_container_app_environment\.vsl\.id",
        app_block,
    )
    assert re.search(r'revision_mode\s*=\s*"Multiple"', app_block)
    assert re.search(r'workload_profile_name\s*=\s*"Consumption"', app_block)

    identity_block = _extract_hcl_block(app_block, r"identity\s*\{")
    assert re.search(r'type\s*=\s*"UserAssigned"', identity_block)
    assert "azurerm_user_assigned_identity.vsl_api_pull.id" in identity_block

    registry_block = _extract_hcl_block(app_block, r"registry\s*\{")
    assert re.search(
        r"server\s*=\s*(?:azurerm_container_registry\.vsl(?:\[0\])?\.login_server|local\.acr_login_server)",
        registry_block,
    )
    assert re.search(
        r"identity\s*=\s*azurerm_user_assigned_identity\.vsl_api_pull\.id",
        registry_block,
    )
    assert "password_secret_name" not in registry_block

    template_block = _extract_hcl_block(app_block, r"template\s*\{")
    assert re.search(r"min_replicas\s*=\s*var\.container_min_replicas", template_block)
    assert re.search(r"max_replicas\s*=\s*var\.container_max_replicas", template_block)
    assert re.search(
        r"cooldown_period_in_seconds\s*=\s*var\.scale_cooldown_seconds",
        template_block,
    )
    assert re.search(r"polling_interval_in_seconds\s*=\s*30\b", template_block)
    assert re.search(
        r"termination_grace_period_seconds\s*=\s*var\.container_termination_grace_period_seconds",
        template_block,
    )

    http_scale = _extract_hcl_block(template_block, r"http_scale_rule\s*\{")
    assert re.search(r"name\s*=\s*\"http-scaling\"", http_scale)
    assert re.search(
        r"concurrent_requests\s*=\s*tostring\(var\.http_scale_concurrent_requests\)",
        http_scale,
    )

    lifecycle_block = _extract_hcl_block(app_block, r"lifecycle\s*\{")
    assert "var.container_min_replicas == 0" in lifecycle_block
    assert "var.container_max_replicas >= var.container_min_replicas" in lifecycle_block
    assert 'var.container_cpu != 1 || var.container_memory == "2Gi"' in lifecycle_block

    assert re.search(r'log_analytics_workspace_name\s*=\s*"workspace-rgvslstaging8EBp"', staging)
    assert re.search(r'container_app_environment_name\s*=\s*"cae-vsl-staging-std"', staging)
    assert re.search(r"container_min_replicas\s*=\s*0\b", staging)
    assert re.search(r"container_max_replicas\s*=\s*3\b", staging)
    assert re.search(
        r'allowed_origins\s*=\s*"https://sign-language-classification\.pages\.dev"',
        staging,
    )
    tag_match = re.search(r'^\s*image_tag\s*=\s*"([^"]+)"\s*$', staging, re.MULTILINE)
    assert tag_match, "staging.tfvars must pin image_tag"
    assert tag_match.group(1) != "latest"
    assert not tag_match.group(1).startswith("REPLACE_WITH_")


def test_tsk_036_resources_probes_env_ingress_outputs_and_identity_scope():
    container_app_tf = _read_infra("container_app.tf")
    identity_tf = _read_infra("identity.tf")
    outputs_tf = _read_infra("outputs.tf")

    app_block = _extract_hcl_block(
        container_app_tf,
        r'resource\s+"azurerm_container_app"\s+"vsl_api"\s*\{',
    )
    ingress_block = _extract_hcl_block(app_block, r"ingress\s*\{")
    assert re.search(r"external_enabled\s*=\s*true", ingress_block)
    assert re.search(r"allow_insecure_connections\s*=\s*false", ingress_block)
    assert re.search(r"target_port\s*=\s*8080\b", ingress_block)
    assert re.search(r'transport\s*=\s*"auto"', ingress_block)
    traffic_block = _extract_hcl_block(ingress_block, r"traffic_weight\s*\{")
    assert re.search(r"percentage\s*=\s*100\b", traffic_block)
    assert re.search(r"latest_revision\s*=\s*true", traffic_block)

    template_block = _extract_hcl_block(app_block, r"template\s*\{")
    container_block = _extract_hcl_block(template_block, r"container\s*\{")
    assert re.search(r"name\s*=\s*var\.container_app_name", container_block)
    assert '"${local.acr_login_server}/${var.image_repository}:${var.image_tag}"' in container_block
    assert re.search(r"cpu\s*=\s*var\.container_cpu", container_block)
    assert re.search(r"memory\s*=\s*var\.container_memory", container_block)

    assert '"PORT"' in container_block
    assert '"8080"' in container_block
    assert '"VSL_MODEL_PATH"' in container_block
    assert "var.model_path" in container_block
    assert '"VSL_ALLOWED_ORIGINS"' in container_block
    assert "var.allowed_origins" in container_block

    for probe_name in ("startup_probe", "readiness_probe", "liveness_probe"):
        probe_block = _extract_hcl_block(container_block, rf"{probe_name}\s*\{{")
        assert re.search(r'transport\s*=\s*"HTTP"', probe_block)
        assert re.search(r'path\s*=\s*"/health"', probe_block)
        assert re.search(r"port\s*=\s*8080\b", probe_block)

    assert 'data "azurerm_container_app" "vsl_api"' not in identity_tf
    deploy_role = _extract_hcl_block(
        identity_tf,
        r'resource\s+"azurerm_role_assignment"\s+"deployment_app"\s*\{',
    )
    assert re.search(r"scope\s*=\s*azurerm_container_app\.vsl_api\.id", deploy_role)

    for output_name in (
        "container_app_url",
        "container_app_fqdn",
        "container_app_id",
        "container_app_environment_id",
    ):
        assert re.search(rf'output\s+"{output_name}"\s*\{{', outputs_tf)


def test_us020_variable_defaults_validations_and_production_placeholders():
    variables_tf = _read_infra("variables.tf")
    production = _read_infra("environments/production.tfvars")

    expected_defaults = {
        "image_repository": '"vsl-api"',
        "container_cpu": r"1\b",
        "container_memory": '"2Gi"',
        "container_min_replicas": r"0\b",
        "container_max_replicas": r"3\b",
        "container_termination_grace_period_seconds": r"60\b",
        "scale_cooldown_seconds": r"300\b",
        "http_scale_concurrent_requests": r"10\b",
        "model_path": '"/app/train/vsl_cnn_pose_keras.h5"',
    }
    for name, default_pattern in expected_defaults.items():
        var_block = _extract_hcl_block(variables_tf, rf'variable\s+"{name}"\s*\{{')
        assert re.search(rf"default\s*=\s*{default_pattern}", var_block), name

    image_tag_block = _extract_hcl_block(variables_tf, r'variable\s+"image_tag"\s*\{')
    assert "validation" in image_tag_block
    assert "latest" in image_tag_block

    cpu_block = _extract_hcl_block(variables_tf, r'variable\s+"container_cpu"\s*\{')
    assert "validation" in cpu_block
    memory_block = _extract_hcl_block(variables_tf, r'variable\s+"container_memory"\s*\{')
    assert "validation" in memory_block
    for mem in ("1Gi", "1.5Gi", "2Gi"):
        assert f'"{mem}"' in memory_block

    for placeholder_field in (
        "log_analytics_workspace_name",
        "container_app_environment_name",
        "image_tag",
        "allowed_origins",
    ):
        match = re.search(
            rf'^\s*{placeholder_field}\s*=\s*"([^"]+)"\s*$',
            production,
            re.MULTILINE,
        )
        assert match, f"Missing {placeholder_field} placeholder in production.tfvars"
        assert match.group(1).startswith("REPLACE_WITH_PRODUCTION_")


def test_us020_infra_readme_documents_staging_import_and_guardrails():
    readme = _read_infra("README.md")
    for required in (
        "terraform -chdir=infra import",
        "azurerm_log_analytics_workspace.vsl",
        "azurerm_container_app_environment.vsl",
        "azurerm_user_assigned_identity.vsl_api_pull",
        "azurerm_role_assignment.vsl_api_acr_pull",
        "azurerm_container_app.vsl_api",
    ):
        assert required in readme
