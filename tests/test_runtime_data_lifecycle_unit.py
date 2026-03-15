"""Unit tests for runtime backup, restore, and prune maintenance scripts."""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.runtime_backup import create_runtime_backup
from scripts.runtime_prune import prune_runtime_data
from scripts.runtime_restore import restore_runtime_backup


def _write_runtime_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_create_runtime_backup_archives_runtime_files(tmp_path):
    _write_runtime_file(tmp_path / "data" / "sessions" / "sessions.json", '{"s1": {"session_id": "s1"}}')
    _write_runtime_file(tmp_path / "data" / "agent_memory.json", '{"sessions": {}}')

    archive_path, manifest = create_runtime_backup(
        project_root=tmp_path,
        output_dir=tmp_path / "artifacts" / "runtime_backups",
        label="unit",
    )

    assert archive_path.exists()
    assert archive_path.suffix == ".zip"
    assert len(manifest["files"]) >= 2
    archived_paths = {item["relative_path"] for item in manifest["files"]}
    assert "data/sessions/sessions.json" in archived_paths
    assert "data/agent_memory.json" in archived_paths


def test_restore_runtime_backup_recovers_modified_files(tmp_path):
    sessions_path = tmp_path / "data" / "sessions" / "sessions.json"
    _write_runtime_file(sessions_path, '{"s1": {"session_id": "s1", "messages": []}}')

    archive_path, _ = create_runtime_backup(
        project_root=tmp_path,
        output_dir=tmp_path / "artifacts" / "runtime_backups",
    )

    _write_runtime_file(sessions_path, '{"broken": true}')
    result = restore_runtime_backup(
        archive_path=archive_path,
        project_root=tmp_path,
        create_safety_backup=False,
    )

    restored = json.loads(sessions_path.read_text(encoding="utf-8"))
    assert "s1" in restored
    assert result["safety_archive"] is None
    assert "data/sessions/sessions.json" in result["restored_files"]


def test_prune_runtime_data_cleans_backups_sessions_failures_and_vacuums(tmp_path):
    backups_dir = tmp_path / "artifacts" / "runtime_backups"
    backups_dir.mkdir(parents=True, exist_ok=True)
    old_backup = backups_dir / "runtime_backup_old.zip"
    mid_backup = backups_dir / "runtime_backup_mid.zip"
    new_backup = backups_dir / "runtime_backup_new.zip"
    for path in (old_backup, mid_backup, new_backup):
        path.write_bytes(b"test")

    now = datetime.now(timezone.utc)
    old_ts = (now - timedelta(days=10)).timestamp()
    mid_ts = (now - timedelta(days=5)).timestamp()
    new_ts = (now - timedelta(days=1)).timestamp()
    old_backup.touch()
    mid_backup.touch()
    new_backup.touch()
    import os

    os.utime(old_backup, (old_ts, old_ts))
    os.utime(mid_backup, (mid_ts, mid_ts))
    os.utime(new_backup, (new_ts, new_ts))

    sessions_path = tmp_path / "data" / "sessions" / "sessions.json"
    sessions_path.parent.mkdir(parents=True, exist_ok=True)
    sessions_payload = {
        "old": {
            "session_id": "old",
            "created_at": (now - timedelta(days=30)).isoformat(),
            "last_active": (now - timedelta(days=30)).isoformat(),
            "message_count": 1,
            "messages": [],
            "name": "old",
            "model_id": "m",
            "user_preferences": {},
        },
        "new": {
            "session_id": "new",
            "created_at": now.isoformat(),
            "last_active": now.isoformat(),
            "message_count": 1,
            "messages": [],
            "name": "new",
            "model_id": "m",
            "user_preferences": {},
        },
    }
    sessions_path.write_text(json.dumps(sessions_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    failure_path = tmp_path / "data" / "runtime_failure_clusters.jsonl"
    failure_path.parent.mkdir(parents=True, exist_ok=True)
    failure_lines = [
        json.dumps({"ts": (now - timedelta(days=15)).isoformat(), "clusters": {"timeout": 1}}, ensure_ascii=False),
        json.dumps({"ts": now.isoformat(), "clusters": {"timeout": 0}}, ensure_ascii=False),
    ]
    failure_path.write_text("\n".join(failure_lines) + "\n", encoding="utf-8")

    checkpoint_path = tmp_path / "data" / "langgraph_checkpoints.sqlite3"
    with sqlite3.connect(checkpoint_path) as connection:
        connection.execute("CREATE TABLE demo(id INTEGER PRIMARY KEY)")
        connection.commit()

    result = prune_runtime_data(
        project_root=tmp_path,
        backups_dir=backups_dir,
        keep_latest_backups=1,
        max_backup_age_days=7,
        max_session_age_seconds=24 * 3600,
        max_failure_age_days=7,
        vacuum_checkpoints_enabled=True,
    )

    remaining_archives = {path.name for path in backups_dir.glob("runtime_backup_*.zip")}
    assert remaining_archives == {"runtime_backup_new.zip"}
    pruned_sessions = json.loads(sessions_path.read_text(encoding="utf-8"))
    assert "new" in pruned_sessions
    assert "old" not in pruned_sessions
    remaining_failure_lines = [line for line in failure_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(remaining_failure_lines) == 1
    assert result["deleted_sessions"] == 1
    assert result["deleted_failure_records"] == 1
    assert result["vacuumed_checkpoints"] is True
