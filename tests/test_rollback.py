"""Tests for guarded Azure Container Apps traffic rollback."""

import json

import pytest

from scripts import rollback

REVISION_DATA = [
    {
        "name": "vsl-api--rev1",
        "properties": {"active": True, "createdTime": "2026-11-01T10:00:00Z"},
    },
    {
        "name": "vsl-api--rev2",
        "properties": {"active": True, "createdTime": "2026-11-02T10:00:00Z"},
    },
]


class AzureCliStub:
    def __init__(self) -> None:
        self.traffic = [{"revisionName": "vsl-api--rev2", "weight": 100}]
        self.commands: list[list[str]] = []
        self.revision_mode = "Multiple"
        self.revisions = REVISION_DATA

    def run(self, args: list[str], *, timeout: float = 60) -> str:
        self.commands.append(args)
        if any("activeRevisionsMode" in argument for argument in args):
            return self.revision_mode
        if args[:3] == ["containerapp", "revision", "list"]:
            return json.dumps(self.revisions)
        if args[:4] == ["containerapp", "ingress", "traffic", "show"]:
            return json.dumps(self.traffic)
        if args[:4] == ["containerapp", "ingress", "traffic", "set"]:
            weight_index = args.index("--revision-weight") + 1
            weights = args[weight_index : args.index("--name")]
            self.traffic = [
                {
                    "revisionName": value.rsplit("=", 1)[0],
                    "weight": int(value.rsplit("=", 1)[1]),
                }
                for value in weights
            ]
            return ""
        raise AssertionError(f"Unexpected Azure CLI command: {args}")


def _install_azure_stub(
    monkeypatch: pytest.MonkeyPatch,
) -> AzureCliStub:
    stub = AzureCliStub()
    monkeypatch.setattr(rollback, "_run_az", stub.run)
    return stub


def test_dry_run_selects_previous_revision_without_changing_traffic(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    azure = _install_azure_stub(monkeypatch)

    selected = rollback.rollback(
        resource_group="rg-test",
        app_name="vsl-api",
    )

    assert selected == "vsl-api--rev1"
    assert not any(
        command[:4] == ["containerapp", "ingress", "traffic", "set"] for command in azure.commands
    )
    assert "Dry run" in capsys.readouterr().out


def test_apply_sets_previous_revision_to_100_percent_and_verifies_sha(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    azure = _install_azure_stub(monkeypatch)
    responses = {
        "/health": {"model_loaded": True},
        "/version": {"git_sha": "sha-rev1"},
    }

    def get_json(url: str, *, timeout: float = 30) -> dict[str, object]:
        return responses[url[url.rfind("/") :]]

    monkeypatch.setattr(rollback, "_request_json", get_json)

    selected = rollback.rollback(
        resource_group="rg-test",
        app_name="vsl-api",
        apply=True,
        target_revision="vsl-api--rev1",
        expected_current_revision="vsl-api--rev2",
        expected_sha="sha-rev1",
        url="https://api.example",
    )

    set_command = next(
        command
        for command in azure.commands
        if command[:4] == ["containerapp", "ingress", "traffic", "set"]
    )
    assert selected == "vsl-api--rev1"
    weight_values = set_command[
        set_command.index("--revision-weight") + 1 : set_command.index("--name")
    ]
    assert weight_values == [
        "vsl-api--rev1=100",
        "vsl-api--rev2=0",
    ]
    assert azure.traffic == [
        {"revisionName": "vsl-api--rev1", "weight": 100},
        {"revisionName": "vsl-api--rev2", "weight": 0},
    ]


def test_apply_refuses_target_different_from_detected_previous(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    azure = _install_azure_stub(monkeypatch)

    with pytest.raises(rollback.RollbackError, match="target"):
        rollback.rollback(
            resource_group="rg-test",
            app_name="vsl-api",
            apply=True,
            target_revision="vsl-api--rev2",
            expected_current_revision="vsl-api--rev2",
            expected_sha="sha",
            url="https://api.example",
        )

    assert not any(
        command[:4] == ["containerapp", "ingress", "traffic", "set"] for command in azure.commands
    )


def test_apply_refuses_unconfirmed_current_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    azure = _install_azure_stub(monkeypatch)

    with pytest.raises(rollback.RollbackError, match="Current revision mismatch"):
        rollback.rollback(
            resource_group="rg-test",
            app_name="vsl-api",
            apply=True,
            target_revision="vsl-api--rev1",
            expected_current_revision="unexpected",
            expected_sha="sha",
            url="https://api.example",
        )

    assert not any(
        command[:4] == ["containerapp", "ingress", "traffic", "set"] for command in azure.commands
    )


def test_rollback_refuses_single_revision_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    azure = _install_azure_stub(monkeypatch)
    azure.revision_mode = "Single"

    with pytest.raises(rollback.RollbackError, match="Multiple"):
        rollback.rollback(resource_group="rg-test", app_name="vsl-api")

    assert not any(
        command[:4] == ["containerapp", "ingress", "traffic", "set"] for command in azure.commands
    )


def test_rollback_refuses_split_or_ambiguous_current_traffic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    azure = _install_azure_stub(monkeypatch)
    azure.traffic = [
        {"revisionName": "vsl-api--rev1", "weight": 20},
        {"revisionName": "vsl-api--rev2", "weight": 80},
    ]

    with pytest.raises(rollback.RollbackError, match="100%"):
        rollback.rollback(resource_group="rg-test", app_name="vsl-api")

    assert not any(
        command[:4] == ["containerapp", "ingress", "traffic", "set"] for command in azure.commands
    )


def test_rollback_refuses_ambiguous_previous_revision_timestamp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    azure = _install_azure_stub(monkeypatch)
    azure.revisions = [
        {
            "name": "vsl-api--rev1",
            "properties": {
                "active": True,
                "createdTime": "2026-11-01T10:00:00Z",
            },
        },
        {
            "name": "vsl-api--rev1b",
            "properties": {
                "active": True,
                "createdTime": "2026-11-01T10:00:00Z",
            },
        },
        REVISION_DATA[1],
    ]

    with pytest.raises(rollback.RollbackError, match="unique previous revision"):
        rollback.rollback(resource_group="rg-test", app_name="vsl-api")

    assert not any(
        command[:4] == ["containerapp", "ingress", "traffic", "set"] for command in azure.commands
    )


def test_apply_validates_required_inputs_before_calling_azure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    azure = _install_azure_stub(monkeypatch)

    with pytest.raises(rollback.RollbackError, match="requires"):
        rollback.rollback(
            resource_group="rg-test",
            app_name="vsl-api",
            apply=True,
        )

    assert azure.commands == []
