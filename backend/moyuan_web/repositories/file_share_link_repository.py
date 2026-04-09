"""File-backed share-link repository with atomic writes and backup recovery."""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from typing import Any

from .share_link_repository import ShareLinkRepository


class FileShareLinkRepository(ShareLinkRepository):
    """Persist share-link records to one JSON file plus `.bak` backup snapshot."""

    BACKUP_SUFFIX = ".bak"

    def __init__(self, file_path: str = "data/share_links.json") -> None:
        """Initialize file-backed share-link repository and load current snapshots."""

        os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
        self._file_path = file_path
        self._lock = asyncio.Lock()
        self._items: dict[str, dict[str, Any]] = self._load_from_file()

    @classmethod
    def backup_path(cls, path: str) -> str:
        """Return backup filepath for the primary share-link snapshot."""

        return f"{path}{cls.BACKUP_SUFFIX}"

    @staticmethod
    def _load_json_file(path: str) -> dict[str, dict[str, Any]] | None:
        """Load one JSON snapshot file when it exists and is well-formed."""

        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return None
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _fsync_directory(path: str) -> None:
        """Best-effort directory fsync so renamed snapshots survive process crashes."""

        try:
            directory_fd = os.open(path, os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(directory_fd)
        except OSError:
            pass
        finally:
            os.close(directory_fd)

    def _atomic_write_json(self, path: str, payload: dict[str, dict[str, Any]]) -> None:
        """Persist JSON payload atomically using temp-file plus replace."""

        target_dir = os.path.dirname(path) or "."
        os.makedirs(target_dir, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(
            prefix=f".{os.path.basename(path)}.",
            suffix=".tmp",
            dir=target_dir,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
                json.dump(payload, tmp_file, ensure_ascii=False, indent=2)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())
            os.replace(temp_path, path)
            self._fsync_directory(target_dir)
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def _load_from_file(self) -> dict[str, dict[str, Any]]:
        """Load share-link records into memory and recover from backup when needed."""

        primary = self._file_path
        backup = self.backup_path(primary)

        primary_payload = self._load_json_file(primary)
        if primary_payload is not None:
            return primary_payload

        backup_payload = self._load_json_file(backup)
        if backup_payload is None:
            return {}

        try:
            self._atomic_write_json(primary, backup_payload)
        except OSError:
            pass
        return backup_payload

    def _save_to_file(self) -> None:
        """Persist current in-memory snapshot to primary and backup files."""

        self._atomic_write_json(self._file_path, self._items)
        self._atomic_write_json(self.backup_path(self._file_path), self._items)

    async def save(self, record: dict[str, Any]) -> None:
        """Persist one share-link record to the file-backed snapshot."""

        share_id = str(record.get("share_id") or "").strip()
        if not share_id:
            raise ValueError("share_id is required")
        async with self._lock:
            self._items[share_id] = dict(record)
            await asyncio.to_thread(self._save_to_file)

    async def get(self, share_id: str) -> dict[str, Any] | None:
        """Return one share-link record by token."""

        async with self._lock:
            item = self._items.get(share_id)
            return dict(item) if isinstance(item, dict) else None

    async def list_all(self) -> dict[str, dict[str, Any]]:
        """Return all share-link records keyed by share ID."""

        async with self._lock:
            return {key: dict(value) for key, value in self._items.items()}
