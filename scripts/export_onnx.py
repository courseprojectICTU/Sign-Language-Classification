"""Export the Keras VSL classifier H5 model to ONNX via SavedModel (US-011, TSK-017)."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from time import perf_counter
from typing import Any

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
    except OnnxExportError as exc:
        print(f"ONNX export failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"Exported ONNX model to {report['output_path']} "
        f"({report['onnx_size_bytes']} bytes, opset {report['opset']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
