"""Persistent share-link storage service."""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ShareService:
    """Create and fetch shared travel plans using local JSON storage."""

    def __init__(self, file_path: str = "data/share_links.json") -> None:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        self._file_path = file_path
        self._lock = asyncio.Lock()
        self._items: dict[str, dict[str, Any]] = self._load_from_file()

    def _load_from_file(self) -> dict[str, dict[str, Any]]:
        try:
            with open(self._file_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
                if isinstance(payload, dict):
                    return payload
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            return {}
        return {}

    def _save_to_file(self) -> None:
        with open(self._file_path, "w", encoding="utf-8") as handle:
            json.dump(self._items, handle, ensure_ascii=False, indent=2)

    async def create(self, *, title: str | None, content: str) -> tuple[str, dict[str, Any]]:
        if not content.strip():
            raise ValueError("content cannot be empty")

        share_id = uuid.uuid4().hex[:10]
        record = {
            "share_id": share_id,
            "title": title.strip() if title else "",
            "content": content.strip(),
            "created_at": _utc_now_iso(),
        }
        async with self._lock:
            self._items[share_id] = record
            await asyncio.to_thread(self._save_to_file)
        return share_id, record

    async def get(self, share_id: str) -> dict[str, Any] | None:
        async with self._lock:
            return self._items.get(share_id)
