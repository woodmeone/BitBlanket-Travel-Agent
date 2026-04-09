"""Unit tests for the SQL runtime backfill script."""

from __future__ import annotations

import json

import pytest

from agent.travel_agent.memory.postgres_memory_session_repository import PostgresMemorySessionRepository
from scripts.runtime_backfill_postgres import backfill_runtime_snapshots
from moyuan_web.repositories.postgres_share_link_repository import PostgresShareLinkRepository
from moyuan_web.repositories.session_repository_postgres import PostgresSessionRepository


def _write_json(path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


@pytest.mark.asyncio
async def test_backfill_runtime_snapshots_imports_file_backed_runtime_data(tmp_path):
    sessions_file = tmp_path / "sessions.json"
    share_links_file = tmp_path / "share_links.json"
    agent_memory_file = tmp_path / "agent_memory.json"
    database_url = f"sqlite+pysqlite:///{tmp_path / 'backfill.db'}"

    _write_json(
        sessions_file,
        {
            "session-1": {
                "session_id": "session-1",
                "created_at": "2026-04-04T00:00:00+00:00",
                "last_active": "2026-04-04T00:00:00+00:00",
                "message_count": 1,
                "name": "Hangzhou",
                "model_id": "demo-model",
                "messages": [{"role": "user", "content": "plan"}],
                "user_preferences": {"days": 2},
            }
        },
    )
    _write_json(
        share_links_file,
        {
            "share123456": {
                "share_id": "share123456",
                "title": "Hangzhou",
                "content": "Plan content",
                "html_content": "<html>Plan</html>",
                "delivery_bundle": {"schemaVersion": "2026-03-29"},
                "created_at": "2026-04-04T00:00:00+00:00",
            }
        },
    )
    _write_json(
        agent_memory_file,
        {
            "session-1": {
                "summary": "trip summary",
                "profile": {"schema_version": 2, "budget_hint": "5000元"},
                "messages": [{"role": "user", "content": "预算5000元", "timestamp": "2026-04-04T00:00:00+00:00"}],
            }
        },
    )

    first_import = await backfill_runtime_snapshots(
        database_url=database_url,
        sessions_file=sessions_file,
        share_links_file=share_links_file,
        agent_memory_file=agent_memory_file,
    )
    second_import = await backfill_runtime_snapshots(
        database_url=database_url,
        sessions_file=sessions_file,
        share_links_file=share_links_file,
        agent_memory_file=agent_memory_file,
    )

    assert first_import == {"sessions_imported": 1, "share_links_imported": 1, "memory_sessions_imported": 1}
    assert second_import == {"sessions_imported": 1, "share_links_imported": 1, "memory_sessions_imported": 1}

    session_repository = PostgresSessionRepository(database_url, ensure_schema_ready=False)
    share_repository = PostgresShareLinkRepository(database_url, ensure_schema_ready=False)
    memory_repository = PostgresMemorySessionRepository(database_url, ensure_schema_ready=False)

    sessions = await session_repository.list_all(include_empty=True)
    share_record = await share_repository.get("share123456")
    memory_snapshot, recovered_from_backup = memory_repository.load_snapshot()

    assert len(sessions) == 1
    assert sessions[0]["name"] == "Hangzhou"
    assert share_record is not None
    assert share_record["content"] == "Plan content"
    assert recovered_from_backup is False
    assert memory_snapshot == {
        "session-1": {
            "summary": "trip summary",
            "profile": {"schema_version": 2, "budget_hint": "5000元"},
            "messages": [{"role": "user", "content": "预算5000元", "timestamp": "2026-04-04T00:00:00+00:00"}],
        }
    }
