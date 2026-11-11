"""Export Keras VSL classifier H5 model to ONNX and verify parity (US-011, TSK-017/TSK-018)."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


class OnnxExportError(RuntimeError):
    """Raised when Keras-to-ONNX conversion, validation, or loading fails."""


def _ensure_repo_root_on_sys_path() -> None:
    root_str = str(ROOT)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


def compute_file_sha256(path: Path) -> str:
    """Return the lowercase SHA-256 hex digest of a file."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _collect_versions() -> dict[str, str]:
    versions: dict[str, str] = {"python": sys.version.split()[0]}
    for package_name in ("tensorflow", "keras", "tf2onnx", "onnx", "onnxruntime", "numpy"):
        try:
            versions[package_name] = importlib.metadata.version(package_name)
        except importlib.metadata.PackageNotFoundError:
            versions[package_name] = "not-installed"
    return versions


def _export_keras_to_saved_model(model_path: Path, saved_model_dir: Path) -> float:
    """Load a Keras HDF5 model and export it to TensorFlow SavedModel format."""
    started = perf_counter()
    try:
        from keras.models import load_model

        keras_model = load_model(str(model_path))
        keras_model.export(str(saved_model_dir))
    except Exception as exc:
        raise OnnxExportError(f"Failed to export Keras H5 to SavedModel: {exc}") from exc
    return round((perf_counter() - started) * 1000, 3)


def _convert_saved_model_to_onnx(
    saved_model_dir: Path,
    onnx_path: Path,
    *,
    opset: int = 15,
) -> float:
    """Invoke tf2onnx.convert on a SavedModel directory to emit an ONNX file."""
    started = perf_counter()
    command = [
        sys.executable,
        "-m",
        "tf2onnx.convert",
        "--saved-model",
        str(saved_model_dir),
        "--output",
        str(onnx_path),
        "--opset",
        str(opset),
    ]
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0 or not onnx_path.is_file():
        detail = (result.stderr or result.stdout or "no output").strip()
        raise OnnxExportError(
            f"tf2onnx conversion failed (exit {result.returncode}): {detail[-600:]}"
        )
    return round((perf_counter() - started) * 1000, 3)


def verify_onnx_session(
    onnx_path: Path,
    *,
    providers: list[str] | None = None,
) -> dict[str, Any]:
    """Load an ONNX artifact with ONNX Runtime and return tensor metadata."""
    resolved_path = Path(onnx_path)
    if not resolved_path.is_file():
        raise OnnxExportError(f"ONNX file does not exist: {resolved_path}")

    started = perf_counter()
    try:
        import onnxruntime as ort

        session = ort.InferenceSession(
            str(resolved_path),
            providers=providers or ["CPUExecutionProvider"],
        )
    except Exception as exc:
        raise OnnxExportError(f"ONNX Runtime failed to load {resolved_path}: {exc}") from exc

    load_ms = round((perf_counter() - started) * 1000, 3)
    inputs = session.get_inputs()
    outputs = session.get_outputs()
    return {
        "providers": session.get_providers(),
        "input_names": [item.name for item in inputs],
        "output_names": [item.name for item in outputs],
        "input_shape": list(inputs[0].shape) if inputs else [],
        "output_shape": list(outputs[0].shape) if outputs else [],
        "ort_load_ms": load_ms,
    }


def export_keras_to_onnx(
    model_path: Path,
    output_path: Path,
    *,
    saved_model_dir: Path | None = None,
    opset: int = 15,
    overwrite: bool = False,
    json_report_path: Path | None = None,
) -> dict[str, Any]:
    """Export a Keras HDF5 model to an ONNX artifact and verify ORT loading."""
    source_path = Path(model_path)
    target_path = Path(output_path)

    if not source_path.is_file():
        raise OnnxExportError(f"Source Keras model does not exist: {source_path}")
    if isinstance(opset, bool) or not isinstance(opset, int) or opset <= 0:
        raise OnnxExportError(f"opset must be a positive integer, got {opset!r}")
    if target_path.exists() and not overwrite:
        raise OnnxExportError(
            f"Refusing to overwrite existing ONNX artifact without --overwrite: {target_path}"
        )

    target_path.parent.mkdir(parents=True, exist_ok=True)
    had_existing_target = target_path.exists()
    temp_dir: tempfile.TemporaryDirectory[str] | None = None

    try:
        if saved_model_dir is None:
            temp_dir = tempfile.TemporaryDirectory(prefix="vsl-saved-model-")
            export_dir = Path(temp_dir.name) / "saved_model"
        else:
            export_dir = Path(saved_model_dir)
            export_dir.mkdir(parents=True, exist_ok=True)

        saved_model_ms = _export_keras_to_saved_model(source_path, export_dir)
        convert_ms = _convert_saved_model_to_onnx(export_dir, target_path, opset=opset)
        session_info = verify_onnx_session(target_path, providers=["CPUExecutionProvider"])
    except OnnxExportError:
        if not had_existing_target or overwrite:
            target_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        if not had_existing_target or overwrite:
            target_path.unlink(missing_ok=True)
        raise OnnxExportError(f"tf2onnx conversion pipeline failed: {exc}") from exc
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()

    report: dict[str, Any] = {
        "source_path": str(source_path),
        "source_sha256": compute_file_sha256(source_path),
        "output_path": str(target_path),
        "h5_size_bytes": source_path.stat().st_size,
        "onnx_size_bytes": target_path.stat().st_size,
        "opset": opset,
        "versions": _collect_versions(),
        "saved_model_export_ms": saved_model_ms,
        "onnx_convert_ms": convert_ms,
        **session_info,
    }

    if json_report_path is not None:
        report_file = Path(json_report_path)
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(f"{json.dumps(report, indent=2)}\n", encoding="utf-8")

    return report


def load_csv_landmarks(csv_path: Path) -> np.ndarray:
    """Load and validate a single 93-column landmark CSV sample."""
    _ensure_repo_root_on_sys_path()
    from src.vsl.landmarks import TOTAL_LANDMARK_COORDS, validate_landmark_columns

    resolved_path = Path(csv_path)
    if not resolved_path.is_file():
        raise OnnxExportError(f"Landmark CSV file does not exist: {resolved_path}")

    with resolved_path.open("r", encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.reader(handle) if any(cell.strip() for cell in row)]

    if len(rows) != 2:
        raise OnnxExportError(
            f"Landmark CSV must contain header plus 1 sample row ({len(rows)} rows): "
            f"{resolved_path}"
        )

    header, data_row = rows[0], rows[1]
    is_valid, reason = validate_landmark_columns(header)
    if not is_valid:
        raise OnnxExportError(f"Invalid landmark columns in {resolved_path}: {reason}")
    if len(data_row) != TOTAL_LANDMARK_COORDS:
        raise OnnxExportError(
            f"Expected {TOTAL_LANDMARK_COORDS} coordinates in {resolved_path}, found {len(data_row)}"
        )

    try:
        values = np.asarray([float(cell) for cell in data_row], dtype=np.float64)
    except ValueError as exc:
        raise OnnxExportError(f"Non-numeric landmark coordinate in {resolved_path}: {exc}") from exc

    if not np.all(np.isfinite(values)):
        raise OnnxExportError(f"Non-finite landmark coordinate in {resolved_path}")
    return values


def load_sample_heatmap_batch(
    data_dir: Path | None = None,
    sample_filename: str = "1.csv",
) -> tuple[tuple[str, ...], np.ndarray]:
    """Build the canonical 23-class Caffe-preprocessed float32 batch (BR-006)."""
    _ensure_repo_root_on_sys_path()
    from src.vsl.config import get_data_dir
    from src.vsl.heatmap import create_heatmap
    from src.vsl.labels import VIETNAMESE_ALPHABET
    from src.vsl.service import preprocess_heatmap

    resolved_data_dir = Path(data_dir) if data_dir is not None else get_data_dir()
    if not resolved_data_dir.is_dir():
        raise OnnxExportError(f"Landmark dataset directory does not exist: {resolved_data_dir}")

    heatmaps = []
    for label in VIETNAMESE_ALPHABET:
        csv_path = resolved_data_dir / label / sample_filename
        landmarks = load_csv_landmarks(csv_path)
        heatmaps.append(create_heatmap(landmarks))

    raw_batch = np.stack(heatmaps, axis=0)
    preprocessed = preprocess_heatmap(raw_batch)
    return VIETNAMESE_ALPHABET, np.asarray(preprocessed, dtype=np.float32)


def measure_keras_vs_onnx_parity(
    model_path: Path,
    onnx_path: Path,
    *,
    data_dir: Path | None = None,
    providers: list[str] | None = None,
    repeats: int = 5,
    tolerance: float = 1e-4,
) -> dict[str, Any]:
    """Compare Keras H5 vs ONNX Runtime outputs, sizes, and local load/inference timings."""
    if repeats < 1:
        raise OnnxExportError(f"repeats must be >= 1, got {repeats}")

    source_path = Path(model_path)
    target_path = Path(onnx_path)
    if not source_path.is_file():
        raise OnnxExportError(f"Source Keras model does not exist: {source_path}")
    if not target_path.is_file():
        raise OnnxExportError(f"ONNX model does not exist: {target_path}")

    import onnxruntime as ort
    from keras.models import load_model

    active_providers = providers or ["CPUExecutionProvider"]
    labels, batch = load_sample_heatmap_batch(data_dir=data_dir)

    t0 = perf_counter()
    keras_model = load_model(str(source_path))
    keras_load_ms = (perf_counter() - t0) * 1000.0

    t1 = perf_counter()
    session = ort.InferenceSession(str(target_path), providers=active_providers)
    ort_load_ms = (perf_counter() - t1) * 1000.0

    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name

    # Warm up both engines once before timing steady-state inference.
    keras_preds = np.asarray(keras_model(batch, training=False).numpy(), dtype=np.float32)
    onnx_preds = np.asarray(session.run([output_name], {input_name: batch})[0], dtype=np.float32)

    keras_latencies_ms: list[float] = []
    onnx_latencies_ms: list[float] = []
    for _ in range(repeats):
        start_k = perf_counter()
        _ = keras_model(batch, training=False).numpy()
        keras_latencies_ms.append((perf_counter() - start_k) * 1000.0)

        start_o = perf_counter()
        _ = session.run([output_name], {input_name: batch})[0]
        onnx_latencies_ms.append((perf_counter() - start_o) * 1000.0)

    abs_diff = np.abs(keras_preds - onnx_preds)
    max_abs_diff = float(np.max(abs_diff))
    mean_abs_diff = float(np.mean(abs_diff))

    keras_argmax = [int(idx) for idx in np.argmax(keras_preds, axis=1)]
    onnx_argmax = [int(idx) for idx in np.argmax(onnx_preds, axis=1)]
    argmax_match_count = sum(1 for k, o in zip(keras_argmax, onnx_argmax) if k == o)
    expected_match_count = sum(1 for idx, o in enumerate(onnx_argmax) if idx == o)

    h5_size = source_path.stat().st_size
    onnx_size = target_path.stat().st_size
    keras_median_batch_ms = statistics.median(keras_latencies_ms)
    onnx_median_batch_ms = statistics.median(onnx_latencies_ms)
    batch_size = len(labels)

    return {
        "providers": session.get_providers(),
        "sample_count": batch_size,
        "repeats": repeats,
        "tolerance": tolerance,
        "parity_passed": (max_abs_diff < tolerance) and (argmax_match_count == batch_size),
        "max_abs_diff": max_abs_diff,
        "mean_abs_diff": mean_abs_diff,
        "argmax_match_count": argmax_match_count,
        "expected_label_match_count": expected_match_count,
        "h5_size_bytes": h5_size,
        "onnx_size_bytes": onnx_size,
        "onnx_to_h5_size_ratio": round(onnx_size / h5_size, 4),
        "keras_load_ms": round(keras_load_ms, 2),
        "ort_load_ms": round(ort_load_ms, 2),
        "keras_batch_infer_median_ms": round(keras_median_batch_ms, 2),
        "onnx_batch_infer_median_ms": round(onnx_median_batch_ms, 2),
        "keras_per_sample_median_ms": round(keras_median_batch_ms / batch_size, 3),
        "onnx_per_sample_median_ms": round(onnx_median_batch_ms / batch_size, 3),
    }


def _build_parser() -> argparse.ArgumentParser:
    _ensure_repo_root_on_sys_path()
    from src.vsl.config import get_model_path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model-path",
        type=Path,
        default=get_model_path(),
        help="Path to the source Keras .h5 model (defaults to get_model_path())",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "models" / "model.onnx",
        help="Destination path for the exported .onnx model",
    )
    parser.add_argument(
        "--saved-model-dir",
        type=Path,
        default=None,
        help="Optional directory for intermediate SavedModel (defaults to temp dir)",
    )
    parser.add_argument(
        "--opset",
        type=int,
        default=15,
        help="Target ONNX opset version (default: 15)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting an existing .onnx output file",
    )
    parser.add_argument(
        "--json-report",
        type=Path,
        default=None,
        help="Optional path to write JSON export metadata",
    )
    parser.add_argument(
        "--verify-parity",
        action="store_true",
        help="Run CPUExecutionProvider parity and timing comparison against the H5 model",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=5,
        help="Number of warmed-up batch inference runs when --verify-parity is set",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for Keras-to-ONNX export."""
    args = _build_parser().parse_args(argv)
    try:
        report = export_keras_to_onnx(
            args.model_path,
            args.output,
            saved_model_dir=args.saved_model_dir,
            opset=args.opset,
            overwrite=args.overwrite,
            json_report_path=args.json_report,
        )
        if args.verify_parity:
            parity = measure_keras_vs_onnx_parity(
                args.model_path,
                args.output,
                repeats=args.repeats,
            )
            report["parity"] = parity
            if args.json_report is not None:
                report_file = Path(args.json_report)
                report_file.write_text(f"{json.dumps(report, indent=2)}\n", encoding="utf-8")
            if not parity["parity_passed"]:
                raise OnnxExportError(
                    f"Parity check failed: max_abs_diff={parity['max_abs_diff']}, "
                    f"argmax_match_count={parity['argmax_match_count']}/{parity['sample_count']}"
                )
    except OnnxExportError as exc:
        print(f"ONNX export failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"Exported ONNX model to {report['output_path']} "
        f"({report['onnx_size_bytes']} bytes, opset {report['opset']})"
    )
    if "parity" in report:
        parity = report["parity"]
        print(
            f"Parity PASSED: max_abs_diff={parity['max_abs_diff']:.3e}, "
            f"argmax={parity['argmax_match_count']}/{parity['sample_count']}, "
            f"keras_load={parity['keras_load_ms']}ms, ort_load={parity['ort_load_ms']}ms, "
            f"keras_batch={parity['keras_batch_infer_median_ms']}ms, "
            f"onnx_batch={parity['onnx_batch_infer_median_ms']}ms"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
