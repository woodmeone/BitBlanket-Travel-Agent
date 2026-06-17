"""Unit tests for the compatibility-first SQL repository baseline."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from moyuan_web.persistence import (
    build_sync_engine,
    memory_sessions_table,
    session_messages_table,
    sessions_table,
)
from moyuan_web.repositories.postgres_share_link_repository import PostgresShareLinkRepository
from moyuan_web.repositories.session_repository_postgres import PostgresSessionRepository
from agent.travel_agent.memory.postgres_memory_session_repository import PostgresMemorySessionRepository


@pytest.mark.asyncio
async def test_postgres_session_repository_supports_sqlite_crud_and_cleanup(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'sessions.db'}"
    repository = PostgresSessionRepository(database_url)

    active_session_id = await repository.create(
        {
            "session_id": "session-active",
            "name": "Weekend",
            "model_id": "demo-model",
            "messages": [{"role": "user", "content": "hello"}],
            "user_preferences": {"days": 2},
        }
    )
    await repository.create(
        {
            "session_id": "session-expired",
            "created_at": "2020-01-01T00:00:00+00:00",
            "last_active": "2020-01-01T00:00:00+00:00",
            "message_count": 0,
            "name": "Expired",
            "model_id": "demo-model",
            "messages": [],
            "user_preferences": {},
        }
    )

    loaded = await repository.get(active_session_id)
    assert loaded is not None
    assert loaded["messages"][0]["content"] == "hello"
    assert loaded["user_preferences"]["days"] == 2

    await repository.update(active_session_id, {"name": "Weekend Updated", "message_count": 1})
    updated = await repository.get(active_session_id)
    assert updated is not None
    assert updated["name"] == "Weekend Updated"

    listed = await repository.list_all(include_empty=True)
    assert [item["session_id"] for item in listed] == ["session-active", "session-expired"]

    deleted = await repository.cleanup_expired(max_age_seconds=60)
    assert deleted == 1
    assert await repository.get("session-expired") is None

    engine = build_sync_engine(database_url)
    with engine.begin() as connection:
        message_rows = connection.execute(
            select(session_messages_table.c.session_id, session_messages_table.c.sequence)
            .order_by(session_messages_table.c.sequence.asc())
        ).mappings().all()
        shadow_messages = connection.execute(
            select(sessions_table.c.messages).where(sessions_table.c.session_id == "session-active")
        ).scalar_one()
    assert message_rows == [{"session_id": "session-active", "sequence": 0}]
    assert shadow_messages == []
    engine.dispose()


@pytest.mark.asyncio
async def test_postgres_share_link_repository_upserts_records(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'share-links.db'}"
    repository = PostgresShareLinkRepository(database_url)

    record = {
        "share_id": "share123456",
        "title": "Weekend",
        "content": "Hangzhou trip",
        "html_content": "<html>Hangzhou</html>",
        "delivery_bundle": {"schemaVersion": "2026-03-29", "share": {"title": "Weekend", "content": "Hangzhou"}},
        "created_at": "2026-04-04T00:00:00+00:00",
    }

    await repository.save(record)
    await repository.save({**record, "title": "Weekend Updated"})

    loaded = await repository.get("share123456")
    assert loaded is not None
    assert loaded["title"] == "Weekend Updated"
    assert loaded["delivery_bundle"]["schemaVersion"] == "2026-03-29"

    all_links = await repository.list_all()
    assert list(all_links) == ["share123456"]


def test_postgres_memory_session_repository_round_trips_snapshots(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agent-memory.db'}"
    repository = PostgresMemorySessionRepository(database_url)

    payload = {
        "memory-session-1": {
            "summary": "trip summary",
            "profile": {"schema_version": 2, "budget_hint": "5000元"},
            "messages": [{"role": "user", "content": "预算5000元", "timestamp": "2026-04-04T00:00:00+00:00"}],
        }
    }

    repository.write_snapshot(payload)
    loaded, recovered_from_backup = repository.load_snapshot()

    assert recovered_from_backup is False
    assert loaded == payload

    engine = build_sync_engine(database_url)
    with engine.begin() as connection:
        rows = connection.execute(select(memory_sessions_table.c.session_id)).mappings().all()
    assert rows == [{"session_id": "memory-session-1"}]
    engine.dispose()
