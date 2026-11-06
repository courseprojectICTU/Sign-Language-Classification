"""Unit tests for the US-013 cold-start benchmark harness."""

from unittest.mock import patch

import pytest

from scripts.benchmark_cold_start import (
    calculate_statistics,
    measure_request,
    run_benchmark,
    validate_preflight_receipt,
)


def test_scale_to_zero_receipt_requires_zero_instances() -> None:
    receipt = validate_preflight_receipt(
        '{"mode":"scale_to_zero","active_instances":0,'
        '"min_instances":0,"revision":"rev-a"}'
    )

    assert receipt["mode"] == "scale_to_zero"
    assert receipt["revision"] == "rev-a"


@pytest.mark.parametrize(
    "raw_receipt",
    [
        '{"mode":"scale_to_zero","active_instances":1,"min_instances":0}',
        '{"mode":"scale_to_zero","active_instances":0,"min_instances":1}',
        '{"mode":"fresh_revision","confirmed":false,"revision":"rev-a"}',
        '{"mode":"fresh_revision","confirmed":true}',
        "not-json",
    ],
)
def test_invalid_preflight_receipt_is_rejected(raw_receipt: str) -> None:
    with pytest.raises(ValueError):
        validate_preflight_receipt(raw_receipt)


def test_fresh_revision_receipt_is_accepted() -> None:
    receipt = validate_preflight_receipt(
        '{"mode":"fresh_revision","confirmed":true,"revision":"rev-b"}'
    )

    assert receipt["mode"] == "fresh_revision"
    assert receipt["revision"] == "rev-b"


def test_statistics_calculate_median_mean_min_max() -> None:
    assert calculate_statistics([8.0, 3.0, 5.0, 4.0, 10.0]) == {
        "median_ms": 5.0,
        "mean_ms": 6.0,
        "min_ms": 3.0,
        "max_ms": 10.0,
    }


def test_measure_request_records_ttfb_and_total_latency() -> None:
    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, size: int = -1) -> bytes:
            return b"{" if size == 1 else b'"ok":true}'

    with patch("scripts.benchmark_cold_start.urlopen", return_value=FakeResponse()):
        result = measure_request("https://staging.example/health", timeout=3.0)

    assert result["status_code"] == 200
    assert result["bytes_received"] > 0
    assert result["ttfb_ms"] >= 0
    assert result["total_ms"] >= result["ttfb_ms"]


def test_benchmark_runs_five_preflights_and_measurements() -> None:
    receipt = {"mode": "scale_to_zero", "active_instances": 0, "min_instances": 0, "revision": "rev-a"}
    measurement = {
        "status_code": 200,
        "ttfb_ms": 100.0,
        "total_ms": 120.0,
        "bytes_received": 10,
    }

    with (
        patch("scripts.benchmark_cold_start.run_preflight", return_value=receipt) as preflight,
        patch("scripts.benchmark_cold_start.measure_request", return_value=measurement) as request,
    ):
        result = run_benchmark(
            url="https://staging.example/health",
            preflight_command=["check-cloud-run-zero"],
            timeout=30.0,
        )

    assert len(result["measurements"]) == 5
    assert preflight.call_count == 5
    assert request.call_count == 5
    assert result["statistics"]["ttfb"]["median_ms"] == 100.0
    assert result["statistics"]["total"]["mean_ms"] == 120.0