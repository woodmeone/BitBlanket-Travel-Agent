"""Unit tests for extracted memory persistence helpers."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.travel_agent.memory import MemoryPersistenceStore  # noqa: E402


def test_memory_persistence_store_recovers_from_backup_and_restores_primary(tmp_path):
    persist_path = tmp_path / "agent_memory.json"
    store = MemoryPersistenceStore(str(persist_path))
    payload = {
        "session-1": {
            "summary": "trip summary",
            "profile": {"schema_version": 2},
            "messages": [{"role": "user", "content": "plan a trip", "timestamp": "2026-03-26T00:00:00"}],
        }
    }

    store.write_snapshot(payload)

    assert persist_path.exists()
    assert Path(store.backup_path or "").exists()

    persist_path.write_text("{broken-json", encoding="utf-8")
    recovered_payload, recovered_from_backup = store.load_snapshot()

    assert recovered_from_backup is True
    assert recovered_payload == payload

    store.restore_primary(recovered_payload or {})
    restored = json.loads(persist_path.read_text(encoding="utf-8"))
    assert restored == payload
