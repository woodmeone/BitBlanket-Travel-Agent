"""Artifact retrieval routes."""

from __future__ import annotations

from fastapi import APIRouter

from ..api.schemas import LatestArtifactResponse
from .errors import raise_api_error
from .service_resolver import get_artifact_service

router = APIRouter()


@router.get("/artifacts/{session_id}/latest", response_model=LatestArtifactResponse)
async def get_latest_artifact(session_id: str):
    """Return the latest persisted trip artifact for one session."""
    service = get_artifact_service()
    result = await service.get_latest_artifact(session_id)
    if not result.get("success"):
        raise_api_error(status_code=404, message=result.get("error", "Session not found"), code="SESSION_NOT_FOUND")
    return result
