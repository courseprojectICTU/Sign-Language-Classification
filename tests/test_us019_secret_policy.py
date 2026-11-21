"""Secret-policy checks for US-019; reports paths, never credential values."""

import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {
    "",
    ".cfg",
    ".cmd",
    ".csv",
    ".gitattributes",
    ".hcl",
    ".ini",
    ".ipynb",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".sh",
    ".tf",
    ".tfvars",
    ".toml",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
PRIVATE_KEY_MARKER = re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")


def _tracked_and_untracked_paths():
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return {
        pathlib.Path(line)
        for line in result.stdout.splitlines()
        if line and pathlib.Path(line).suffix.lower() in TEXT_SUFFIXES
    }


def _working_tree_key_paths():
    matches = []
    for relative_path in _tracked_and_untracked_paths():
        if any(part in {".git", ".terraform", ".venv"} for part in relative_path.parts):
            continue
        path = ROOT / relative_path
        if path.is_file() and PRIVATE_KEY_MARKER.search(path.read_bytes()):
            matches.append(relative_path.as_posix())
    return sorted(matches)


def _historical_key_paths():
    objects = subprocess.run(
        ["git", "rev-list", "--all", "--objects"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    paths_by_object = {}
    for line in objects.stdout.splitlines():
        parts = line.split(" ", 1)
        if len(parts) != 2:
            continue
        object_id, file_name = parts
        if pathlib.Path(file_name).suffix.lower() in TEXT_SUFFIXES:
            paths_by_object.setdefault(object_id, file_name)

    if not paths_by_object:
        return []

    object_ids = list(paths_by_object)
    metadata = subprocess.run(
        ["git", "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
        cwd=ROOT,
        input="".join(f"{object_id}\n" for object_id in object_ids),
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    text_object_ids = []
    for line in metadata.stdout.splitlines():
        object_id, object_type, size = line.split()
        if object_type == "blob" and int(size) <= 5_000_000:
            text_object_ids.append(object_id)

    history = subprocess.run(
        ["git", "cat-file", "--batch"],
        cwd=ROOT,
        input="".join(f"{object_id}\n" for object_id in text_object_ids).encode(),
        check=True,
        capture_output=True,
    ).stdout

    matches = []
    offset = 0
    while offset < len(history):
        header_end = history.find(b"\n", offset)
        object_id, object_type, size_text = history[offset:header_end].split()
        size = int(size_text)
        content_start = header_end + 1
        content_end = content_start + size
        content = history[content_start:content_end]
        if PRIVATE_KEY_MARKER.search(content):
            matches.append(paths_by_object[object_id.decode("ascii")])
        offset = content_end + 1
    return sorted(set(matches))


def test_repository_working_tree_contains_no_private_key_material():
    matches = _working_tree_key_paths()
    assert not matches, f"Private-key material found in file paths: {matches}"


def test_git_history_contains_no_private_key_material():
    matches = _historical_key_paths()
    assert not matches, f"Private-key material found in historical file paths: {matches}"


def test_terraform_and_workflow_do_not_use_static_ci_credentials():
    infra_sources = [
        path.read_text(encoding="utf-8")
        for path in (ROOT / "infra").rglob("*.tf")
        if ".terraform" not in path.parts
    ]
    workflow_path = ROOT / ".github" / "workflows" / "azure-oidc-smoke.yml"
    assert workflow_path.is_file(), f"Missing GitHub OIDC workflow: {workflow_path}"
    workflow = workflow_path.read_text(encoding="utf-8")

    for source in infra_sources:
        assert "azuread_service_principal_password" not in source
        assert not re.search(r"\bclient_secret\s*=", source, re.IGNORECASE)
    for forbidden in (
        "AZURE_CREDENTIALS",
        "REGISTRY_USERNAME",
        "REGISTRY_PASSWORD",
        "ACR_USERNAME",
        "ACR_PASSWORD",
        "secrets.",
    ):
        assert forbidden not in workflow


def test_ci_documentation_recommends_oidc_not_static_secret_creation():
    handover = (ROOT / "docs" / "infrastructure" / "HO-SO-BAN-GIAO-HA-TANG.md").read_text(
        encoding="utf-8"
    )
    ci_plan = (ROOT / "docs" / "planning" / "KE-HOACH-NANG-CAP-CI-CD-2-TUAN.md").read_text(
        encoding="utf-8"
    )
    migration_plan = (
        ROOT / "docs" / "planning" / "KE-HOACH-CHUYEN-DOI-HA-TANG-AZURE.md"
    ).read_text(encoding="utf-8")

    assert "az ad sp create-for-rbac" not in handover
    assert "Cấu Hình GitHub Actions bằng Azure OIDC" in handover
    assert "Actions Variables" in handover
    assert "`clientSecret`, service-account key JSON hoặc ACR" in ci_plan
    assert "GitHub OIDC Federated Identity Credential" in ci_plan
    assert "Azure Service Principal + GitHub OIDC Federated Identity Credential" in migration_plan
