"""Tests for US-018 Terraform scaffolding and remote state configuration."""

import pathlib
import re


ROOT = pathlib.Path(__file__).resolve().parents[1]
INFRA = ROOT / "infra"


def _read(relative_path):
    path = INFRA / relative_path
    assert path.is_file(), f"Missing Terraform configuration: {path}"
    return path.read_text(encoding="utf-8")


def test_tsk_030_google_provider_and_environment_tfvars_are_defined():
    versions = _read("versions.tf")
    provider = _read("provider.tf")
    variables = _read("variables.tf")

    assert re.search(r'google\s*=\s*\{[^}]*source\s*=\s*"hashicorp/google"', versions, re.DOTALL)
    assert re.search(r'provider\s+"google"\s*\{', provider)
    assert re.search(r'project\s*=\s*var\.project_id', provider)
    assert re.search(r'region\s*=\s*var\.region', provider)
    assert re.search(r'variable\s+"project_id"', variables)
    assert re.search(r'variable\s+"region"', variables)
    assert re.search(r'variable\s+"environment"', variables)

    for environment in ("staging", "production"):
        tfvars = _read(f"environments/{environment}.tfvars")
        assert re.search(rf'environment\s*=\s*"{environment}"', tfvars)
        assert re.search(r'project_id\s*=', tfvars)
        assert re.search(r'region\s*=', tfvars)


def test_tsk_031_gcs_backend_and_state_safety_are_documented():
    backend = _read("backend.tf")
    gitignore = _read(".gitignore")
    readme = _read("README.md")

    assert re.search(r'backend\s+"gcs"\s*\{', backend)
    assert re.search(r'^\s*\.terraform/?\s*$', gitignore, re.MULTILINE)
    assert re.search(r'^\s*\*\.tfstate\*?\s*$', gitignore, re.MULTILINE)
    assert "terraform init" in readme
    assert "backend-config" in readme
    assert "lock" in readme.lower()
