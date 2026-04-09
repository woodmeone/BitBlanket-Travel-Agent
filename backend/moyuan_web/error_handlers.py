"""Application-level exception handlers for standardized API error payloads."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .api.error_codes import ApiErrorCode
from .routes.errors import error_detail, validation_error_detail


def _normalize_http_exception_detail(detail: Any) -> dict[str, Any]:
    """Convert raw HTTPException detail values into the shared API error shape."""

    if isinstance(detail, dict) and detail.get("success") is False and detail.get("error"):
        return detail
    return error_detail(message=str(detail), code=ApiErrorCode.HTTP_ERROR)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach standardized validation and HTTP exception handlers to the app."""

    @app.exception_handler(RequestValidationError)
    async def _validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": validation_error_detail(exc)})

    @app.exception_handler(HTTPException)
    async def _http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": _normalize_http_exception_detail(exc.detail)},
            headers=exc.headers,
        )
