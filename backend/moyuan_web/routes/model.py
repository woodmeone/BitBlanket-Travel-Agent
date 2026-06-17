"""Model info routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path

from ..api.error_codes import ApiErrorCode
from ..config.runtime import get_model_config_manager
from ..api.validation import MODEL_ID_PATTERN
from .errors import raise_api_error

router = APIRouter()


@router.get("/models")
async def list_models():
    """List available models from the runtime configuration."""
    config_manager = get_model_config_manager()
    return {"success": True, "models": config_manager.get_available_models()}


@router.get("/models/{model_id}")
async def get_model(model_id: Annotated[str, Path(min_length=1, max_length=128, pattern=MODEL_ID_PATTERN)]):
    """Get one configured model by ID."""
    config_manager = get_model_config_manager()
    try:
        model_config = config_manager.get_model_config(model_id)
    except ValueError:
        raise_api_error(status_code=404, message="Model not found", code=ApiErrorCode.MODEL_NOT_FOUND)

    return {
        "success": True,
        "model_id": model_id,
        "name": model_config.get("name", model_id),
        "provider": model_config.get("provider", "unknown"),
        **model_config,
    }
