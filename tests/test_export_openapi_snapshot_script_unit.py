"""Unit tests for OpenAPI snapshot export utility."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.export_openapi_snapshot import export_openapi_snapshot


def test_export_openapi_snapshot_writes_sorted_schema(tmp_path):
    output_path = tmp_path / "openapi.snapshot.json"
    written_path = export_openapi_snapshot(output_path=output_path, base_url="http://example.test")

    assert written_path == output_path
    assert output_path.exists()

    schema = json.loads(output_path.read_text(encoding="utf-8"))
    assert schema["openapi"].startswith("3.")
    assert schema["servers"][0]["url"] == "http://example.test"
    assert "/api/health" in schema["paths"]
    assert "/api/chat/stream" in schema["paths"]
