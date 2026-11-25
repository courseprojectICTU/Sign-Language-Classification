"""Contract tests for the US-034 Azure Monitor 5xx alert."""

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
INFRA = ROOT / "infra"
API_DOC = ROOT / "docs" / "api" / "US-034.md"
MONITORING_TF = INFRA / "monitoring.tf"
VARIABLES_TF = INFRA / "variables.tf"
RUNBOOK = ROOT / "docs" / "RUNBOOK.md"


def _read(path: pathlib.Path) -> str:
    assert path.is_file(), f"Missing file required for US-034: {path}"
    return path.read_text(encoding="utf-8")


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


def test_us034_contract_doc_has_all_sections_and_decisions() -> None:
    content = _read(API_DOC)

    for section_number in range(1, 18):
        assert re.search(
            rf"(?m)^##\s+{section_number}\.\s+", content
        ), f"docs/api/US-034.md missing section {section_number}"

    for marker in (
        "ANALYSIS_READY",
        "AC-034-01",
        "BR-023",
        "100",
        "PT5M",
        "staging",
        "TF_VAR_server_error_alert_emails",
        "revision canary",
    ):
        assert marker in content


def test_us034_alert_counts_only_5xx_for_the_staging_container_app() -> None:
    monitoring = _read(MONITORING_TF)

    assert re.search(
        r'resource\s+"azurerm_monitor_scheduled_query_rules_alert_v2"\s+"server_error"\s*\{',
        monitoring,
    )
    assert "ContainerAppConsoleLogs_CL" in monitoring
    assert "ContainerAppName_s" in monitoring
    assert "Log_s" in monitoring
    assert "500" in monitoring and "599" in monitoring
    assert re.search(r'container_app_name\s*=\s*var\.container_app_name', monitoring)

    alert = _extract_hcl_block(
        monitoring,
        r'resource\s+"azurerm_monitor_scheduled_query_rules_alert_v2"\s+"server_error"\s*\{',
    )
    assert re.search(r"scopes\s*=\s*\[azurerm_log_analytics_workspace\.vsl\.id\]", alert)
    assert re.search(r'evaluation_frequency\s*=\s*"PT5M"', alert)
    assert re.search(r'window_duration\s*=\s*"PT5M"', alert)
    assert re.search(r'time_aggregation_method\s*=\s*"Count"', alert)
    assert re.search(r"threshold\s*=\s*100\b", alert)
    assert re.search(r'operator\s*=\s*"GreaterThanOrEqual"', alert)
    assert re.search(
        r"action_groups\s*=\s*\[azurerm_monitor_action_group\.server_error\[0\]\.id\]",
        alert,
    )


def test_us034_alert_resources_are_created_only_for_staging() -> None:
    monitoring = _read(MONITORING_TF)

    for resource_type, resource_name in (
        ("azurerm_monitor_action_group", "server_error"),
        ("azurerm_monitor_scheduled_query_rules_alert_v2", "server_error"),
    ):
        block = _extract_hcl_block(
            monitoring,
            rf'resource\s+"{resource_type}"\s+"{resource_name}"\s*\{{',
        )
        assert re.search(r'count\s*=\s*var\.environment\s*==\s*"staging"\s*\?\s*1\s*:\s*0', block)


def test_us034_email_recipients_are_required_and_validated() -> None:
    variables = _read(VARIABLES_TF)
    variable = _extract_hcl_block(
        variables,
        r'variable\s+"server_error_alert_emails"\s*\{',
    )

    assert re.search(r"type\s*=\s*list\(string\)", variable)
    assert "default" not in variable
    assert "length(var.server_error_alert_emails) > 0" in variable
    assert "alltrue" in variable
    assert "email" in variable.lower()


def test_us034_runbook_documents_alert_verification_and_canary_cleanup() -> None:
    runbook = _read(RUNBOOK)

    for required in (
        "US-034",
        "5xx",
        "100",
        "5 phút",
        "10 phút",
        "canary",
        "TF_VAR_server_error_alert_emails",
    ):
        assert required in runbook, f"Missing US-034 runbook detail: {required}"
