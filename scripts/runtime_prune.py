"""Prune old runtime backups, stale session records, and aged failure telemetry."""
# ruff: noqa: E402

from __future__ import annotations

import argparse
import asyncio
import importlib
import importlib.util
import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

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

from scripts.runtime_data_utils import DEFAULT_BACKUP_DIR, parse_utc_iso
from moyuan_web.repositories.file_session_repository import FileSessionRepository


def resolve_checkpointer_config(**kwargs):
    """Lazily load checkpoint config resolver so prune stays lightweight."""

    from agent.travel_agent.runtime_sources import resolve_checkpointer_config as _resolve_checkpointer_config

    return _resolve_checkpointer_config(**kwargs)


def create_checkpointer(config):
    """Lazily construct checkpoint backend instances for maintenance routines."""

    from agent.travel_agent.runtime_sources import create_checkpointer as _create_checkpointer

    return _create_checkpointer(config)


def close_checkpointer(checkpointer) -> None:
    """Lazily release checkpoint backend resources after maintenance."""

    from agent.travel_agent.runtime_sources import close_checkpointer as _close_checkpointer

    _close_checkpointer(checkpointer)


def prune_backup_archives(
    backups_dir: Path,
    *,
    keep_latest: int = 10,
    max_age_days: int | None = None,
) -> list[str]:
    """Delete old backup archives by count and optional age threshold."""
    if not backups_dir.exists():
        return []

    archives = sorted(
        [path for path in backups_dir.glob("runtime_backup_*.zip") if path.is_file()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    now = datetime.now(timezone.utc)
    deleted: list[str] = []
    for index, archive in enumerate(archives):
        too_many = index >= keep_latest
        too_old = False
        if max_age_days is not None:
            modified_at = datetime.fromtimestamp(archive.stat().st_mtime, tz=timezone.utc)
            too_old = modified_at < now - timedelta(days=max_age_days)
        if not too_many and not too_old:
            continue
        archive.unlink(missing_ok=True)
        deleted.append(str(archive))
    return deleted


async def prune_sessions_file(sessions_path: Path, *, max_age_seconds: int) -> int:
    """Remove expired sessions from persisted session storage."""
    if not sessions_path.exists():
        return 0
    repository = FileSessionRepository(str(sessions_path))
    return await repository.cleanup_expired(max_age_seconds)


def prune_failure_clusters(file_path: Path, *, max_age_days: int) -> int:
    """Rewrite failure-cluster JSONL file and drop old entries by timestamp."""
    if not file_path.exists():
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    kept_lines: list[str] = []
    removed = 0
    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError:
            kept_lines.append(raw_line)
            continue
        created_at = parse_utc_iso(payload.get("ts"))
        if created_at is not None and created_at < cutoff:
            removed += 1
            continue
        kept_lines.append(json.dumps(payload, ensure_ascii=False))

    if kept_lines:
        file_path.write_text("\n".join(kept_lines) + "\n", encoding="utf-8")
    else:
        file_path.write_text("", encoding="utf-8")
    return removed


def vacuum_checkpoint_db(db_path: Path) -> bool:
    """Run SQLite VACUUM on checkpoint database when it exists."""
    if not db_path.exists():
        return False
    with sqlite3.connect(str(db_path)) as connection:
        connection.execute("VACUUM")
        connection.commit()
    return True


def compact_checkpoint_store(checkpointer: Any) -> dict[str, Any]:
    """Trigger backend compaction across known checkpoint namespaces."""

    namespaces_touched = 0
    storage = getattr(checkpointer, "storage", None)
    if isinstance(storage, dict):
        for thread_id, namespace_map in storage.items():
            if not isinstance(namespace_map, dict):
                continue
            for checkpoint_ns in list(namespace_map.keys()):
                if hasattr(checkpointer, "get_checkpoint_count"):
                    checkpointer.get_checkpoint_count(str(thread_id), str(checkpoint_ns))
                    namespaces_touched += 1
    return {
        "performed": True,
        "namespaces_touched": namespaces_touched,
    }


def prune_runtime_data(
    project_root: Path = ROOT,
    *,
    backups_dir: Path = DEFAULT_BACKUP_DIR,
    keep_latest_backups: int = 10,
    max_backup_age_days: int | None = None,
    max_session_age_seconds: int | None = None,
    max_failure_age_days: int | None = None,
    vacuum_checkpoints_enabled: bool = False,
    checkpoint_backend: str | None = None,
    checkpoint_target: str | None = None,
) -> dict[str, Any]:
    """Apply configured pruning actions and return structured maintenance summary."""
    data_dir = project_root / "data"
    result: dict[str, Any] = {
        "deleted_backups": prune_backup_archives(
            backups_dir,
            keep_latest=keep_latest_backups,
            max_age_days=max_backup_age_days,
        ),
        "deleted_sessions": 0,
        "deleted_failure_records": 0,
        "vacuumed_checkpoints": False,
        "checkpoint_maintenance": {
            "backend": None,
            "action": None,
            "performed": False,
            "namespaces_touched": 0,
        },
    }

    if max_session_age_seconds is not None:
        sessions_path = data_dir / "sessions" / "sessions.json"
        result["deleted_sessions"] = asyncio.run(
            prune_sessions_file(sessions_path, max_age_seconds=max_session_age_seconds)
        )

    if max_failure_age_days is not None:
        failure_path = data_dir / "runtime_failure_clusters.jsonl"
        result["deleted_failure_records"] = prune_failure_clusters(
            failure_path,
            max_age_days=max_failure_age_days,
        )

    if vacuum_checkpoints_enabled:
        checkpoint_config = resolve_checkpointer_config(
            backend_override=checkpoint_backend,
            target_override=checkpoint_target or str(data_dir / "langgraph_checkpoints.sqlite3"),
        )
        result["checkpoint_maintenance"]["backend"] = checkpoint_config.backend
        if checkpoint_config.backend == "sqlite" and not Path(checkpoint_config.target).exists():
            result["checkpoint_maintenance"]["action"] = "compact+vacuum"
        else:
            checkpointer = create_checkpointer(checkpoint_config)
            try:
                maintenance = compact_checkpoint_store(checkpointer)
            finally:
                close_checkpointer(checkpointer)
            result["checkpoint_maintenance"].update(maintenance)
            if checkpoint_config.backend == "sqlite":
                result["checkpoint_maintenance"]["action"] = "compact+vacuum"
                result["vacuumed_checkpoints"] = vacuum_checkpoint_db(Path(checkpoint_config.target))
                result["checkpoint_maintenance"]["performed"] = bool(
                    result["checkpoint_maintenance"]["performed"] or result["vacuumed_checkpoints"]
                )
            else:
                result["checkpoint_maintenance"]["action"] = "compact"

    return result


def build_parser() -> argparse.ArgumentParser:
    """Construct CLI parser for runtime pruning utility."""
    parser = argparse.ArgumentParser(description="Prune old runtime data and maintenance artifacts.")
    parser.add_argument(
        "--backups-dir",
        default=str(DEFAULT_BACKUP_DIR),
        help="Directory where runtime backups are stored.",
    )
    parser.add_argument(
        "--keep-latest-backups",
        type=int,
        default=10,
        help="Always keep at least this many newest backup archives.",
    )
    parser.add_argument(
        "--max-backup-age-days",
        type=int,
        default=None,
        help="Delete runtime backups older than this age in days.",
    )
    parser.add_argument(
        "--max-session-age-seconds",
        type=int,
        default=None,
        help="Delete sessions inactive for longer than this many seconds.",
    )
    parser.add_argument(
        "--max-failure-age-days",
        type=int,
        default=None,
        help="Delete runtime failure-cluster records older than this many days.",
    )
    parser.add_argument(
        "--vacuum-checkpoints",
        action="store_true",
        help="Run checkpoint backend maintenance. SQLite backends also execute VACUUM.",
    )
    parser.add_argument(
        "--checkpoint-backend",
        choices=("sqlite", "postgres"),
        default=None,
        help="Explicit checkpoint backend override used with --vacuum-checkpoints.",
    )
    parser.add_argument(
        "--checkpoint-db",
        default=None,
        help="Checkpoint SQLite path or PostgreSQL DSN override used with --vacuum-checkpoints.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for runtime prune utility."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = prune_runtime_data(
            project_root=ROOT,
            backups_dir=Path(args.backups_dir),
            keep_latest_backups=max(1, int(args.keep_latest_backups)),
            max_backup_age_days=args.max_backup_age_days,
            max_session_age_seconds=args.max_session_age_seconds,
            max_failure_age_days=args.max_failure_age_days,
            vacuum_checkpoints_enabled=bool(args.vacuum_checkpoints),
            checkpoint_backend=str(args.checkpoint_backend) if args.checkpoint_backend else None,
            checkpoint_target=str(args.checkpoint_db) if args.checkpoint_db else None,
        )
    except Exception as exc:
        print(f"Runtime prune failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
