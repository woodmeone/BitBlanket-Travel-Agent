"""Automated tests for test travel provider metadata unit.

The module validates behavior, regressions, and integration contracts.
"""

from __future__ import annotations

import pytest

from agent.src.tools.travel_api import TravelAPIClient
from agent.src.tools.travel_tools import get_weather, query_attractions, query_hotels, search_cities


@pytest.mark.asyncio
async def test_travel_api_cities_fallback_to_secondary_provider(monkeypatch):
    monkeypatch.setenv("CITIES_API_PROVIDER", "cities-primary")
    monkeypatch.setenv("CITIES_API_FALLBACK_PROVIDER", "cities-secondary")
    monkeypatch.setenv("CITIES_DOWN_PROVIDERS", "cities-primary")

    client = TravelAPIClient(use_cache=False)
    result = await client.search_cities(query="北京")
    meta = result.get("_meta", {})

    assert meta.get("source") == "cities_provider:cities-secondary"
    assert meta.get("provider_used") == "cities-secondary"
    assert meta.get("fallback_used") is True
    assert meta.get("provider_chain") == ["cities-primary", "cities-secondary"]


@pytest.mark.asyncio
async def test_travel_api_attractions_returns_provider_metadata():
    client = TravelAPIClient(use_cache=True)
    result = await client.search_attractions(city="北京", category="historical", page=1, page_size=10)
    meta = result.get("_meta", {})
    assert meta.get("source", "").startswith("attraction_provider:")
    assert isinstance(meta.get("fetched_at"), str)
    assert meta.get("ttl_seconds") == 21600
    assert meta.get("is_stale") is False


@pytest.mark.asyncio
async def test_travel_api_hotels_returns_provider_metadata():
    client = TravelAPIClient(use_cache=True)
    result = await client.search_hotels(city="北京", district=None, page=1, page_size=10)
    meta = result.get("_meta", {})
    assert meta.get("source", "").startswith("hotel_provider:")
    assert isinstance(meta.get("fetched_at"), str)
    assert meta.get("ttl_seconds") == 1800
    assert meta.get("is_stale") is False


@pytest.mark.asyncio
async def test_travel_api_attractions_fallback_to_secondary_provider(monkeypatch):
    monkeypatch.setenv("ATTRACTIONS_API_PROVIDER", "attractions-primary")
    monkeypatch.setenv("ATTRACTIONS_API_FALLBACK_PROVIDER", "attractions-secondary")
    monkeypatch.setenv("ATTRACTIONS_DOWN_PROVIDERS", "attractions-primary")

    client = TravelAPIClient(use_cache=False)
    result = await client.search_attractions(city="北京", category="historical", page=1, page_size=10)
    meta = result.get("_meta", {})

    assert meta.get("source") == "attraction_provider:attractions-secondary"
    assert meta.get("provider_used") == "attractions-secondary"
    assert meta.get("fallback_used") is True
    assert meta.get("provider_chain") == ["attractions-primary", "attractions-secondary"]


@pytest.mark.asyncio
async def test_travel_api_hotels_fallback_to_secondary_provider(monkeypatch):
    monkeypatch.setenv("HOTELS_API_PROVIDER", "hotels-primary")
    monkeypatch.setenv("HOTELS_API_FALLBACK_PROVIDER", "hotels-secondary")
    monkeypatch.setenv("HOTELS_DOWN_PROVIDERS", "hotels-primary")

    client = TravelAPIClient(use_cache=False)
    result = await client.search_hotels(city="北京", district=None, page=1, page_size=10)
    meta = result.get("_meta", {})

    assert meta.get("source") == "hotel_provider:hotels-secondary"
    assert meta.get("provider_used") == "hotels-secondary"
    assert meta.get("fallback_used") is True
    assert meta.get("provider_chain") == ["hotels-primary", "hotels-secondary"]


@pytest.mark.asyncio
async def test_travel_api_weather_fallback_to_secondary_provider(monkeypatch):
    monkeypatch.setenv("WEATHER_API_PROVIDER", "primary-provider")
    monkeypatch.setenv("WEATHER_API_FALLBACK_PROVIDER", "secondary-provider")
    monkeypatch.setenv("WEATHER_DOWN_PROVIDERS", "primary-provider")

    client = TravelAPIClient(use_cache=False)
    result = await client.get_weather(city="北京", days=2)
    meta = result.get("_meta", {})

    assert meta.get("source") == "weather_provider:secondary-provider"
    assert meta.get("provider_used") == "secondary-provider"
    assert meta.get("fallback_used") is True
    assert meta.get("provider_chain") == ["primary-provider", "secondary-provider"]


@pytest.mark.asyncio
async def test_travel_api_weather_bypass_cache_sets_refresh_metadata():
    client = TravelAPIClient(use_cache=True)
    cached = await client.get_weather(city="北京", days=2)
    refreshed = await client.get_weather(city="北京", days=2, bypass_cache=True)

    cached_meta = cached.get("_meta", {})
    refreshed_meta = refreshed.get("_meta", {})
    assert cached_meta.get("refresh_attempted") is False
    assert cached_meta.get("refresh_success") is False
    assert refreshed_meta.get("refresh_attempted") is True
    assert refreshed_meta.get("refresh_success") is True


@pytest.mark.asyncio
async def test_travel_api_hotels_bypass_cache_sets_refresh_metadata():
    client = TravelAPIClient(use_cache=True)
    cached = await client.search_hotels(city="北京", district=None, page=1, page_size=10)
    refreshed = await client.search_hotels(city="北京", district=None, page=1, page_size=10, bypass_cache=True)

    cached_meta = cached.get("_meta", {})
    refreshed_meta = refreshed.get("_meta", {})
    assert cached_meta.get("refresh_attempted") is False
    assert cached_meta.get("refresh_success") is False
    assert refreshed_meta.get("refresh_attempted") is True
    assert refreshed_meta.get("refresh_success") is True


def test_travel_tools_attractions_metadata_passthrough():
    payload = query_attractions.invoke({"city": "北京", "category": "historical"})
    assert isinstance(payload, dict)
    assert "report" in payload
    meta = payload.get("_meta", {})
    assert meta.get("source", "").startswith("attraction_provider:")


def test_travel_tools_hotels_metadata_passthrough():
    payload = query_hotels.invoke({"city": "北京"})
    assert isinstance(payload, dict)
    assert "report" in payload
    meta = payload.get("_meta", {})
    assert meta.get("source", "").startswith("hotel_provider:")


def test_travel_tools_hotels_refresh_metadata_passthrough():
    payload = query_hotels.invoke({"city": "北京", "refresh": True})
    assert isinstance(payload, dict)
    meta = payload.get("_meta", {})
    assert meta.get("source", "").startswith("hotel_provider:")
    assert meta.get("refresh_attempted") is True
    assert meta.get("refresh_success") is True


def test_travel_tools_cities_metadata_passthrough():
    payload = search_cities.invoke({"query": "北京"})
    assert isinstance(payload, dict)
    assert "report" in payload
    meta = payload.get("_meta", {})
    assert meta.get("source", "").startswith("cities_provider:")


def test_travel_tools_weather_refresh_metadata_passthrough():
    payload = get_weather.invoke({"city": "北京", "days": 2, "refresh": True})
    assert isinstance(payload, dict)
    meta = payload.get("_meta", {})
    assert meta.get("source", "").startswith("weather_provider:")
    assert meta.get("refresh_attempted") is True
    assert meta.get("refresh_success") is True
