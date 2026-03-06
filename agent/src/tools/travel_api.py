"""
================================================================================
真实旅游 API 数据源
================================================================================

提供真实旅游数据的工具适配器。
目前使用模拟数据，可接入真实 API。

__all__ = [
    "TravelAPIClient",
    "get_travel_api_client",
]

真实 API 来源:
- 携程 API (ctrip.com)
- 马蜂窝 API (mafengwo.com)
- 去哪 er API (qunar.com)

使用示例:
```python
from tools.travel_api import TravelAPIClient

client = TravelAPIClient()

# 搜索城市
cities = await client.search_cities("北京")

# 查询景点
attractions = await client.search_attractions("北京", category="historical")

# 查询酒店
hotels = await client.search_hotels("北京", district="东城区")

# 获取天气
weather = await client.get_weather("北京")
```

================================================================================
"""

import os
import json
import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

# 配置日志
logger = logging.getLogger("agent.tools.travel_api")


class TravelAPIClient:
    """
    旅游 API 客户端

    统一封装多个旅游数据源的 API 调用
    """

    def __init__(self, use_cache: bool = True):
        """
        初始化

        Args:
            use_cache: 是否使用缓存
        """
        self.use_cache = use_cache
        self._cache: Dict[str, Any] = {}

    def _get_cache(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if self.use_cache and key in self._cache:
            return self._cache[key]
        return None

    def _set_cache(self, key: str, value: Any):
        """设置缓存"""
        if self.use_cache:
            self._cache[key] = value

    async def search_cities(self, query: str) -> List[Dict[str, Any]]:
        """
        搜索城市

        Args:
            query: 搜索关键词

        Returns:
            城市列表
        """
        cache_key = f"city:{query}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        # 模拟 API 调用
        # 真实实现应该调用携程/马蜂窝 API
        await asyncio.sleep(0.1)  # 模拟网络延迟

        # 城市数据库
        cities_db = [
            {
                "id": "101010100",
                "name": "北京",
                "pinyin": "beijing",
                "province": "北京",
                "description": "中国的首都，拥有悠久的历史和丰富的文化遗产",
                "highlights": ["故宫", "长城", "天安门", "颐和园"],
                "best_time": "春秋季节",
                "weather": "四季分明",
                "image": "https://example.com/beijing.jpg",
                "rating": 4.8
            },
            {
                "id": "101020100",
                "name": "上海",
                "pinyin": "shanghai",
                "province": "上海",
                "description": "国际化大都市，中西文化交融",
                "highlights": ["外滩", "东方明珠", "豫园", "田子坊"],
                "best_time": "春秋季节",
                "weather": "亚热带季风气候",
                "image": "https://example.com/shanghai.jpg",
                "rating": 4.7
            },
            {
                "id": "101280100",
                "name": "广州",
                "pinyin": "guangzhou",
                "province": "广东",
                "description": "华南地区最大城市，美食天堂",
                "highlights": ["广州塔", "珠江新城", "上下九", "白云山"],
                "best_time": "10月-次年4月",
                "weather": "亚热带季风气候",
                "rating": 4.6
            },
            {
                "id": "101280600",
                "name": "深圳",
                "pinyin": "shenzhen",
                "province": "广东",
                "description": "现代化国际大都市",
                "highlights": ["世界之窗", "欢乐谷", "东部华侨城", "深圳湾"],
                "best_time": "10月-次年5月",
                "weather": "亚热带季风气候",
                "rating": 4.5
            },
            {
                "id": "101210100",
                "name": "杭州",
                "pinyin": "hangzhou",
                "province": "浙江",
                "description": "人间天堂，丝绸之府",
                "highlights": ["西湖", "灵隐寺", "宋城", "西溪湿地"],
                "best_time": "3月-5月",
                "weather": "亚热带季风气候",
                "rating": 4.9
            },
            {
                "id": "101230400",
                "name": "丽江",
                "pinyin": "lijiang",
                "province": "云南",
                "description": "世界文化遗产，古城之美",
                "highlights": ["丽江古城", "玉龙雪山", "泸沽湖", "束河古镇"],
                "best_time": "春秋季节",
                "weather": "高原季风气候",
                "rating": 4.8
            },
            {
                "id": "101260100",
                "name": "三亚",
                "pinyin": "sanya",
                "province": "海南",
                "description": "东方夏威夷，海滨度假胜地",
                "highlights": ["亚龙湾", "蜈支洲岛", "天涯海角", "南山文化旅游区"],
                "best_time": "10月-次年3月",
                "weather": "热带季风气候",
                "rating": 4.9
            },
            {
                "id": "101190400",
                "name": "苏州",
                "pinyin": "suzhou",
                "province": "江苏",
                "description": "江南水乡，园林之城",
                "highlights": ["拙政园", "周庄", "平江路", "虎丘"],
                "best_time": "4月-10月",
                "weather": "亚热带季风气候",
                "rating": 4.7
            },
            {
                "id": "101200100",
                "name": "西安",
                "pinyin": "xian",
                "province": "陕西",
                "description": "十三朝古都，历史文化名城",
                "highlights": ["秦始皇兵马俑", "大雁塔", "城墙", "回民街"],
                "best_time": "3月-5月, 9月-10月",
                "weather": "温带季风气候",
                "rating": 4.8
            },
            {
                "id": "101270100",
                "name": "成都",
                "pinyin": "chengdu",
                "province": "四川",
                "description": "天府之国，美食之都",
                "highlights": ["大熊猫基地", "宽窄巷子", "锦里", "青城山"],
                "best_time": "3月-6月, 9月-11月",
                "weather": "亚热带季风气候",
                "rating": 4.7
            }
        ]

        # 搜索匹配
        query_lower = query.lower()
        results = [
            city for city in cities_db
            if query_lower in city["name"].lower()
            or query_lower in city["pinyin"].lower()
            or query_lower in city["province"].lower()
            or query_lower in city["description"].lower()
        ]

        # 如果没有精确匹配，返回部分匹配
        if not results:
            results = cities_db[:5]

        self._set_cache(cache_key, results)
        return results

    async def search_attractions(
        self,
        city: str,
        category: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        查询景点

        Args:
            city: 城市名称
            category: 景点类别 (natural/historical/entertainment/food)
            page: 页码
            page_size: 每页数量

        Returns:
            景点列表和分页信息
        """
        cache_key = f"attractions:{city}:{category}:{page}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        await asyncio.sleep(0.1)

        # 景点数据库
        attractions_db = {
            "北京": {
                "historical": [
                    {"id": "a001", "name": "故宫", "desc": "明清两代皇家宫殿", "ticket": "60元", "hours": "8:30-17:00", "rating": 4.9, "address": "北京市东城区景山前街4号"},
                    {"id": "a002", "name": "长城", "desc": "中国古代伟大工程", "ticket": "40-65元", "hours": "7:00-18:00", "rating": 4.8, "address": "北京市延庆区G6京藏高速58号"},
                    {"id": "a003", "name": "天坛", "desc": "皇帝祭天祈谷场所", "ticket": "34元", "hours": "6:30-21:00", "rating": 4.7, "address": "北京市东城区天坛内东里7号"}
                ],
                "natural": [
                    {"id": "a004", "name": "颐和园", "desc": "清代皇家园林", "ticket": "30元", "hours": "6:30-18:00", "rating": 4.8, "address": "北京市海淀区新建宫门路19号"},
                    {"id": "a005", "name": "北海公园", "desc": "历史悠久的皇家园林", "ticket": "10元", "hours": "6:00-21:00", "rating": 4.6, "address": "北京市西城区文津街1号"}
                ]
            },
            "上海": {
                "historical": [
                    {"id": "a101", "name": "外滩", "desc": "万国建筑群", "ticket": "免费", "hours": "全天", "rating": 4.8, "address": "上海市黄浦区中山东一路"},
                    {"id": "a102", "name": "豫园", "desc": "江南园林", "ticket": "40元", "hours": "8:30-17:00", "rating": 4.6, "address": "上海市黄浦区安仁街137号"}
                ],
                "entertainment": [
                    {"id": "a103", "name": "东方明珠", "desc": "上海标志性建筑", "ticket": "180元", "hours": "8:00-21:30", "rating": 4.5, "address": "上海市浦东新区世纪大道1号"}
                ]
            },
            "三亚": {
                "natural": [
                    {"id": "a201", "name": "亚龙湾", "desc": "天下第一湾", "ticket": "免费", "hours": "全天", "rating": 4.9, "address": "三亚市吉阳区亚龙湾"},
                    {"id": "a202", "name": "蜈支洲岛", "desc": "海岛度假胜地", "ticket": "168元", "hours": "8:00-18:30", "rating": 4.8, "address": "三亚市海棠区蜈支洲岛"}
                ]
            }
        }

        attractions = attractions_db.get(city, {})

        if category:
            attractions = attractions.get(category, [])
        else:
            # 合并所有类别
            all_attractions = []
            for cat_attractions in attractions.values():
                all_attractions.extend(cat_attractions)
            attractions = all_attractions

        # 分页
        start = (page - 1) * page_size
        end = start + page_size
        page_data = attractions[start:end]

        result = {
            "city": city,
            "category": category,
            "page": page,
            "page_size": page_size,
            "total": len(attractions),
            "data": page_data
        }

        self._set_cache(cache_key, result)
        return result

    async def search_hotels(
        self,
        city: str,
        district: Optional[str] = None,
        check_in: Optional[str] = None,
        check_out: Optional[str] = None,
        price_range: Optional[tuple] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        搜索酒店

        Args:
            city: 城市
            district: 商圈/区域
            check_in: 入住日期
            check_out: 退房日期
            price_range: 价格区间 (min, max)
            page: 页码
            page_size: 每页数量

        Returns:
            酒店列表
        """
        await asyncio.sleep(0.15)

        # 模拟酒店数据
        hotels = [
            {"id": "h001", "name": f"{city}王府饭店", "district": "市中心", "rating": 4.8, "price": 680, "image": "https://example.com/h1.jpg"},
            {"id": "h002", "name": f"{city}香格里拉大酒店", "district": "市中心", "rating": 4.9, "price": 980, "image": "https://example.com/h2.jpg"},
            {"id": "h003", "name": f"{city}希尔顿酒店", "district": "金融区", "rating": 4.7, "price": 580, "image": "https://example.com/h3.jpg"},
        ]

        # 过滤
        if district:
            hotels = [h for h in hotels if h["district"] == district]
        if price_range:
            hotels = [h for h in hotels if price_range[0] <= h["price"] <= price_range[1]]

        return {
            "city": city,
            "page": page,
            "page_size": page_size,
            "total": len(hotels),
            "data": hotels
        }

    async def get_weather(self, city: str, days: int = 7) -> Dict[str, Any]:
        """
        获取天气预报

        Args:
            city: 城市
            days: 天数

        Returns:
            天气信息
        """
        cache_key = f"weather:{city}:{days}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        await asyncio.sleep(0.1)

        # 模拟天气数据
        weather_types = ["晴", "多云", "阴", "小雨", "晴"]
        temps = [(18, 28), (20, 30), (19, 27), (17, 25), (20, 29)]

        forecast = []
        for i in range(days):
            forecast.append({
                "date": f"2024-{(i // 30) + 1:02d}{(i % 30) + 1:02d}",
                "weather": weather_types[i % len(weather_types)],
                "temp_low": temps[i % len(temps)][0],
                "temp_high": temps[i % len(temps)][1],
                "wind": "东南风3-4级",
                "pm25": "35"
            })

        result = {
            "city": city,
            "current": {
                "weather": "晴",
                "temp": 25,
                "humidity": "65%",
                "wind": "东南风3级"
            },
            "forecast": forecast
        }

        self._set_cache(cache_key, result)
        return result


# 全局客户端实例
_travel_api_client: Optional[TravelAPIClient] = None


def get_travel_api_client() -> TravelAPIClient:
    """获取旅游 API 客户端单例"""
    global _travel_api_client
    if _travel_api_client is None:
        _travel_api_client = TravelAPIClient()
    return _travel_api_client
