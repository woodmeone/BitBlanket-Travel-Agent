"""Artifact retrieval helpers for session-backed trip artifacts."""

from __future__ import annotations

from typing import Any

from ..api.schemas import normalize_trip_plan_artifact
from ..repositories.session_repository import SessionRepository


class ArtifactService:
    """Resolve persisted trip artifacts from session message history."""

    def __init__(self, repository: SessionRepository) -> None:
        """Store the repository used to look up session-backed artifacts."""
        self._repository = repository

    async def get_latest_artifact(self, session_id: str) -> dict[str, Any]:
        """Return the latest normalized artifact stored in one session."""
        session = await self._repository.get(session_id)
        if not session:
            return {"success": False, "error": "SESSION_NOT_FOUND"}

        messages = session.get("messages", [])
        for reverse_index, message in enumerate(reversed(messages)):
            if not isinstance(message, dict):
                continue
            diagnostics = message.get("diagnostics")
            if not isinstance(diagnostics, dict):
                continue
            artifact = diagnostics.get("artifact")
            if not isinstance(artifact, dict) or not artifact:
                continue

            message_index = len(messages) - reverse_index - 1
            return {
                "success": True,
                "session_id": session_id,
                "artifact_found": True,
                "artifact": normalize_trip_plan_artifact(artifact),
                "run_id": diagnostics.get("runId") or diagnostics.get("run_id"),
                "message_timestamp": message.get("timestamp"),
                "message_index": message_index,
            }

        return {
            "success": True,
            "session_id": session_id,
            "artifact_found": False,
            "artifact": None,
            "run_id": None,
            "message_timestamp": None,
            "message_index": None,
        }
