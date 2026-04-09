"""SQLAlchemy table metadata for the compatibility-first database baseline."""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Index, Integer, MetaData, String, Table, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON


metadata = MetaData()
json_type = JSON().with_variant(JSONB(astext_type=Text()), "postgresql")

sessions_table = Table(
    "sessions",
    metadata,
    Column("session_id", String(128), primary_key=True),
    Column("created_at", String(64), nullable=False),
    Column("last_active", String(64), nullable=False),
    Column("message_count", Integer, nullable=False, default=0),
    Column("name", String(120), nullable=False),
    Column("model_id", String(128), nullable=False),
    Column("messages", json_type, nullable=False),
    Column("user_preferences", json_type, nullable=False),
)

Index("ix_sessions_last_active", sessions_table.c.last_active)

session_messages_table = Table(
    "session_messages",
    metadata,
    Column("message_id", Integer, primary_key=True, autoincrement=True),
    Column("session_id", String(128), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False),
    Column("sequence", Integer, nullable=False),
    Column("role", String(32), nullable=False),
    Column("content", Text, nullable=False),
    Column("reasoning", Text, nullable=True),
    Column("model_content", Text, nullable=True),
    Column("diagnostics", json_type, nullable=True),
    Column("timestamp", String(64), nullable=False),
)

Index(
    "ix_session_messages_session_sequence",
    session_messages_table.c.session_id,
    session_messages_table.c.sequence,
    unique=True,
)

share_links_table = Table(
    "share_links",
    metadata,
    Column("share_id", String(32), primary_key=True),
    Column("title", String(100), nullable=False, default=""),
    Column("content", Text, nullable=False),
    Column("html_content", Text, nullable=False, default=""),
    Column("delivery_bundle", json_type, nullable=True),
    Column("created_at", String(64), nullable=False),
)

Index("ix_share_links_created_at", share_links_table.c.created_at)

memory_sessions_table = Table(
    "memory_sessions",
    metadata,
    Column("session_id", String(128), primary_key=True),
    Column("summary", Text, nullable=False),
    Column("profile", json_type, nullable=False),
    Column("messages", json_type, nullable=False),
    Column("updated_at", String(64), nullable=False),
)

Index("ix_memory_sessions_updated_at", memory_sessions_table.c.updated_at)
