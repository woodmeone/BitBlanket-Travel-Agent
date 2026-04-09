"""Shared API error helpers for route handlers."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError

from ..api.error_codes import ApiErrorCode


def error_detail(
    message: str,
    code: str | ApiErrorCode | None = None,
    *,
    details: dict[str, Any] | list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a normalized API error payload."""
    detail: dict[str, Any] = {"success": False, "error": message}
    if code:
        detail["code"] = str(code)
    if details is not None:
        detail["details"] = details
    return detail


def validation_error_detail(exc: RequestValidationError) -> dict[str, Any]:
    """Convert FastAPI request-validation failures into the shared API error shape."""

    issues: list[dict[str, Any]] = []
    for entry in exc.errors():
        location = ".".join(str(part) for part in entry.get("loc", ()) if part != "__root__")
        issues.append(
            {
                "field": location or "request",
                "message": str(entry.get("msg") or "Invalid value"),
                "issueType": str(entry.get("type") or "value_error"),
                "input": entry.get("input"),
            }
        )
    return error_detail(
        "Request validation failed.",
        ApiErrorCode.REQUEST_VALIDATION_FAILED,
        details=issues,
    )


def raise_api_error(
    status_code: int,
    message: str,
    code: str | ApiErrorCode | None = None,
    *,
    details: dict[str, Any] | list[dict[str, Any]] | None = None,
) -> None:
    """Raise HTTPException with the shared API error payload format."""
    raise HTTPException(status_code=status_code, detail=error_detail(message=message, code=code, details=details))
