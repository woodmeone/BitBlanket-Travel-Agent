"""地图路线预览服务兼容性门面（Facade），委托给高德路线预览服务。

门面模式说明：
    MapService 作为对外的统一 API 入口，内部将实际操作委托给
    AmapRoutePreviewService 处理，封装了高德地图 API 的调用细节。

高德地图 API 说明：
    通过高德地图的路线规划 API，计算多个景点之间的驾车路线，
    生成路线几何摘要和静态地图 URL，供前端展示路线预览图。
"""

from __future__ import annotations

import os

from .map import AmapRoutePreviewService, RoutePoint, RoutePreview


class MapService:
    """地图服务门面，暴露现有 API 同时委托给更小的协作者。"""

    def __init__(self, route_preview_service: AmapRoutePreviewService | None = None) -> None:
        """创建门面，默认使用高德路线预览服务。

        Args:
            route_preview_service: 可选的路线预览服务实例，
                未提供时使用 AMAP_KEY 环境变量创建高德服务
        """
        self._route_preview_service = route_preview_service or AmapRoutePreviewService(
            amap_key=os.getenv("AMAP_KEY", "").strip(),
        )

    async def route_preview(
        self,
        *,
        spots: list[str],
        city: str | None = None,
        provider: str | None = None,
    ) -> RoutePreview:
        """返回路线预览载荷，包含几何摘要和静态地图 URL。

        Args:
            spots: 景点名称列表（如 ["亚龙湾", "天涯海角", "南山寺"]）
            city: 所在城市名称（可选，用于提高路线规划精度）
            provider: 地图服务提供商（可选，默认高德）

        Returns:
            RoutePreview 对象，含路线点、距离、时长和静态地图 URL
        """
        return await self._route_preview_service.route_preview(
            spots=spots,
            city=city,
            provider=provider,
        )


__all__ = ["MapService", "RoutePoint", "RoutePreview"]
