"""City recommendation and lookup routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query

from ..api.error_codes import ApiErrorCode
from ..api.schemas.city import (
    CityAttractionsResponse,
    CityDetail,
    CityListResponse,
    CitySummary,
    RegionListResponse,
    TagListResponse,
)
from ..api.validation import CITY_ID_PATTERN, NON_BLANK_TEXT_PATTERN
from .errors import raise_api_error
from .service_resolver import get_city_service

router = APIRouter()

CityIdParam = Annotated[str, Path(min_length=1, max_length=64, pattern=CITY_ID_PATTERN)]


def _find_city_or_404(city_id: str) -> dict[str, object]:
    """Resolve city by ID or raise a standard not-found API error."""
    city = get_city_service().find_city(city_id)
    if city is None:
        raise_api_error(status_code=404, message="City not found", code=ApiErrorCode.CITY_NOT_FOUND)
    return city


@router.get("/cities", response_model=CityListResponse)
async def list_cities(
    region: Annotated[str | None, Query(description="Filter by region", min_length=1, max_length=40, pattern=NON_BLANK_TEXT_PATTERN)] = None,
    tags: Annotated[str | None, Query(description="Filter by comma-separated tags", min_length=1, max_length=200, pattern=NON_BLANK_TEXT_PATTERN)] = None,
):
    """List cities with optional region and tag filters."""
    result = get_city_service().list_cities(region=region, tags=tags)
    return CityListResponse(cities=[CitySummary.model_validate(item) for item in result])


@router.get("/cities/{city_id}", response_model=CityDetail)
async def get_city(city_id: CityIdParam):
    """Get full city detail by city identifier."""
    city = _find_city_or_404(city_id)
    return CityDetail.model_validate(get_city_service().build_city_detail(city))


@router.get("/cities/{city_id}/attractions", response_model=CityAttractionsResponse)
async def get_city_attractions(city_id: CityIdParam):
    """Get recommended attractions for the selected city."""
    city = _find_city_or_404(city_id)
    city_name = str(city["name"])
    return CityAttractionsResponse(city=city_name, attractions=get_city_service().build_attractions(city_name))


@router.get("/regions", response_model=RegionListResponse)
async def list_regions():
    """List supported region filters."""
    return RegionListResponse(regions=get_city_service().list_regions())


@router.get("/tags", response_model=TagListResponse)
async def list_tags():
    """List supported city tags for filtering."""
    return TagListResponse(tags=get_city_service().list_tags())
