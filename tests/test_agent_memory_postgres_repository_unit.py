"""Unit tests for SQL-backed agent-memory persistence integration."""

from __future__ import annotations

import pytest

from agent.travel_agent.graph.memory_integration import AgentMemoryManager
from agent.travel_agent.memory import MemoryPersistenceStore, PostgresMemorySessionRepository


@pytest.mark.asyncio
async def test_agent_memory_manager_persists_and_reloads_from_sql_repository(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'memory-manager.db'}"

    writer = AgentMemoryManager(
        max_history=5,
        summary_threshold=5,
        persist_path=None,
        persistence_store=MemoryPersistenceStore(
            persist_path=None,
            repository=PostgresMemorySessionRepository(database_url),
        ),
        session_ttl_seconds=3600,
        max_sessions=10,
    )
    await writer.add_message("session-memory", "user", "预算5000元，玩3天，偏好美食")

    reader = AgentMemoryManager(
        max_history=5,
        summary_threshold=5,
        persist_path=None,
        persistence_store=MemoryPersistenceStore(
            persist_path=None,
            repository=PostgresMemorySessionRepository(database_url, ensure_schema_ready=False),
        ),
        session_ttl_seconds=3600,
        max_sessions=10,
    )

    profile = await reader.get_profile("session-memory")
    messages = await reader.get_recent_messages("session-memory")

    assert profile.get("budget_hint") == "5000元"
    assert profile.get("days_hint") == 3
    assert "美食" in profile.get("interests", [])
    assert len(messages) == 1
    assert messages[0].content == "预算5000元，玩3天，偏好美食"
