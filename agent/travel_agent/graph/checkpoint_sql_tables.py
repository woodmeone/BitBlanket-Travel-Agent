"""SQLAlchemy tables for SQL-backed LangGraph checkpoint persistence."""

from __future__ import annotations

from sqlalchemy import Column, Engine, Index, Integer, LargeBinary, String, Table

from moyuan_web.persistence.sql_tables import metadata


agent_checkpoints_table = Table(
    "agent_checkpoints",
    metadata,
    Column("thread_id", String(128), primary_key=True),
    Column("checkpoint_ns", String(128), primary_key=True),
    Column("checkpoint_id", String(128), primary_key=True),
    Column("payload", LargeBinary, nullable=False),
    Column("created_at", String(64), nullable=False),
)

Index(
    "ix_agent_checkpoints_thread_ns_created_at",
    agent_checkpoints_table.c.thread_id,
    agent_checkpoints_table.c.checkpoint_ns,
    agent_checkpoints_table.c.created_at,
)

agent_checkpoint_blobs_table = Table(
    "agent_checkpoint_blobs",
    metadata,
    Column("thread_id", String(128), primary_key=True),
    Column("checkpoint_ns", String(128), primary_key=True),
    Column("channel", String(128), primary_key=True),
    Column("version", String(128), primary_key=True),
    Column("payload", LargeBinary, nullable=False),
    Column("created_at", String(64), nullable=False),
)

Index(
    "ix_agent_checkpoint_blobs_thread_ns_created_at",
    agent_checkpoint_blobs_table.c.thread_id,
    agent_checkpoint_blobs_table.c.checkpoint_ns,
    agent_checkpoint_blobs_table.c.created_at,
)

agent_checkpoint_writes_table = Table(
    "agent_checkpoint_writes",
    metadata,
    Column("thread_id", String(128), primary_key=True),
    Column("checkpoint_ns", String(128), primary_key=True),
    Column("checkpoint_id", String(128), primary_key=True),
    Column("task_id", String(128), primary_key=True),
    Column("write_idx", Integer, primary_key=True),
    Column("payload", LargeBinary, nullable=False),
    Column("created_at", String(64), nullable=False),
)

Index(
    "ix_agent_checkpoint_writes_thread_ns_checkpoint",
    agent_checkpoint_writes_table.c.thread_id,
    agent_checkpoint_writes_table.c.checkpoint_ns,
    agent_checkpoint_writes_table.c.checkpoint_id,
)

agent_checkpoint_meta_table = Table(
    "agent_checkpoint_meta",
    metadata,
    Column("key", String(128), primary_key=True),
    Column("value", String(256), nullable=False),
)


def ensure_checkpoint_schema(engine: Engine) -> None:
    """Create SQL-backed checkpoint tables when they do not exist yet."""

    metadata.create_all(
        engine,
        tables=[
            agent_checkpoints_table,
            agent_checkpoint_blobs_table,
            agent_checkpoint_writes_table,
            agent_checkpoint_meta_table,
        ],
    )


__all__ = [
    "agent_checkpoint_blobs_table",
    "agent_checkpoint_meta_table",
    "agent_checkpoint_writes_table",
    "agent_checkpoints_table",
    "ensure_checkpoint_schema",
]
