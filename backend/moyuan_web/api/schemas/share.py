"""Share endpoint schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DeliveryBundleMetric(BaseModel):
    """One delivery overview metric surfaced to share/export clients."""

    label: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=200)
    tone: Literal["default", "success", "warning", "danger", "info"] | None = None


class DeliveryBundleSection(BaseModel):
    """Structured section used by delivery HTML and replay snapshots."""

    key: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=100)
    items: list[str] = Field(default_factory=list, max_length=20)


class DeliveryBundleDescriptor(BaseModel):
    """Structured delivery descriptor shared across frontend replay/export paths."""

    title: str = Field(min_length=1, max_length=100)
    filenameBase: str = Field(min_length=1, max_length=120)
    summary: str = Field(default="", max_length=5000)
    summaryLines: list[str] = Field(default_factory=list, max_length=20)
    metrics: list[DeliveryBundleMetric] = Field(default_factory=list, max_length=16)
    warnings: list[str] = Field(default_factory=list, max_length=20)
    subagentTrail: list[str] = Field(default_factory=list, max_length=20)
    shareContent: str = Field(min_length=1, max_length=50000)
    htmlDocumentTitle: str = Field(min_length=1, max_length=160)
    htmlSections: list[DeliveryBundleSection] = Field(default_factory=list, max_length=12)


class DeliveryBundleShareMetadata(BaseModel):
    """Share metadata co-packaged with delivery artifacts."""

    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=50000)


class DeliveryBundlePayload(BaseModel):
    """Full delivery bundle persisted behind share links."""

    schemaVersion: Literal["2026-03-29"] = "2026-03-29"
    descriptor: DeliveryBundleDescriptor
    artifact: dict[str, Any] | None = None
    executionReceipt: dict[str, Any] | None = None
    htmlContent: str = Field(min_length=1, max_length=200000)
    share: DeliveryBundleShareMetadata


class ShareCreateRequest(BaseModel):
    """Create share-link request body."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    content: str = Field(min_length=1, max_length=50000)
    title: str | None = Field(default=None, max_length=100)
    html_content: str | None = Field(default=None, max_length=200000)
    delivery_bundle: DeliveryBundlePayload | None = None

    @field_validator("title", "html_content", mode="after")
    @classmethod
    def _empty_string_to_none(cls, value: str | None) -> str | None:
        """Normalize blank optional share fields so persistence sees missing values."""

        return value or None


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
    html_content: str | None = None
    delivery_bundle: DeliveryBundlePayload | None = None
    created_at: str
