"""phase-1 normalization tables for session messages and agent memory"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260404_0002"
down_revision = "20260404_0001"
branch_labels = None
depends_on = None

json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    """Create normalized tables and backfill existing session message payloads."""

    op.create_table(
        "session_messages",
        sa.Column("message_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(length=128), sa.ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("model_content", sa.Text(), nullable=True),
        sa.Column("diagnostics", json_type, nullable=True),
        sa.Column("timestamp", sa.String(length=64), nullable=False),
    )
    op.create_index(
        "ix_session_messages_session_sequence",
        "session_messages",
        ["session_id", "sequence"],
        unique=True,
    )

    op.create_table(
        "memory_sessions",
        sa.Column("session_id", sa.String(length=128), primary_key=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("profile", json_type, nullable=False),
        sa.Column("messages", json_type, nullable=False),
        sa.Column("updated_at", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_memory_sessions_updated_at", "memory_sessions", ["updated_at"], unique=False)

    connection = op.get_bind()
    sessions = sa.table(
        "sessions",
        sa.column("session_id", sa.String(length=128)),
        sa.column("messages", json_type),
    )
    session_messages = sa.table(
        "session_messages",
        sa.column("session_id", sa.String(length=128)),
        sa.column("sequence", sa.Integer()),
        sa.column("role", sa.String(length=32)),
        sa.column("content", sa.Text()),
        sa.column("reasoning", sa.Text()),
        sa.column("model_content", sa.Text()),
        sa.column("diagnostics", json_type),
        sa.column("timestamp", sa.String(length=64)),
    )

    inserts: list[dict[str, object]] = []
    rows = connection.execute(sa.select(sessions.c.session_id, sessions.c.messages)).mappings().all()
    for row in rows:
        raw_messages = row["messages"] if isinstance(row["messages"], list) else []
        for sequence, item in enumerate(raw_messages):
            if not isinstance(item, dict):
                continue
            inserts.append(
                {
                    "session_id": str(row["session_id"]),
                    "sequence": sequence,
                    "role": str(item.get("role") or "user"),
                    "content": str(item.get("content") or ""),
                    "reasoning": str(item.get("reasoning")) if item.get("reasoning") is not None else None,
                    "model_content": str(item.get("model_content")) if item.get("model_content") is not None else None,
                    "diagnostics": item.get("diagnostics"),
                    "timestamp": str(item.get("timestamp") or ""),
                }
            )

    if inserts:
        connection.execute(sa.insert(session_messages), inserts)


def downgrade() -> None:
    """Drop the normalized tables while keeping compatibility shadow columns intact."""

    op.drop_index("ix_memory_sessions_updated_at", table_name="memory_sessions")
    op.drop_table("memory_sessions")
    op.drop_index("ix_session_messages_session_sequence", table_name="session_messages")
    op.drop_table("session_messages")
