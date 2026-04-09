"""Disk persistence helpers for session memory snapshots."""

from __future__ import annotations

from typing import Any, Optional

from .file_memory_session_repository import FileMemorySessionRepository
from .memory_session_repository import MemorySessionRepository


class MemoryPersistenceStore:
    """Best-effort persistence store with primary/backup recovery and atomic writes."""

    def __init__(
        self,
        persist_path: Optional[str],
        *,
        backup_suffix: str = ".bak",
        repository: MemorySessionRepository | None = None,
    ) -> None:
        """Create a store backed by the provided repository or a file-backed default."""

        self._repository = repository or FileMemorySessionRepository(persist_path, backup_suffix=backup_suffix)

    @property
    def enabled(self) -> bool:
        """Return whether persistence is configured for the current manager instance."""
        return bool(self._repository.enabled)

    @property
    def backup_path(self) -> Optional[str]:
        """Return the hot-backup path associated with the primary snapshot file."""
        return self._repository.backup_path

    def load_snapshot(self) -> tuple[Optional[dict[str, Any]], bool]:
        """Load the newest usable snapshot, falling back to the hot backup when needed."""
        return self._repository.load_snapshot()

    def write_snapshot(self, payload: dict[str, Any]) -> None:
        """Write the current snapshot to both primary and hot-backup locations."""
        self._repository.write_snapshot(payload)

    def restore_primary(self, payload: dict[str, Any]) -> None:
        """Rewrite the primary file from a recovered snapshot."""
        self._repository.restore_primary(payload)


__all__ = ["MemoryPersistenceStore"]
