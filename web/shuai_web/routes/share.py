"""Share link endpoints for itinerary content."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from ..services.share_service import ShareService
from .errors import raise_api_error

router = APIRouter()
_share_service = ShareService()


class ShareCreateRequest(BaseModel):
    """Create share-link request body."""

    content: str = Field(min_length=1, max_length=50000)
    title: str | None = Field(default=None, max_length=100)


class ShareCreateResponse(BaseModel):
    """Create share-link response body."""

    success: bool = True
    share_id: str
    share_url: str


class ShareDetailResponse(BaseModel):
    """Shared content response body."""

    success: bool = True
    share_id: str
    title: str | None = None
    content: str
    created_at: str


@router.post("/share-links", response_model=ShareCreateResponse)
async def create_share_link(request: ShareCreateRequest, fastapi_request: Request):
    """Create a short share id and return an app URL with share query parameter."""
    _ = fastapi_request
    try:
        share_id, _record = await _share_service.create(title=request.title, content=request.content)
    except ValueError as exc:
        raise_api_error(status_code=422, message=str(exc), code="SHARE_INVALID")

    origin = fastapi_request.headers.get("origin") or "http://localhost:33001"
    share_url = f"{origin}/?share={share_id}"
    return ShareCreateResponse(success=True, share_id=share_id, share_url=share_url)


@router.get("/share-links/{share_id}", response_model=ShareDetailResponse)
async def get_share_link(share_id: str):
    """Fetch shared travel-plan content by share id."""
    record = await _share_service.get(share_id)
    if not record:
        raise_api_error(status_code=404, message="Share link not found", code="SHARE_NOT_FOUND")

    return ShareDetailResponse(
        success=True,
        share_id=share_id,
        title=record.get("title") or "",
        content=str(record.get("content") or ""),
        created_at=str(record.get("created_at") or ""),
    )
