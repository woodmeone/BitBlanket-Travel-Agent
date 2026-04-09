"""Artifact retrieval routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query

from ..api.error_codes import ApiErrorCode
from ..api.schemas import ArtifactHistoryResponse, LatestArtifactResponse
from ..api.validation import SESSION_ID_PATTERN
from .errors import raise_api_error
from .service_resolver import get_artifact_service

router = APIRouter()

SessionIdParam = Annotated[str, Path(min_length=1, max_length=128, pattern=SESSION_ID_PATTERN)]


@router.get("/artifacts/{session_id}/latest", response_model=LatestArtifactResponse)
async def get_latest_artifact(session_id: SessionIdParam):
    """Return the latest persisted trip artifact for one session."""
    service = get_artifact_service()
    result = await service.get_latest_artifact(session_id)
    if not result.get("success"):
        raise_api_error(status_code=404, message=result.get("error", "Session not found"), code=ApiErrorCode.SESSION_NOT_FOUND)
    return result


@router.get("/artifacts/{session_id}/history", response_model=ArtifactHistoryResponse)
async def get_artifact_history(session_id: SessionIdParam, limit: int = Query(default=10, ge=1, le=50)):
    """Return persisted artifact snapshots for one session in newest-first order."""
    service = get_artifact_service()
    result = await service.get_artifact_history(session_id, limit=limit)
    if not result.get("success"):
        raise_api_error(status_code=404, message=result.get("error", "Session not found"), code=ApiErrorCode.SESSION_NOT_FOUND)
    return result
