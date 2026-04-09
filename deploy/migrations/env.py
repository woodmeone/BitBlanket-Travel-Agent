"""Alembic environment wiring for the compatibility-first SQL baseline."""
# ruff: noqa: E402

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool


ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web"
for candidate in (ROOT, WEB_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from agent.travel_agent.graph import checkpoint_sql_tables as _checkpoint_sql_tables
from moyuan_web.persistence import metadata, normalize_database_url


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = normalize_database_url(os.getenv("MOYUAN_POSTGRES_DSN") or config.get_main_option("sqlalchemy.url"))
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

target_metadata = metadata


def run_migrations_offline() -> None:
    """Run migrations in offline mode."""

    if not database_url:
        raise RuntimeError("Set MOYUAN_POSTGRES_DSN or sqlalchemy.url before running alembic migrations.")

    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in online mode."""

    if not database_url:
        raise RuntimeError("Set MOYUAN_POSTGRES_DSN or sqlalchemy.url before running alembic migrations.")

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
