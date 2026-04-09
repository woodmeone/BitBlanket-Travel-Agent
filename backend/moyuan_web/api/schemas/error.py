"""Normalized API error response schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, Field


class ApiValidationIssue(BaseModel):
    """One field-level validation issue included in 4xx error details."""

    field: str
    message: str
    issue_type: str = Field(
        validation_alias=AliasChoices("issue_type", "issueType"),
        serialization_alias="issueType",
    )
    input: Any | None = None


class ApiErrorDetail(BaseModel):
    """Shared HTTP error detail envelope used across API routes."""

    success: Literal[False] = False
    error: str
    code: str
    details: dict[str, Any] | list[ApiValidationIssue] | None = None


class ApiErrorResponse(BaseModel):
    """Top-level FastAPI error response schema."""

    detail: ApiErrorDetail
