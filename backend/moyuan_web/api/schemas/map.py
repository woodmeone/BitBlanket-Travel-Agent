"""Map endpoint schemas."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


RouteSpot = Annotated[str, Field(min_length=1, max_length=120)]


class RoutePreviewRequest(BaseModel):
    """Request payload for route preview."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    spots: list[RouteSpot] = Field(min_length=2, max_length=10)
    city: str | None = Field(default=None, max_length=100)
    provider: Literal["amap"] = "amap"

    @field_validator("city", mode="after")
    @classmethod
    def _empty_city_to_none(cls, value: str | None) -> str | None:
        """Treat blank city names as absent after whitespace normalization."""

        return value or None


class RoutePointItem(BaseModel):
    """Response point item."""

    name: str
    lat: float
    lng: float


class RoutePreviewResponse(BaseModel):
    """Response payload for route preview."""

    success: bool = True
    provider: str
    points: list[RoutePointItem]
    distance_m: float
    duration_s: float
    static_map_url: str
    route_polyline: list[tuple[float, float]]
