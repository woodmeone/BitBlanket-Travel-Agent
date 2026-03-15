"""Create zip backups for runtime data such as sessions, memory, and checkpoints."""
# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.runtime_data_utils import (
    DEFAULT_BACKUP_DIR,
    build_manifest,
    discover_runtime_files,
    snapshot_timestamp_slug,
)


def create_runtime_backup(
    project_root: Path = ROOT,
    output_dir: Path = DEFAULT_BACKUP_DIR,
    label: str | None = None,
) -> tuple[Path, dict[str, Any]]:
    """Create one zip archive containing current runtime files plus manifest metadata."""
    files = discover_runtime_files(project_root)
    if not files:
        raise FileNotFoundError("No runtime files were found to back up.")

    output_dir.mkdir(parents=True, exist_ok=True)
    safe_label = ""
    if label:
        safe_label = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in label).strip("-")
    stem = f"runtime_backup_{snapshot_timestamp_slug()}"
    if safe_label:
        stem = f"{stem}_{safe_label}"
    archive_path = output_dir / f"{stem}.zip"

    manifest = build_manifest(project_root, files)
    manifest["archive_name"] = archive_path.name

    with zipfile.ZipFile(archive_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        for item in files:
            archive.write(item["absolute_path"], arcname=item["relative_path"])
    return archive_path, manifest


def build_parser() -> argparse.ArgumentParser:
    """Construct CLI parser for runtime backup utility."""
    parser = argparse.ArgumentParser(description="Create runtime data backup archive.")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_BACKUP_DIR),
        help="Directory where runtime backup archives will be written.",
    )
    parser.add_argument(
        "--label",
        default=None,
        help="Optional label appended to the backup archive name.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for creating runtime backup archives."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        archive_path, manifest = create_runtime_backup(
            project_root=ROOT,
            output_dir=Path(args.output_dir),
            label=str(args.label) if args.label else None,
        )
    except Exception as exc:
        print(f"Runtime backup failed: {exc}", file=sys.stderr)
        return 1

    print(f"Runtime backup archive: {archive_path}")
    print(f"Backed up files: {len(manifest.get('files', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
