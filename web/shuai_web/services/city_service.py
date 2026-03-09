"""City data service for route handlers."""

from __future__ import annotations


class CityService:
    """Encapsulates city list/filter/detail logic."""

    def __init__(self) -> None:
        self._cities: list[dict[str, object]] = [
            {"id": "beijing", "name": "北京", "region": "华北", "tags": ["历史文化", "首都", "古建筑"]},
            {"id": "shanghai", "name": "上海", "region": "华东", "tags": ["现代都市", "购物", "美食"]},
            {"id": "hangzhou", "name": "杭州", "region": "华东", "tags": ["自然风光", "人文历史", "休闲"]},
            {"id": "chengdu", "name": "成都", "region": "西南", "tags": ["美食", "休闲", "熊猫"]},
            {"id": "xian", "name": "西安", "region": "西北", "tags": ["历史文化", "古都", "美食"]},
            {"id": "xiamen", "name": "厦门", "region": "华南", "tags": ["海滨", "休闲", "文艺"]},
        ]

    def list_cities(self, region: str | None = None, tags: str | None = None) -> list[dict[str, object]]:
        result = list(self._cities)

        if region:
            region_value = region.strip()
            result = [item for item in result if item.get("region") == region_value]

        if tags:
            tag_set = {item.strip() for item in tags.split(",") if item.strip()}
            if tag_set:
                result = [
                    item
                    for item in result
                    if any(tag in tag_set for tag in (item.get("tags") or []))
                ]

        return result

    def find_city(self, city_id: str) -> dict[str, object] | None:
        return next((item for item in self._cities if item.get("id") == city_id), None)

    def build_city_detail(self, city: dict[str, object]) -> dict[str, object]:
        city_name = str(city["name"])
        city_region = str(city["region"])
        city_tags = city.get("tags") or []
        primary_tag = city_tags[0] if city_tags else "旅游"
        return {
            **city,
            "description": f"{city_name}是{city_region}热门旅游城市，以{primary_tag}著称。",
            "attractions": self.build_attractions(city_name),
            "avg_budget_per_day": 400,
            "best_seasons": ["春季", "秋季"],
        }

    @staticmethod
    def build_attractions(city_name: str) -> list[dict[str, object]]:
        return [
            {"name": f"{city_name}著名景点1", "type": "景点", "duration": "3小时", "ticket": 50},
            {"name": f"{city_name}著名景点2", "type": "景点", "duration": "4小时", "ticket": 60},
        ]

    def list_regions(self) -> list[str]:
        return sorted({str(item["region"]) for item in self._cities})

    def list_tags(self) -> list[str]:
        tags: set[str] = set()
        for city in self._cities:
            tags.update(city.get("tags") or [])
        return sorted(tags)
