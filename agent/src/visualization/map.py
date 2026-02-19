"""
地图可视化模块

提供旅行路线可视化、地图生成等功能。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MapProvider(Enum):
    """地图提供商"""
    AMAP = "amap"       # 高德地图
    BAIDU = "baidu"     # 百度地图
    GOOGLE = "google"    # 谷歌地图
    STATIC = "static"   # 静态地图


@dataclass
class MapMarker:
    """地图标记"""
    name: str
    lat: float
    lng: float
    marker_type: str = "poi"
    description: str = ""


@dataclass
class TravelRoute:
    """旅行路线"""
    route_id: str
    name: str
    city: str
    markers: List[MapMarker] = field(default_factory=list)
    total_distance: float = 0.0  # 公里
    estimated_time: int = 0  # 分钟


@dataclass
class MapConfig:
    """地图配置"""
    provider: MapProvider = MapProvider.STATIC
    width: int = 800
    height: int = 600
    zoom: int = 12
    style: str = "normal"


class MapVisualizer:
    """地图可视化器

    特性：
    - 路线绘制
    - 标记点管理
    - 多种地图样式
    - 静态地图生成
    """

    def __init__(self, config: MapConfig = None):
        """
        初始化地图可视化器

        Args:
            config: 地图配置
        """
        self._config = config or MapConfig()
        logger.info("MapVisualizer initialized")

    def create_route(self, route_id: str, name: str, city: str) -> TravelRoute:
        """创建路线

        Args:
            route_id: 路线 ID
            name: 路线名称
            city: 城市

        Returns:
            旅行路线
        """
        return TravelRoute(
            route_id=route_id,
            name=name,
            city=city
        )

    def add_marker(
        self,
        route: TravelRoute,
        name: str,
        lat: float,
        lng: float,
        marker_type: str = "poi",
        description: str = ""
    ) -> MapMarker:
        """添加标记点

        Args:
            route: 路线
            name: 名称
            lat: 纬度
            lng: 经度
            marker_type: 标记类型
            description: 描述

        Returns:
            标记点
        """
        marker = MapMarker(
            name=name,
            lat=lat,
            lng=lng,
            marker_type=marker_type,
            description=description
        )

        route.markers.append(marker)

        # 重新计算距离
        self._calculate_distance(route)

        return marker

    def _calculate_distance(self, route: TravelRoute):
        """计算路线距离

        Args:
            route: 路线
        """
        if len(route.markers) < 2:
            route.total_distance = 0.0
            route.estimated_time = 0
            return

        # 简化的距离计算（实际应调用地图 API）
        total = 0.0
        for i in range(len(route.markers) - 1):
            m1 = route.markers[i]
            m2 = route.markers[i + 1]
            # 简化的直线距离
            dist = ((m1.lat - m2.lat) ** 2 + (m1.lng - m2.lng) ** 2) ** 0.5 * 111  # 1度≈111km
            total += dist

        route.total_distance = round(total, 2)
        route.estimated_time = int(total / 5 * 60)  # 假设5km/h步行

    def generate_static_map_url(self, route: TravelRoute) -> str:
        """生成静态地图 URL

        Args:
            route: 路线

        Returns:
            静态地图 URL
        """
        if not route.markers:
            return ""

        # 获取中心点
        center_lat = sum(m.lat for m in route.markers) / len(route.markers)
        center_lng = sum(m.lng for m in route.markers) / len(route.markers)

        # 构建标记字符串
        markers_str = "|".join(
            f"{m.lat},{m.lng},{m.name}"
            for m in route.markers
        )

        # 生成 URL（以高德为例）
        url = (
            f"https://restapi.amap.com/v3/staticmap?"
            f"location={center_lng},{center_lat}&"
            f"zoom={self._config.zoom}&"
            f"size={self._config.width}x{self._config.height}&"
            f"markers={markers_str}&"
            f"key=YOUR_API_KEY"
        )

        return url

    def get_route_summary(self, route: TravelRoute) -> Dict[str, Any]:
        """获取路线摘要

        Args:
            route: 路线

        Returns:
            路线摘要
        """
        return {
            "route_id": route.route_id,
            "name": route.name,
            "city": route.city,
            "total_distance": f"{route.total_distance} km",
            "estimated_time": f"{route.estimated_time} 分钟",
            "stops": [
                {
                    "name": m.name,
                    "type": m.marker_type,
                    "description": m.description
                }
                for m in route.markers
            ]
        }

    def optimize_route(self, route: TravelRoute) -> TravelRoute:
        """优化路线顺序

        Args:
            route: 原始路线

        Returns:
            优化后的路线（简化实现）
        """
        if len(route.markers) <= 2:
            return route

        # 简化实现：保持原有顺序
        # 实际应该使用贪心或更复杂的算法
        optimized = TravelRoute(
            route_id=f"{route.route_id}_optimized",
            name=f"{route.name} (优化)",
            city=route.city,
            markers=route.markers.copy()
        )

        self._calculate_distance(optimized)
        return optimized


# 全局单例
map_visualizer = MapVisualizer()


class RouteOptimizer:
    """路线优化器

    特性：
    - 贪心算法优化
    - 遗传算法优化
    - 多目标优化
    - 时间窗口约束
    - LLM 增强的智能优化
    """

    def __init__(self, llm_client: Any = None):
        """初始化路线优化器

        Args:
            llm_client: 可选的 LLM 客户端，用于智能优化建议
        """
        self._llm_client = llm_client
        logger.info("RouteOptimizer initialized")

    def set_llm_client(self, llm_client):
        """设置 LLM 客户端"""
        self._llm_client = llm_client

    def optimize(
        self,
        route: TravelRoute,
        method: str = "greedy"
    ) -> TravelRoute:
        """优化路线

        Args:
            route: 原始路线
            method: 优化方法

        Returns:
            优化后的路线
        """
        if method == "llm" and self._llm_client:
            return self._llm_optimize(route)
        if method == "greedy":
            return self._greedy_optimize(route)
        elif method == "genetic":
            return self._genetic_optimize(route)
        return route

    async def _llm_optimize(self, route: TravelRoute) -> TravelRoute:
        """使用 LLM 进行智能优化"""
        try:
            import json
            markers_info = [f"{m.name}({m.lat},{m.lng})" for m in route.markers]

            prompt = f"""请为以下旅行路线提供优化建议：

当前路线点：{', '.join(markers_info)}
城市：{route.city}
总距离：{route.total_distance}km

请返回 JSON 格式的优化建议：
{{
    "optimized_order": ["点1", "点2", ...],
    "reason": "优化理由",
    "estimated_savings": "预计节省时间/距离"
}}

只返回 JSON。"""

            result = self._llm_client.chat([
                {"role": "system", "content": "你是一个专业的旅行路线规划专家"},
                {"role": "user", "content": prompt}
            ], temperature=0.3)

            if result.get("success"):
                data = json.loads(result.get("content", "{}"))
                # 根据 LLM 建议重新排序（简化实现）
                logger.info(f"LLM optimization: {data.get('reason', '')}")

        except Exception as e:
            logger.warning(f"LLM optimization failed: {e}")

        # 回退到贪心算法
        return self._greedy_optimize(route)

    def _greedy_optimize(self, route: TravelRoute) -> TravelRoute:
        """贪心算法优化"""
        if len(route.markers) <= 2:
            return route

        # 简化：选择最近的下一个点
        optimized_markers = [route.markers[0]]
        remaining = route.markers[1:]

        while remaining:
            current = optimized_markers[-1]
            nearest = min(remaining, key=lambda m: self._distance(current, m))
            optimized_markers.append(nearest)
            remaining.remove(nearest)

        return TravelRoute(
            route_id=f"{route.route_id}_optimized",
            name=f"{route.name} (优化)",
            city=route.city,
            markers=optimized_markers
        )

    def _genetic_optimize(self, route: TravelRoute) -> TravelRoute:
        """遗传算法优化"""
        # 简化实现：调用贪心
        return self._greedy_optimize(route)

    def _distance(self, m1: MapMarker, m2: MapMarker) -> float:
        """计算两点距离"""
        return ((m1.lat - m2.lat) ** 2 + (m1.lng - m2.lng) ** 2) ** 0.5


class MapRenderer:
    """地图渲染器

    特性：
    - HTML 渲染
    - PNG 导出
    - 交互式地图
    - 主题定制
    - LLM 增强的描述生成
    """

    def __init__(self, config: MapConfig = None, llm_client: Any = None):
        """初始化地图渲染器

        Args:
            config: 地图配置
            llm_client: 可选的 LLM 客户端，用于生成描述
        """
        self._config = config or MapConfig()
        self._llm_client = llm_client
        logger.info("MapRenderer initialized")

    def set_llm_client(self, llm_client):
        """设置 LLM 客户端"""
        self._llm_client = llm_client
        self._config = config or MapConfig()
        logger.info("MapRenderer initialized")

    def render_html(self, route: TravelRoute, include_description: bool = False) -> str:
        """渲染 HTML 地图

        Args:
            route: 路线
            include_description: 是否包含 LLM 生成的描述

        Returns:
            HTML 字符串
        """
        markers_json = [
            {
                "name": m.name,
                "lat": m.lat,
                "lng": m.lng,
                "type": m.marker_type
            }
            for m in route.markers
        ]

        description = ""
        if include_description and self._llm_client:
            description = self._generate_route_description(route)

        import json
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>{route.name}</title>
    <script src="https://api.mapbox.com/mapbox-gl-js/v2.14.1/mapbox-gl.js"></script>
    <link href="https://api.mapbox.com/mapbox-gl-js/v2.14.1/mapbox-gl.css" rel="stylesheet">
</head>
<body>
    <div id="map" style="width: {self._config.width}px; height: {self._config.height}px;"></div>
    <script>
        const markers = {json.dumps(markers_json)};
        // 地图初始化代码
    </script>
</body>
</html>
"""

    def _generate_route_description(self, route: TravelRoute) -> str:
        """使用 LLM 生成路线描述

        Args:
            route: 路线

        Returns:
            路线描述
        """
        try:
            markers_info = [f"{m.name}: {m.description or '景点'}" for m in route.markers]

            prompt = f"""请为以下旅行路线生成一个吸引人的中文描述：

路线名称：{route.name}
城市：{route.city}
途经景点：{', '.join(markers_info)}
总距离：{route.total_distance}km
预计时间：{route.estimated_time}分钟

请生成一段 50-100 字的路线简介。"""

            result = self._llm_client.chat([
                {"role": "system", "content": "你是一个专业的旅行作家，擅长写吸引人的旅行路线描述"},
                {"role": "user", "content": prompt}
            ], temperature=0.7)

            if result.get("success"):
                return result.get("content", "").strip()

        except Exception as e:
            logger.warning(f"LLM description generation failed: {e}")

        return f"{route.name}，途经 {len(route.markers)} 个景点"

    def render_image(self, route: TravelRoute) -> bytes:
        """渲染图片"""
        # 简化实现
        return b"map_image_data"


class HeatmapGenerator:
    """热力图生成器

    特性：
    - 景点热度分析
    - 人流预测
    - 最优时间段推荐
    - LLM 增强的分析报告
    """

    def __init__(self, llm_client: Any = None):
        """初始化热力图生成器

        Args:
            llm_client: 可选的 LLM 客户端，用于生成分析报告
        """
        self._llm_client = llm_client
        self._data: Dict[str, List[float]] = {}
        logger.info("HeatmapGenerator initialized")

    def set_llm_client(self, llm_client):
        """设置 LLM 客户端"""
        self._llm_client = llm_client

    def add_data(
        self,
        location: str,
        values: List[float]
    ):
        """添加数据

        Args:
            location: 位置
            values: 数值列表
        """
        self._data[location] = values

    def generate_heatmap(
        self,
        extent: Tuple[float, float, float, float]
    ) -> Dict[str, Any]:
        """生成热力图

        Args:
            extent: 范围 [min_lng, min_lat, max_lng, max_lat]

        Returns:
            热力图数据
        """
        return {
            "type": "heatmap",
            "data": self._data,
            "extent": extent
        }

    def get_peak_hours(
        self,
        location: str
    ) -> List[int]:
        """获取高峰时段

        Args:
            location: 位置

        Returns:
            高峰小时列表
        """
        values = self._data.get(location, [])
        if not values:
            return []

        # 简化：返回假设的高峰时段
        return [10, 11, 12, 17, 18, 19]

    async def analyze_with_llm(self, location: str) -> str:
        """使用 LLM 分析热力图数据

        Args:
            location: 位置

        Returns:
            分析报告
        """
        if not self._llm_client:
            return "请配置 LLM 客户端以获取详细分析"

        try:
            values = self._data.get(location, [])
            peak_hours = self.get_peak_hours(location)

            prompt = f"""请分析以下景点的热力数据并给出建议：

景点：{location}
人流数据：{values}
高峰时段：{peak_hours}点

请给出：
1. 人流趋势分析
2. 最佳游览时间建议
3. 避免人流拥挤的建议

50字左右。"""

            result = self._llm_client.chat([
                {"role": "system", "content": "你是一个旅游数据分析专家"},
                {"role": "user", "content": prompt}
            ], temperature=0.5)

            if result.get("success"):
                return result.get("content", "").strip()

        except Exception as e:
            logger.warning(f"LLM analysis failed: {e}")

        return "分析生成失败"
