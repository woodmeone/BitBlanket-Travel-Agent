"""城市查询服务兼容性门面（Facade），委托给更小的协作者处理。

门面模式说明：
    CityService 作为对外的统一 API 入口，内部将实际操作委托给
    CityQueryService 和 CuratedCityCatalog 处理。
"""

from __future__ import annotations

from .city import CityQueryService, CuratedCityCatalog


class CityService:
    """城市服务门面，暴露现有 API 同时委托给更小的协作者。"""

    def __init__(self, catalog: CuratedCityCatalog | None = None) -> None:
        """创建带目录支持的查询服务门面。

        Args:
            catalog: 可选的城市目录实例，未提供时使用默认目录
        """
        self._catalog = catalog or CuratedCityCatalog()
        self._queries = CityQueryService(self._catalog)

    def list_cities(self, region: str | None = None, tags: str | None = None) -> list[dict[str, object]]:
        """返回筛选后的城市摘要列表，供城市列表端点使用。"""
        return self._queries.list_cities(region=region, tags=tags)

    def find_city(self, city_id: str) -> dict[str, object] | None:
        """根据 ID 查找一个精选城市。"""
        return self._queries.find_city(city_id)

    def build_city_detail(self, city: dict[str, object]) -> dict[str, object]:
        """构建单个城市的详情载荷。"""
        return self._queries.build_city_detail(city)

    def build_attractions(self, city_name: str) -> list[dict[str, object]]:
        """构建指定城市的景点载荷列表。"""
        return self._queries.build_attractions(city_name)

    def list_regions(self) -> list[str]:
        """列出支持的地区筛选器。"""
        return self._queries.list_regions()

    def list_tags(self) -> list[str]:
        """列出支持的城市标签。"""
        return self._queries.list_tags()
