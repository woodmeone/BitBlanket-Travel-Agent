"""Session management routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query

from ..api.error_codes import ApiErrorCode
from ..api.schemas.session import SetModelRequest, UpdateNameRequest
from ..api.validation import NON_BLANK_TEXT_PATTERN, SESSION_ID_PATTERN
from ..config.runtime import get_model_config_manager
from .errors import raise_api_error
from .service_resolver import get_chat_service, get_session_service

router = APIRouter()


def _raise_not_found(message: str) -> None:
    """Raise standard not-found response for session endpoints."""
    raise_api_error(status_code=404, message=message, code=ApiErrorCode.SESSION_NOT_FOUND)


SessionIdParam = Annotated[str, Path(min_length=1, max_length=128, pattern=SESSION_ID_PATTERN)]
OptionalSessionNameQuery = Annotated[str | None, Query(min_length=1, max_length=120, pattern=NON_BLANK_TEXT_PATTERN)]


@router.post("/session/new")
async def create_session(name: OptionalSessionNameQuery = None):
    """Create a new chat session with optional custom name."""
    service = get_session_service()
    return await service.create_session(name=name)


@router.get("/sessions")
async def list_sessions(include_empty: bool = False):
    """List sessions, optionally including empty sessions."""
    service = get_session_service()
    return await service.list_sessions(include_empty=include_empty)


@router.delete("/session/{session_id}")
async def delete_session(session_id: SessionIdParam):
    """Delete session and all associated messages."""
    service = get_session_service()
    result = await service.delete_session(session_id)
    if not result.get("success"):
        _raise_not_found(result.get("error", "Session not found"))
    return result


@router.put("/session/{session_id}/name")
async def update_session_name(session_id: SessionIdParam, request: UpdateNameRequest):
    """Update session display name."""
    service = get_session_service()
    result = await service.update_session_name(session_id, request.name)
    if not result.get("success"):
        _raise_not_found(result.get("error", "Session not found"))
    return result


@router.put("/session/{session_id}/model")
async def set_session_model(session_id: SessionIdParam, request: SetModelRequest):
    """Bind a model id to a session."""
    model_id = request.model_id
    known_model_ids = {str(item["model_id"]) for item in get_model_config_manager().get_available_models()}
    if model_id not in known_model_ids:
        raise_api_error(
            status_code=404,
            message=f"Model not found: {model_id}",
            code=ApiErrorCode.MODEL_NOT_FOUND,
            details={"model_id": model_id},
        )

    service = get_session_service()
    result = await service.update_session_model(session_id, model_id)
    if not result.get("success"):
        _raise_not_found(result.get("error", "Session not found"))
    return result


@router.get("/session/{session_id}/model")
async def get_session_model(session_id: SessionIdParam):
    """Get model binding metadata for a session."""
    service = get_session_service()
    result = await service.get_session_model(session_id)
    if not result.get("success"):
        _raise_not_found(result.get("error", "Session not found"))
    return result


@router.get("/session/{session_id}/messages")
async def get_session_messages(session_id: SessionIdParam):
    """Return persisted public messages for one session."""
    service = get_chat_service()
    result = await service.get_messages(session_id)
    if not result.get("success"):
        _raise_not_found(result.get("error", "Session not found"))
    return result


@router.post("/clear/{session_id}")
async def clear_chat(session_id: SessionIdParam):
    """Clear all messages in the target session."""
    service = get_session_service()
    result = await service.clear_chat(session_id)
    if not result.get("success"):
        _raise_not_found(result.get("error", "Session not found"))
    return result
