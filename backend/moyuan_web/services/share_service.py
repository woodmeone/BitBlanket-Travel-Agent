"""Persistent share-link orchestration service."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from ..repositories.file_share_link_repository import FileShareLinkRepository
from ..repositories.share_link_repository import ShareLinkRepository


def _utc_now_iso() -> str:
    """Return current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


class ShareService:
    """Create and fetch shared travel plans using the configured repository."""

    BACKUP_SUFFIX = FileShareLinkRepository.BACKUP_SUFFIX

    def __init__(
        self,
        file_path: str = "data/share_links.json",
        repository: ShareLinkRepository | None = None,
    ) -> None:
        """Initialize the service with a file-backed default repository."""

        self._repository = repository or FileShareLinkRepository(file_path)

    @classmethod
    def _backup_path(cls, path: str) -> str:
        """Return backup filepath for the primary share-link snapshot."""

        return FileShareLinkRepository.backup_path(path)

    async def create(
        self,
        *,
        title: str | None,
        content: str,
        html_content: str | None = None,
        delivery_bundle: dict[str, Any] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Create a share record and return generated share URL metadata."""
        if not content.strip():
            raise ValueError("content cannot be empty")

        share_id = uuid.uuid4().hex[:10]
        record = {
            "share_id": share_id,
            "title": title.strip() if title else "",
            "content": content.strip(),
            "html_content": html_content.strip() if html_content else "",
            "delivery_bundle": delivery_bundle,
            "created_at": _utc_now_iso(),
        }
        await self._repository.save(record)
        return share_id, record

    async def get(self, share_id: str) -> dict[str, Any] | None:
        """Return one share record by token."""

        return await self._repository.get(share_id)
