"""Share-link repository abstraction used by file and postgres backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ShareLinkRepository(ABC):
    """Abstract persistence interface for share-link records."""

    @abstractmethod
    async def save(self, record: dict[str, Any]) -> None:
        """Persist one share-link record, replacing existing content when IDs match."""

    @abstractmethod
    async def get(self, share_id: str) -> dict[str, Any] | None:
        """Fetch one share-link record by ID."""

    @abstractmethod
    async def list_all(self) -> dict[str, dict[str, Any]]:
        """Return all persisted share-link records keyed by share ID."""
