"""checkpoint sql baseline tables for optional postgres runtime backend"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260405_0004"
down_revision = "20260404_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create dedicated checkpoint tables that stay outside the business entity path."""

    op.create_table(
        "agent_checkpoints",
        sa.Column("thread_id", sa.String(length=128), primary_key=True),
        sa.Column("checkpoint_ns", sa.String(length=128), primary_key=True),
        sa.Column("checkpoint_id", sa.String(length=128), primary_key=True),
        sa.Column("payload", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.String(length=64), nullable=False),
    )
    op.create_index(
        "ix_agent_checkpoints_thread_ns_created_at",
        "agent_checkpoints",
        ["thread_id", "checkpoint_ns", "created_at"],
        unique=False,
    )

    op.create_table(
        "agent_checkpoint_blobs",
        sa.Column("thread_id", sa.String(length=128), primary_key=True),
        sa.Column("checkpoint_ns", sa.String(length=128), primary_key=True),
        sa.Column("channel", sa.String(length=128), primary_key=True),
        sa.Column("version", sa.String(length=128), primary_key=True),
        sa.Column("payload", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.String(length=64), nullable=False),
    )
    op.create_index(
        "ix_agent_checkpoint_blobs_thread_ns_created_at",
        "agent_checkpoint_blobs",
        ["thread_id", "checkpoint_ns", "created_at"],
        unique=False,
    )

    op.create_table(
        "agent_checkpoint_writes",
        sa.Column("thread_id", sa.String(length=128), primary_key=True),
        sa.Column("checkpoint_ns", sa.String(length=128), primary_key=True),
        sa.Column("checkpoint_id", sa.String(length=128), primary_key=True),
        sa.Column("task_id", sa.String(length=128), primary_key=True),
        sa.Column("write_idx", sa.Integer(), primary_key=True),
        sa.Column("payload", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.String(length=64), nullable=False),
    )
    op.create_index(
        "ix_agent_checkpoint_writes_thread_ns_checkpoint",
        "agent_checkpoint_writes",
        ["thread_id", "checkpoint_ns", "checkpoint_id"],
        unique=False,
    )

    op.create_table(
        "agent_checkpoint_meta",
        sa.Column("key", sa.String(length=128), primary_key=True),
        sa.Column("value", sa.String(length=256), nullable=False),
    )


def downgrade() -> None:
    """Drop SQL-backed checkpoint tables."""

    op.drop_table("agent_checkpoint_meta")
    op.drop_index("ix_agent_checkpoint_writes_thread_ns_checkpoint", table_name="agent_checkpoint_writes")
    op.drop_table("agent_checkpoint_writes")
    op.drop_index("ix_agent_checkpoint_blobs_thread_ns_created_at", table_name="agent_checkpoint_blobs")
    op.drop_table("agent_checkpoint_blobs")
    op.drop_index("ix_agent_checkpoints_thread_ns_created_at", table_name="agent_checkpoints")
    op.drop_table("agent_checkpoints")
