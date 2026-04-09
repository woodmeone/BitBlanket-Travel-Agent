"""Local ASGI smoke tests for the postgres backend wiring."""

from __future__ import annotations

import httpx
import pytest

from config import server_config
from agent.travel_agent.graph.memory_integration import get_agent_memory_manager, reset_agent_memory_manager
from moyuan_web.bootstrap_app import create_web_application
from moyuan_web.dependencies import reset_container


@pytest.mark.asyncio
async def test_postgres_backend_session_share_and_memory_smoke(tmp_path, monkeypatch):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'postgres-backend-smoke.db'}"
    monkeypatch.setenv("MOYUAN_DB_BACKEND", "postgres")
    monkeypatch.setenv("MOYUAN_POSTGRES_DSN", database_url)
    monkeypatch.setenv("MOYUAN_DB_POOL_MIN", "1")
    monkeypatch.setenv("MOYUAN_DB_POOL_MAX", "2")
    server_config.reload()
    reset_container()
    reset_agent_memory_manager()

    try:
        app = create_web_application()
        transport = httpx.ASGITransport(app=app)

        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            create_resp = await client.post("/api/session/new")
            assert create_resp.status_code == 200
            session_id = create_resp.json()["session_id"]

            memory_manager = get_agent_memory_manager(max_history=10, summary_threshold=20)
            await memory_manager.add_message(session_id, "user", "预算5000元，玩2天")

            messages_resp = await client.get(f"/api/session/{session_id}/messages")
            assert messages_resp.status_code == 200
            assert messages_resp.json()["messages"] == []

            share_create_resp = await client.post(
                "/api/share-links",
                json={"title": "Weekend", "content": "Hangzhou trip"},
            )
            assert share_create_resp.status_code == 200
            share_id = share_create_resp.json()["share_id"]

            share_detail_resp = await client.get(f"/api/share-links/{share_id}")
            assert share_detail_resp.status_code == 200
            assert share_detail_resp.json()["content"] == "Hangzhou trip"

            clear_resp = await client.post(f"/api/clear/{session_id}")
            assert clear_resp.status_code == 200
            assert clear_resp.json()["success"] is True
            assert await memory_manager.get_recent_messages(session_id) == []

            delete_resp = await client.delete(f"/api/session/{session_id}")
            assert delete_resp.status_code == 200
            assert delete_resp.json()["success"] is True
            assert await memory_manager.get_recent_messages(session_id) == []
    finally:
        monkeypatch.delenv("MOYUAN_DB_BACKEND", raising=False)
        monkeypatch.delenv("MOYUAN_POSTGRES_DSN", raising=False)
        monkeypatch.delenv("MOYUAN_DB_POOL_MIN", raising=False)
        monkeypatch.delenv("MOYUAN_DB_POOL_MAX", raising=False)
        server_config.reload()
        reset_agent_memory_manager()
        reset_container()
