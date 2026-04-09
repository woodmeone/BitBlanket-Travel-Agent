"""Shared SQLAlchemy engine helpers for the optional database backend."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.pool import StaticPool

from .sql_tables import metadata


def normalize_database_url(database_url: str) -> str:
    """Normalize configured database URL into the SQLAlchemy driver form."""

    normalized = str(database_url or "").strip()
    if normalized.startswith("postgresql://"):
        return normalized.replace("postgresql://", "postgresql+psycopg://", 1)
    return normalized


def build_sync_engine(database_url: str, *, pool_min: int = 1, pool_max: int = 5) -> Engine:
    """Create one synchronous SQLAlchemy engine for repository adapters and scripts."""

    normalized = normalize_database_url(database_url)
    if not normalized:
        raise ValueError("database_url is required")

    engine_kwargs: dict[str, object] = {"future": True}
    if normalized.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in normalized:
            engine_kwargs["poolclass"] = StaticPool
    else:
        engine_kwargs["pool_pre_ping"] = True
        engine_kwargs["pool_size"] = max(1, int(pool_min))
        engine_kwargs["max_overflow"] = max(0, int(pool_max) - int(pool_min))

    return create_engine(normalized, **engine_kwargs)


def ensure_schema(engine: Engine) -> None:
    """Create baseline tables when they do not exist yet."""

    metadata.create_all(engine)
