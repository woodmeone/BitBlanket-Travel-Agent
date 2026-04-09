"""degrade sessions.messages into a compatibility shadow field"""

from __future__ import annotations

from collections import defaultdict

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260404_0003"
down_revision = "20260404_0002"
branch_labels = None
depends_on = None

json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    """Backfill normalized rows when needed and clear legacy session message shadows."""

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

    existing_rows = connection.execute(sa.select(session_messages.c.session_id)).mappings().all()
    sessions_with_normalized_rows = {str(row["session_id"]) for row in existing_rows}

    inserts: list[dict[str, object]] = []
    shadow_session_ids: list[str] = []
    rows = connection.execute(sa.select(sessions.c.session_id, sessions.c.messages)).mappings().all()
    for row in rows:
        session_id = str(row["session_id"])
        raw_messages = row["messages"] if isinstance(row["messages"], list) else []
        if not raw_messages:
            continue
        shadow_session_ids.append(session_id)
        if session_id in sessions_with_normalized_rows:
            continue
        for sequence, item in enumerate(raw_messages):
            if not isinstance(item, dict):
                continue
            inserts.append(
                {
                    "session_id": session_id,
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

    for session_id in shadow_session_ids:
        connection.execute(
            sa.update(sessions)
            .where(sessions.c.session_id == session_id)
            .values(messages=[])
        )


def downgrade() -> None:
    """Restore compatibility shadow payloads from normalized rows."""

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

    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    rows = connection.execute(
        sa.select(session_messages).order_by(session_messages.c.session_id.asc(), session_messages.c.sequence.asc())
    ).mappings().all()
    for row in rows:
        payload: dict[str, object] = {
            "role": str(row["role"] or "user"),
            "content": str(row["content"] or ""),
            "timestamp": str(row["timestamp"] or ""),
        }
        if row["reasoning"] is not None:
            payload["reasoning"] = str(row["reasoning"])
        if row["model_content"] is not None:
            payload["model_content"] = str(row["model_content"])
        if row["diagnostics"] is not None:
            payload["diagnostics"] = row["diagnostics"]
        grouped[str(row["session_id"])].append(payload)

    for session_id, messages in grouped.items():
        connection.execute(
            sa.update(sessions)
            .where(sessions.c.session_id == session_id)
            .values(messages=messages)
        )
