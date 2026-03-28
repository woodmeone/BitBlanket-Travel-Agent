"""Export a stable runtime-doctor contract snapshot for review and regression checks."""
# ruff: noqa: E402

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
from pathlib import Path

if __package__:
    _bootstrap_paths = importlib.import_module(f"{__package__}.bootstrap_paths")
else:
    _bootstrap_paths_path = Path(__file__).with_name("bootstrap_paths.py")
    _bootstrap_paths_spec = importlib.util.spec_from_file_location("bootstrap_paths", _bootstrap_paths_path)
    if _bootstrap_paths_spec is None or _bootstrap_paths_spec.loader is None:
        raise ImportError(f"Unable to load bootstrap_paths from {_bootstrap_paths_path}")
    _bootstrap_paths = importlib.util.module_from_spec(_bootstrap_paths_spec)
    _bootstrap_paths_spec.loader.exec_module(_bootstrap_paths)

ROOT = _bootstrap_paths.PROJECT_ROOT
ensure_project_paths = _bootstrap_paths.ensure_project_paths
ensure_project_paths()

from scripts.runtime_ops_contracts import build_runtime_doctor_contract_snapshot


DEFAULT_OUTPUT = ROOT / "docs" / "reference" / "runtime-doctor.snapshot.json"


def export_runtime_doctor_snapshot(output_path: Path = DEFAULT_OUTPUT) -> Path:
    """Write the stable runtime-doctor contract snapshot to disk."""

    snapshot = build_runtime_doctor_contract_snapshot()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def build_parser() -> argparse.ArgumentParser:
    """Construct the CLI parser for runtime-doctor snapshot export."""

    parser = argparse.ArgumentParser(description="Export runtime-doctor contract snapshot.")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output path for exported runtime-doctor snapshot.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for runtime-doctor snapshot export."""

    parser = build_parser()
    args = parser.parse_args(argv)
    target = export_runtime_doctor_snapshot(Path(args.output))
    print(f"Runtime doctor snapshot exported to: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
