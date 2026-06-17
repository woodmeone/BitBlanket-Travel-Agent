"""Session endpoint schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..validation import MODEL_ID_PATTERN


class UpdateNameRequest(BaseModel):
    """Payload for updating session display name."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)


class SetModelRequest(BaseModel):
    """Payload for binding a model to a session."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    model_id: str = Field(min_length=1, max_length=128, pattern=MODEL_ID_PATTERN)
