"""compatibility-first postgres baseline"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260404_0001"
down_revision = None
branch_labels = None
depends_on = None

json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    """Create baseline compatibility tables for sessions and share links."""

    op.create_table(
        "sessions",
        sa.Column("session_id", sa.String(length=128), primary_key=True),
        sa.Column("created_at", sa.String(length=64), nullable=False),
        sa.Column("last_active", sa.String(length=64), nullable=False),
        sa.Column("message_count", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("model_id", sa.String(length=128), nullable=False),
        sa.Column("messages", json_type, nullable=False),
        sa.Column("user_preferences", json_type, nullable=False),
    )
    op.create_index("ix_sessions_last_active", "sessions", ["last_active"], unique=False)

    op.create_table(
        "share_links",
        sa.Column("share_id", sa.String(length=32), primary_key=True),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("html_content", sa.Text(), nullable=False),
        sa.Column("delivery_bundle", json_type, nullable=True),
        sa.Column("created_at", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_share_links_created_at", "share_links", ["created_at"], unique=False)


def downgrade() -> None:
    """Drop baseline compatibility tables."""

    op.drop_index("ix_share_links_created_at", table_name="share_links")
    op.drop_table("share_links")
    op.drop_index("ix_sessions_last_active", table_name="sessions")
    op.drop_table("sessions")
