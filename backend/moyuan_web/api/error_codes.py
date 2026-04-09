"""Canonical API error codes shared by validation, route handlers, and docs."""

from __future__ import annotations

from enum import StrEnum


class ApiErrorCode(StrEnum):
    """Stable API error codes exposed to clients and maintainer docs."""

    REQUEST_VALIDATION_FAILED = "REQUEST_VALIDATION_FAILED"
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    CITY_NOT_FOUND = "CITY_NOT_FOUND"
    SHARE_INVALID = "SHARE_INVALID"
    SHARE_NOT_FOUND = "SHARE_NOT_FOUND"
    MAP_ROUTE_INVALID = "MAP_ROUTE_INVALID"
    MAP_ROUTE_ERROR = "MAP_ROUTE_ERROR"
    METRICS_DISABLED = "METRICS_DISABLED"
    HTTP_ERROR = "HTTP_ERROR"
