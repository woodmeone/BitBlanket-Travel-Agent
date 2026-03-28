"""Unit tests for runtime-doctor snapshot export utility."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.export_runtime_doctor_snapshot import export_runtime_doctor_snapshot


def test_export_runtime_doctor_snapshot_writes_stable_contract_shape(tmp_path: Path) -> None:
    """Export the runtime-doctor snapshot and preserve the expected contract shape."""

    output_path = tmp_path / "runtime-doctor.snapshot.json"
    written_path = export_runtime_doctor_snapshot(output_path)

    assert written_path == output_path
    snapshot = json.loads(output_path.read_text(encoding="utf-8"))
    assert snapshot["status"] == "ok"
    assert snapshot["checked_at"] == "<iso8601-utc>"
    assert "server_config" in snapshot["checks"]
    assert "http_probe" in snapshot["checks"]
