"""SQL-backed share-link repository used by the optional postgres backend."""

from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy import Engine, insert, select, update

from ..persistence import build_sync_engine, ensure_schema, share_links_table
from .share_link_repository import ShareLinkRepository


class PostgresShareLinkRepository(ShareLinkRepository):
    """Persist share-link records in the SQL compatibility baseline tables."""

    def __init__(
        self,
        database_url: str,
        *,
        pool_min: int = 1,
        pool_max: int = 5,
        ensure_schema_ready: bool = True,
        engine: Engine | None = None,
    ) -> None:
        """Create SQL repository and optionally bootstrap baseline tables."""

        self._engine = engine or build_sync_engine(database_url, pool_min=pool_min, pool_max=pool_max)
        if ensure_schema_ready:
            ensure_schema(self._engine)

    async def save(self, record: dict[str, Any]) -> None:
        """Upsert one share-link record into the SQL backend."""

        await asyncio.to_thread(self._save_sync, record)

    def _save_sync(self, record: dict[str, Any]) -> None:
        share_id = str(record.get("share_id") or "").strip()
        if not share_id:
            raise ValueError("share_id is required")
        values = {
            "share_id": share_id,
            "title": str(record.get("title") or ""),
            "content": str(record.get("content") or ""),
            "html_content": str(record.get("html_content") or ""),
            "delivery_bundle": record.get("delivery_bundle"),
            "created_at": str(record.get("created_at") or ""),
        }
        with self._engine.begin() as connection:
            existing = connection.execute(
                select(share_links_table.c.share_id).where(share_links_table.c.share_id == share_id)
            ).first()
            if existing is None:
                connection.execute(insert(share_links_table).values(**values))
            else:
                connection.execute(
                    update(share_links_table)
                    .where(share_links_table.c.share_id == share_id)
                    .values(**values)
                )

    async def get(self, share_id: str) -> dict[str, Any] | None:
        """Fetch one share-link record by token."""

        return await asyncio.to_thread(self._get_sync, share_id)

    def _get_sync(self, share_id: str) -> dict[str, Any] | None:
        with self._engine.begin() as connection:
            row = connection.execute(
                select(share_links_table).where(share_links_table.c.share_id == share_id)
            ).mappings().first()
        return self._row_to_record(row) if row is not None else None

    async def list_all(self) -> dict[str, dict[str, Any]]:
        """Return all persisted share-link records keyed by share ID."""

        return await asyncio.to_thread(self._list_all_sync)

    def _list_all_sync(self) -> dict[str, dict[str, Any]]:
        with self._engine.begin() as connection:
            rows = connection.execute(select(share_links_table)).mappings().all()
        return {
            str(row["share_id"]): self._row_to_record(row)
            for row in rows
        }

    @staticmethod
    def _row_to_record(row: Any) -> dict[str, Any]:
        return {
            "share_id": str(row["share_id"]),
            "title": str(row["title"] or ""),
            "content": str(row["content"] or ""),
            "html_content": str(row["html_content"] or ""),
            "delivery_bundle": row["delivery_bundle"],
            "created_at": str(row["created_at"] or ""),
        }
