"""Persistence abstraction for full agent-memory session snapshots."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MemorySessionRepository(ABC):
    """Abstract repository used by file and SQL-backed memory persistence."""

    @property
    @abstractmethod
    def enabled(self) -> bool:
        """Return whether persistence is configured and active."""

    @property
    @abstractmethod
    def backup_path(self) -> str | None:
        """Return the hot-backup path when the backend exposes one."""

    @abstractmethod
    def load_snapshot(self) -> tuple[dict[str, Any] | None, bool]:
        """Load the newest usable memory snapshot."""

    @abstractmethod
    def write_snapshot(self, payload: dict[str, Any]) -> None:
        """Persist the current full memory snapshot."""

    @abstractmethod
    def restore_primary(self, payload: dict[str, Any]) -> None:
        """Restore the primary persistence target from a recovered snapshot."""
