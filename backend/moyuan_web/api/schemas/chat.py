"""Chat endpoint request schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..validation import SESSION_ID_PATTERN


ChatMode = Literal["direct", "react", "plan"]


class ChatRequest(BaseModel):
    """Request payload for the streaming chat endpoint."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    message: str = Field(min_length=1, max_length=5000)
    display_message: str | None = Field(default=None, max_length=5000)
    session_id: str | None = Field(default=None, min_length=1, max_length=128, pattern=SESSION_ID_PATTERN)
    mode: ChatMode = "react"

    @field_validator("display_message", "session_id", mode="after")
    @classmethod
    def _empty_string_to_none(cls, value: str | None) -> str | None:
        """Treat blank optional request fields as absent after whitespace normalization."""

        return value or None
