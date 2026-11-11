"""Parity, exporter, and resilience tests for US-011 (Keras H5 to ONNX)."""

import hashlib
import json
import pathlib
import re

import numpy as np

from src.vsl.config import PROJECT_ROOT, get_model_path
from src.vsl.heatmap import create_heatmap
from src.vsl.labels import NUM_CLASSES, VIETNAMESE_ALPHABET
from src.vsl.service import preprocess_heatmap

ROOT = PROJECT_ROOT


def _exporter():
    from scripts import export_onnx

    return export_onnx


def test_us011_contract_is_analysis_ready():
    doc = (ROOT / "docs" / "api" / "US-011.md").read_text(encoding="utf-8")
    assert "**Trạng thái:** `ANALYSIS_READY`" in doc
    for section_number in range(1, 18):
        assert re.search(
            rf"(?m)^## {section_number}\.\s+", doc
        ), f"Missing section {section_number} in US-011.md"
    for required_id in ("AC-011-01", "AC-011-02", "BR-006", "TSK-017", "TSK-018"):
        assert required_id in doc


def test_tsk_017_export_validates_inputs_and_refuses_blind_overwrite(tmp_path):
    export_onnx = _exporter()
    missing_model = tmp_path / "missing.h5"
    target_onnx = tmp_path / "model.onnx"

    try:
        export_onnx.export_keras_to_onnx(missing_model, target_onnx)
    except export_onnx.OnnxExportError:
        pass
    else:
        raise AssertionError("Expected OnnxExportError for missing .h5 model")

    sample_model = tmp_path / "dummy.h5"
    sample_model.write_bytes(b"h5-content")
    assert (
        export_onnx.compute_file_sha256(sample_model) == hashlib.sha256(b"h5-content").hexdigest()
    )

    try:
        export_onnx.export_keras_to_onnx(sample_model, target_onnx, opset=0)
    except export_onnx.OnnxExportError:
        pass
    else:
        raise AssertionError("Expected OnnxExportError for opset <= 0")

    target_onnx.write_bytes(b"existing-onnx")
    try:
        export_onnx.export_keras_to_onnx(sample_model, target_onnx, overwrite=False)
    except export_onnx.OnnxExportError:
        pass
    else:
        raise AssertionError("Expected OnnxExportError when output exists without overwrite=True")
    assert target_onnx.read_bytes() == b"existing-onnx"

    exit_code = export_onnx.main(
        ["--model-path", str(missing_model), "--output", str(tmp_path / "cli.onnx")]
    )
    assert exit_code != 0


def test_br_006_sample_batch_uses_caffe_preprocessing():
    export_onnx = _exporter()
    labels, batch = export_onnx.load_sample_heatmap_batch()

    assert tuple(labels) == VIETNAMESE_ALPHABET
    assert batch.shape == (NUM_CLASSES, 224, 224, 3)
    assert batch.dtype == np.float32
    assert float(np.min(batch)) < 0.0, "BR-006 Caffe subtraction must produce negative values"
    assert float(np.max(batch)) > 1.0, "BR-006 must not normalize pixels by dividing by 255"

    expected_first = preprocess_heatmap(
        np.expand_dims(
            create_heatmap(
                export_onnx.load_csv_landmarks(ROOT / "data" / "anphabet" / labels[0] / "1.csv")
            ),
            axis=0,
        )
    ).astype(np.float32)
    assert np.array_equal(batch[0:1], expected_first)


def test_ac_011_01_keras_to_onnx_export_and_numerical_parity(tmp_path):
    export_onnx = _exporter()
    import onnxruntime as ort
    from keras.models import load_model

    model_path = get_model_path()
    onnx_path = tmp_path / "model.onnx"
    report_path = tmp_path / "export-report.json"

    metadata = export_onnx.export_keras_to_onnx(
        model_path,
        onnx_path,
        opset=15,
        json_report_path=report_path,
    )
    assert onnx_path.is_file()
    assert metadata["onnx_size_bytes"] == onnx_path.stat().st_size > 0
    assert metadata["h5_size_bytes"] == model_path.stat().st_size

    session_info = export_onnx.verify_onnx_session(onnx_path, providers=["CPUExecutionProvider"])
    assert session_info["input_names"]
    assert session_info["output_names"]

    report_payload = json.loads(report_path.read_text(encoding="utf-8"))
    for key in (
        "source_sha256",
        "h5_size_bytes",
        "onnx_size_bytes",
        "opset",
        "versions",
        "input_names",
        "output_names",
    ):
        assert key in report_payload

    labels, batch = export_onnx.load_sample_heatmap_batch()
    keras_model = load_model(str(model_path))
    keras_preds = keras_model(batch, training=False).numpy()

    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name
    onnx_preds = session.run([output_name], {input_name: batch})[0]

    assert keras_preds.shape == (NUM_CLASSES, NUM_CLASSES)
    assert onnx_preds.shape == (NUM_CLASSES, NUM_CLASSES)

    max_abs_diff = float(np.max(np.abs(keras_preds - onnx_preds)))
    assert max_abs_diff < 1e-4, f"AC-011-01 failed: max_abs_diff={max_abs_diff}"

    keras_argmax = np.argmax(keras_preds, axis=1)
    onnx_argmax = np.argmax(onnx_preds, axis=1)
    assert np.array_equal(keras_argmax, onnx_argmax)
    assert list(onnx_argmax) == list(range(len(labels)))


def test_ac_011_02_converter_failure_cleans_partial_artifacts_and_preserves_runtime(
    tmp_path, monkeypatch
):
    export_onnx = _exporter()
    fake_model = tmp_path / "source.h5"
    fake_model.write_bytes(b"fake-h5-bytes")
    output_onnx = tmp_path / "failed.onnx"

    def fail_convert(*args, **kwargs):
        output_onnx.write_bytes(b"partial-corrupt")
        raise RuntimeError("simulated tf2onnx conversion failure")

    monkeypatch.setattr(export_onnx, "_export_keras_to_saved_model", lambda *args, **kwargs: 0.0)
    monkeypatch.setattr(export_onnx, "_convert_saved_model_to_onnx", fail_convert)

    try:
        export_onnx.export_keras_to_onnx(fake_model, output_onnx, overwrite=True)
    except export_onnx.OnnxExportError as exc:
        assert "tf2onnx" in str(exc) or "conversion" in str(exc).lower()
    else:
        raise AssertionError("Expected OnnxExportError when converter fails")

    assert not output_onnx.exists(), "Partial ONNX artifact must be removed on failure"

    service_source = (ROOT / "src" / "vsl" / "service.py").read_text(encoding="utf-8")
    assert "load_model" in service_source
    assert "preprocess_heatmap" in service_source
    gitignore_source = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "*.onnx" in gitignore_source


def test_tsk_018_csv_validation_and_cli_verify_parity_gate(tmp_path, monkeypatch):
    export_onnx = _exporter()

    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("col_a,col_b\n0.1,0.2\n", encoding="utf-8")
    try:
        export_onnx.load_csv_landmarks(bad_csv)
    except export_onnx.OnnxExportError:
        pass
    else:
        raise AssertionError("Expected OnnxExportError for invalid landmark CSV header")

    fake_model = tmp_path / "source.h5"
    fake_model.write_bytes(b"h5")
    out_onnx = tmp_path / "out.onnx"
    report_path = tmp_path / "report.json"

    monkeypatch.setattr(
        export_onnx,
        "export_keras_to_onnx",
        lambda *args, **kwargs: {
            "source_path": str(fake_model),
            "output_path": str(out_onnx),
            "onnx_size_bytes": 123,
            "opset": 15,
        },
    )
    monkeypatch.setattr(
        export_onnx,
        "measure_keras_vs_onnx_parity",
        lambda *args, **kwargs: {
            "parity_passed": False,
            "max_abs_diff": 0.25,
            "argmax_match_count": 10,
            "sample_count": 23,
        },
    )

    exit_code = export_onnx.main(
        [
            "--model-path",
            str(fake_model),
            "--output",
            str(out_onnx),
            "--json-report",
            str(report_path),
            "--verify-parity",
        ]
    )
    assert exit_code != 0
    saved = json.loads(report_path.read_text(encoding="utf-8"))
    assert saved["parity"]["parity_passed"] is False
