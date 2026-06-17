"""Unit tests for default checkpoint backend selection."""

from __future__ import annotations

from agent.travel_agent.graph.postgres_checkpointer import PersistentPostgresSaver
from agent.travel_agent.graph.persistent_checkpointer import PersistentSqliteSaver
from agent.travel_agent.runtime_sources import create_default_checkpointer, reset_default_checkpointer


def test_create_default_checkpointer_defaults_to_sqlite(monkeypatch, tmp_path):
    monkeypatch.delenv("AGENT_CHECKPOINT_BACKEND", raising=False)
    monkeypatch.delenv("AGENT_CHECKPOINT_DSN", raising=False)
    monkeypatch.setenv("AGENT_CHECKPOINT_DB", str(tmp_path / "runtime-checkpoints.sqlite3"))

    reset_default_checkpointer()
    saver = create_default_checkpointer()

    assert isinstance(saver, PersistentSqliteSaver)
    assert create_default_checkpointer() is saver

    reset_default_checkpointer()


def test_create_default_checkpointer_supports_postgres_backend(monkeypatch, tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'checkpoint-backend.db'}"
    monkeypatch.setenv("AGENT_CHECKPOINT_BACKEND", "postgres")
    monkeypatch.setenv("AGENT_CHECKPOINT_DSN", database_url)

    reset_default_checkpointer()
    saver = create_default_checkpointer()

    assert isinstance(saver, PersistentPostgresSaver)
    assert saver.get_checkpoint_count("missing-thread") == 0

    reset_default_checkpointer()
