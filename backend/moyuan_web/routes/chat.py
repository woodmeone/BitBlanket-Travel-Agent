"""LangChain chat routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from ..api.schemas.chat import ChatRequest
from .service_resolver import get_chat_service

router = APIRouter()


@router.post("/chat/stream")
async def stream_chat(request: ChatRequest, fastapi_request: Request):
    """Proxy SSE stream from chat service to API client."""
    service = get_chat_service()
    request_id = getattr(fastapi_request.state, "request_id", None)
    trace_id = getattr(fastapi_request.state, "trace_id", None)

    return StreamingResponse(
        service.stream_chat(
            message=request.message,
            display_message=request.display_message,
            session_id=request.session_id,
            mode=request.mode,
            request_id=request_id,
            trace_id=trace_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Request-ID": request_id or "",
            "X-Trace-ID": trace_id or request_id or "",
        },
    )
