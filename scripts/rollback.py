#!/usr/bin/env python3
"""Safely inspect or roll back Azure Container Apps revision traffic."""

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
import subprocess
import sys
from typing import Any
import urllib.error
import urllib.request
from urllib.parse import urlsplit


class RollbackError(RuntimeError):
    """Raised when a rollback precondition or verification fails."""


@dataclass(frozen=True)
class Revision:
    name: str
    active: bool
    created_at: datetime


def _run_az(arguments: list[str], *, timeout: float = 60) -> str:
    try:
        result = subprocess.run(
            ["az", *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise RollbackError("Azure CLI 'az' is not installed or not on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise RollbackError("Azure CLI command timed out") from exc
    except OSError as exc:
        raise RollbackError(f"Could not run Azure CLI: {exc}") from exc

    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "no error details"
        raise RollbackError(f"Azure CLI command failed: {detail[:500]}")
    return result.stdout.strip()


def _load_json(raw: str, description: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RollbackError(
            f"Azure CLI returned invalid JSON for {description}"
        ) from exc


def _resource_arguments(
    command: list[str],
    *,
    resource_group: str,
    app_name: str,
    subscription: str | None,
    output: str = "json",
) -> list[str]:
    arguments = [
        *command,
        "--name",
        app_name,
        "--resource-group",
        resource_group,
    ]
    if subscription:
        arguments.extend(["--subscription", subscription])
    arguments.extend(["--output", output])
    return arguments


def _revision_timestamp(value: object, revision_name: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise RollbackError(f"Revision {revision_name!r} has no creation timestamp")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise RollbackError(
            f"Revision {revision_name!r} has an invalid creation timestamp"
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _read_revisions(
    *,
    resource_group: str,
    app_name: str,
    subscription: str | None,
    timeout: float,
) -> list[Revision]:
    raw = _run_az(
        _resource_arguments(
            ["containerapp", "revision", "list"],
            resource_group=resource_group,
            app_name=app_name,
            subscription=subscription,
        ),
        timeout=timeout,
    )
    payload = _load_json(raw, "revision list")
    if not isinstance(payload, list):
        raise RollbackError("Azure revision list must be a JSON array")

    revisions = []
    for item in payload:
        if not isinstance(item, dict):
            raise RollbackError("Azure revision list contains an invalid entry")
        properties = item.get("properties")
        if not isinstance(properties, dict):
            properties = {}

        name = item.get("name")
        active = properties.get("active", item.get("active"))
        if not isinstance(name, str) or not name:
            raise RollbackError("Azure revision list contains an entry without a name")
        if active is not True:
            continue
        created_at = properties.get("createdTime", item.get("createdTime"))
        revisions.append(
            Revision(
                name=name,
                active=True,
                created_at=_revision_timestamp(created_at, name),
            )
        )

    if len(revisions) < 2:
        raise RollbackError("Rollback requires at least two active revisions")
    if len({revision.name for revision in revisions}) != len(revisions):
        raise RollbackError(
            "Azure revision list contains duplicate active revision names"
        )
    return revisions


def _read_traffic_entries(
    *,
    resource_group: str,
    app_name: str,
    subscription: str | None,
    timeout: float,
) -> list[dict[str, Any]]:
    raw = _run_az(
        _resource_arguments(
            ["containerapp", "ingress", "traffic", "show"],
            resource_group=resource_group,
            app_name=app_name,
            subscription=subscription,
        ),
        timeout=timeout,
    )
    payload = _load_json(raw, "traffic configuration")
    if isinstance(payload, dict) and isinstance(payload.get("traffic"), list):
        payload = payload["traffic"]
    elif isinstance(payload, dict) and "revisionName" in payload:
        payload = [payload]
    if not isinstance(payload, list) or not payload:
        raise RollbackError("Azure traffic configuration must be a non-empty array")
    if any(not isinstance(item, dict) for item in payload):
        raise RollbackError("Azure traffic configuration contains an invalid entry")
    return payload


def _resolve_traffic(
    entries: list[dict[str, Any]],
    revisions: list[Revision],
) -> tuple[str, dict[str, int]]:
    latest = _unique_newest_revision(revisions, "latest active revision")
    active_names = {revision.name for revision in revisions}
    weights: dict[str, int] = {}

    for entry in entries:
        if entry.get("label"):
            raise RollbackError(
                "Traffic labels are unsupported; refusing ambiguous rollback"
            )
        revision_name = entry.get("revisionName")
        if entry.get("latestRevision") is True or revision_name == "latest":
            revision_name = latest.name
        if not isinstance(revision_name, str) or revision_name not in active_names:
            raise RollbackError("Traffic references an unknown or inactive revision")
        raw_weight = entry.get("weight")
        if isinstance(raw_weight, bool):
            raise RollbackError("Traffic weight is invalid")
        try:
            weight = int(raw_weight)
        except (TypeError, ValueError) as exc:
            raise RollbackError("Traffic weight is invalid") from exc
        if not 0 <= weight <= 100:
            raise RollbackError("Traffic weight must be between 0 and 100")
        weights[revision_name] = weights.get(revision_name, 0) + weight

    active_weights = {name: weight for name, weight in weights.items() if weight > 0}
    if sum(active_weights.values()) != 100 or len(active_weights) != 1:
        raise RollbackError(
            "Current traffic must route exactly 100% to one revision before rollback"
        )
    current_revision = next(iter(active_weights))
    return current_revision, weights


def _previous_revision(
    revisions: list[Revision],
    current_revision: str,
) -> Revision:
    by_name = {revision.name: revision for revision in revisions}
    current = by_name.get(current_revision)
    if current is None or not current.active:
        raise RollbackError("Current traffic revision is not active")
    previous = [
        revision
        for revision in revisions
        if revision.name != current_revision
        and revision.created_at < current.created_at
    ]
    if not previous:
        raise RollbackError(
            "No active revision older than the current revision was found"
        )
    return _unique_newest_revision(previous, "previous revision")


def _unique_newest_revision(revisions: list[Revision], description: str) -> Revision:
    newest_time = max(revision.created_at for revision in revisions)
    newest = [revision for revision in revisions if revision.created_at == newest_time]
    if len(newest) != 1:
        raise RollbackError(f"Cannot determine a unique {description}")
    return newest[0]


def _validate_url(url: str) -> str:
    try:
        parsed = urlsplit(url)
    except ValueError as exc:
        raise RollbackError("--url must be a valid HTTP(S) base URL") from exc
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise RollbackError(
            "--url must be an HTTP(S) base URL without credentials or query"
        )
    return url.rstrip("/")


def _request_json(url: str, *, timeout: float) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            if response.status != 200:
                raise RollbackError(
                    f"GET {url} expected HTTP 200, got {response.status}"
                )
            body = response.read()
    except urllib.error.HTTPError as exc:
        raise RollbackError(f"GET {url} returned HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RollbackError(f"GET {url} failed: {exc}") from exc

    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RollbackError(f"GET {url} returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise RollbackError(f"GET {url} response must be a JSON object")
    return payload


def _verify_service(url: str, expected_sha: str, timeout: float) -> None:
    health = _request_json(f"{url}/health", timeout=timeout)
    if health.get("model_loaded") is not True:
        raise RollbackError("/health did not report model_loaded=true")
    version = _request_json(f"{url}/version", timeout=timeout)
    if version.get("git_sha") != expected_sha:
        raise RollbackError(
            f"/version git_sha mismatch: expected {expected_sha!r}, "
            f"got {version.get('git_sha')!r}"
        )


def rollback(
    *,
    resource_group: str,
    app_name: str,
    subscription: str | None = None,
    apply: bool = False,
    target_revision: str | None = None,
    expected_current_revision: str | None = None,
    expected_sha: str | None = None,
    url: str | None = None,
    timeout: float = 60,
) -> str:
    """Inspect a rollback candidate or apply a confirmed, verified traffic change."""
    if timeout <= 0 or not math.isfinite(timeout):
        raise RollbackError("--timeout must be finite and positive")
    service_url: str | None = None
    verified_sha: str | None = None
    if apply:
        if (
            target_revision is None
            or expected_current_revision is None
            or expected_sha is None
            or url is None
        ):
            raise RollbackError(
                "--apply requires --target-revision, --expected-current-revision, "
                "--expected-sha, and --url"
            )
        if (
            not target_revision.strip()
            or not expected_current_revision.strip()
            or not expected_sha.strip()
        ):
            raise RollbackError(
                "--target-revision, --expected-current-revision, and --expected-sha "
                "must not be empty"
            )
        service_url = _validate_url(url)
        verified_sha = expected_sha

    mode = (
        _run_az(
            _resource_arguments(
                [
                    "containerapp",
                    "show",
                    "--query",
                    "properties.configuration.activeRevisionsMode",
                ],
                resource_group=resource_group,
                app_name=app_name,
                subscription=subscription,
                output="tsv",
            ),
            timeout=timeout,
        )
        .strip()
        .strip('"')
    )
    if mode.lower() != "multiple":
        raise RollbackError("Container App must use Multiple active revisions mode")

    revisions = _read_revisions(
        resource_group=resource_group,
        app_name=app_name,
        subscription=subscription,
        timeout=timeout,
    )
    traffic_entries = _read_traffic_entries(
        resource_group=resource_group,
        app_name=app_name,
        subscription=subscription,
        timeout=timeout,
    )
    current_revision, current_weights = _resolve_traffic(traffic_entries, revisions)
    target = _previous_revision(revisions, current_revision)

    if expected_current_revision and expected_current_revision != current_revision:
        raise RollbackError(
            f"Current revision mismatch: expected {expected_current_revision!r}, "
            f"found {current_revision!r}"
        )
    if target_revision and target_revision != target.name:
        raise RollbackError(
            f"Requested target {target_revision!r} is not the detected previous revision "
            f"{target.name!r}"
        )

    if not apply:
        print(
            f"Dry run: current={current_revision} ({current_weights[current_revision]}%), "
            f"previous={target.name}; no traffic changes made."
        )
        return target.name

    if expected_current_revision != current_revision:
        raise RollbackError(
            "--expected-current-revision does not match current traffic"
        )
    if target_revision != target.name:
        raise RollbackError(
            "--target-revision does not match the detected previous revision"
        )
    if service_url is None or verified_sha is None:
        raise RollbackError("Missing validated rollback verification inputs")
    print(f"Applying rollback: {current_revision}=0%, {target.name}=100%.")
    _run_az(
        _resource_arguments(
            [
                "containerapp",
                "ingress",
                "traffic",
                "set",
                "--revision-weight",
                f"{target.name}=100",
                f"{current_revision}=0",
            ],
            resource_group=resource_group,
            app_name=app_name,
            subscription=subscription,
            output="none",
        ),
        timeout=timeout,
    )

    try:
        updated_entries = _read_traffic_entries(
            resource_group=resource_group,
            app_name=app_name,
            subscription=subscription,
            timeout=timeout,
        )
        updated_revision, updated_weights = _resolve_traffic(updated_entries, revisions)
        if updated_revision != target.name or updated_weights.get(target.name) != 100:
            raise RollbackError("Azure traffic configuration did not reach target=100%")
        _verify_service(service_url, verified_sha, timeout)
    except RollbackError as exc:
        raise RollbackError(
            f"Traffic may already point to {target.name}, but post-rollback verification "
            f"failed: {exc}. Manual intervention is required; no further traffic change "
            "was attempted."
        ) from exc

    print(
        f"PASS rollback: traffic={target.name} 100%; "
        f"/health ready; /version git_sha={verified_sha}"
    )
    return target.name


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resource-group", required=True)
    parser.add_argument("--app-name", required=True)
    parser.add_argument("--subscription")
    parser.add_argument("--target-revision")
    parser.add_argument("--expected-current-revision")
    parser.add_argument("--expected-sha")
    parser.add_argument("--url")
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the traffic change (default is read-only dry-run)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        rollback(
            resource_group=args.resource_group,
            app_name=args.app_name,
            subscription=args.subscription,
            apply=args.apply,
            target_revision=args.target_revision,
            expected_current_revision=args.expected_current_revision,
            expected_sha=args.expected_sha,
            url=args.url,
            timeout=args.timeout,
        )
    except RollbackError as exc:
        print(f"Rollback failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
