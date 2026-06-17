"""旅行API客户端 —— 与后端API通信的统一适配层。

本模块封装了旅行数据的获取逻辑，提供统一的API客户端接口。
当前实现使用模拟数据（mock），未来可对接真实的旅行数据API。

核心设计模式：
  - Provider Chain（提供者链）：主备提供者自动切换，当主提供者不可用时自动降级到备用提供者
  - Cache with TTL（带过期时间的缓存）：缓存API响应，避免重复请求，支持强制刷新
  - Metadata Enrichment（元数据增强）：每次响应附带 _meta 信息，记录数据来源、缓存状态等

典型场景（以"成都3日游"为例）：
  1. Agent调用 search_cities("成都")
  2. TravelAPIClient 先查缓存，命中则直接返回
  3. 缓存未命中，走主提供者获取数据
  4. 主提供者不可用时，自动切换到备用提供者
  5. 返回结果附带 _meta 元数据（来源、是否过期、是否使用了备用提供者等）

环境变量配置：
  - {RESOURCE}_API_PROVIDER: 主提供者名称（如 CITIES_API_PROVIDER）
  - {RESOURCE}_API_FALLBACK_PROVIDER: 备用提供者名称
  - {RESOURCE}_DOWN_PROVIDERS: 标记为不可用的提供者列表（逗号分隔）
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("agent.tools.travel_api")


class TravelAPIClient:
    """【核心】统一旅行数据适配客户端，当前后端为模拟数据。

    职责：
      - 封装城市搜索、景点查询、酒店搜索、天气查询等API调用
      - 提供带TTL的缓存机制，减少重复请求
      - 实现主备提供者自动切换（Provider Chain failover）
      - 为每次响应附加元数据（_meta），记录数据来源和新鲜度

    缓存策略：
      - 城市数据：TTL 86400秒（24小时），变化频率低
      - 景点数据：TTL 21600秒（6小时），偶尔更新
      - 酒店数据：TTL 1800秒（30分钟），价格变化快
      - 天气数据：TTL 1800秒（30分钟），需保持新鲜
    """

    def __init__(self, use_cache: bool = True):
        """初始化API客户端。

        Args:
            use_cache: 是否启用缓存，默认True。关闭缓存时每次请求都重新获取数据。
        """
        self.use_cache = use_cache                   # 缓存开关
        self._cache: Dict[str, Any] = {}             # 缓存存储：key → 响应数据
        self._cache_meta: Dict[str, str] = {}        # 缓存元数据：key → ISO时间戳（记录缓存写入时间）

    @staticmethod
    def _now_iso() -> str:
        """返回当前UTC时间的ISO-8601格式字符串，用于时间戳记录。

        ISO-8601 是国际标准的日期时间表示格式，如 "2026-06-07T12:30:00+00:00"。
        """
        return datetime.now(timezone.utc).isoformat()

    def _get_cache(self, key: str, *, bypass_cache: bool = False) -> Optional[Any]:
        """从缓存中获取数据。

        Args:
            key: 缓存键，如 "city:成都"
            bypass_cache: 是否绕过缓存（强制刷新时为True）

        Returns:
            缓存的数据，未命中或绕过缓存时返回 None
        """
        if bypass_cache:
            return None
        if self.use_cache and key in self._cache:
            return self._cache[key]
        return None

    def _set_cache(self, key: str, value: Any) -> None:
        """将响应数据写入缓存，并记录写入时间戳。

        Args:
            key: 缓存键
            value: 要缓存的数据
        """
        if self.use_cache:
            self._cache[key] = value
            self._cache_meta[key] = self._now_iso()  # 记录缓存写入时间

    def _build_meta(self, key: str, source: str, ttl_seconds: int) -> Dict[str, Any]:
        """构建响应元数据，包含数据来源、获取时间和新鲜度判断。

        新鲜度判断逻辑：比较缓存写入时间与当前时间的差值，若超过TTL则标记为过期(is_stale)。

        Args:
            key: 缓存键，用于查找缓存写入时间
            source: 数据来源标识，如 "cities_provider:mock-cities-provider"
            ttl_seconds: 缓存有效期（秒）

        Returns:
            元数据字典，包含 source/fetched_at/ttl_seconds/is_stale
        """
        fetched_at = self._cache_meta.get(key, self._now_iso())
        is_stale = False
        try:
            fetched_dt = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
            age = datetime.now(timezone.utc) - fetched_dt.astimezone(timezone.utc)
            is_stale = age > timedelta(seconds=ttl_seconds)  # 缓存年龄超过TTL则标记为过期
        except Exception:
            is_stale = False
        return {
            "source": source,           # 数据来源
            "fetched_at": fetched_at,   # 数据获取时间
            "ttl_seconds": ttl_seconds, # 缓存有效期
            "is_stale": is_stale,       # 数据是否过期
        }

    @staticmethod
    def _refresh_meta(refresh_attempted: bool, refresh_success: bool) -> Dict[str, Any]:
        """构建刷新状态元数据，记录本次请求是否尝试了刷新以及是否成功。

        Args:
            refresh_attempted: 是否尝试了刷新过期数据
            refresh_success: 刷新是否成功

        Returns:
            刷新状态字典
        """
        return {
            "refresh_attempted": bool(refresh_attempted),  # 是否尝试刷新
            "refresh_success": bool(refresh_success),      # 刷新是否成功
        }

    @staticmethod
    def _weather_provider_chain() -> List[str]:
        """解析天气查询的提供者链（主→备）。

        提供者链是故障转移的核心机制：
          1. 优先使用主提供者（WEATHER_API_PROVIDER）
          2. 主提供者不可用时，切换到备用提供者（WEATHER_API_FALLBACK_PROVIDER）
          3. 若主备相同，则只保留一个（无需故障转移）

        Returns:
            提供者名称列表，如 ["mock-weather-provider", "mock-weather-fallback"]
        """
        primary = os.getenv("WEATHER_API_PROVIDER", "mock-weather-provider").strip() or "mock-weather-provider"
        fallback = os.getenv("WEATHER_API_FALLBACK_PROVIDER", "mock-weather-fallback").strip() or "mock-weather-fallback"
        if primary == fallback:
            return [primary]
        return [primary, fallback]

    @staticmethod
    def _is_provider_down(provider: str) -> bool:
        """检查指定提供者是否被标记为不可用。

        通过环境变量 WEATHER_DOWN_PROVIDERS 维护不可用提供者列表，
        用于模拟故障场景或手动禁用某个提供者。

        Args:
            provider: 提供者名称

        Returns:
            True 表示该提供者不可用
        """
        down_list = [item.strip() for item in os.getenv("WEATHER_DOWN_PROVIDERS", "").split(",") if item.strip()]
        return provider in down_list

    @staticmethod
    def _provider_chain(primary_env: str, fallback_env: str, primary_default: str, fallback_default: str) -> List[str]:
        """【核心】通用的提供者链解析方法，支持任意资源类型。

        所有API查询（城市/景点/酒店/天气）共用此方法解析主备提供者，
        通过不同的环境变量名和默认值区分不同资源类型。

        Args:
            primary_env: 主提供者环境变量名，如 "CITIES_API_PROVIDER"
            fallback_env: 备用提供者环境变量名，如 "CITIES_API_FALLBACK_PROVIDER"
            primary_default: 主提供者默认值
            fallback_default: 备用提供者默认值

        Returns:
            提供者名称列表（去重后）
        """
        primary = os.getenv(primary_env, primary_default).strip() or primary_default
        fallback = os.getenv(fallback_env, fallback_default).strip() or fallback_default
        if primary == fallback:
            return [primary]
        return [primary, fallback]

    @staticmethod
    def _is_provider_down_by_env(provider: str, down_env: str) -> bool:
        """通过指定环境变量检查提供者是否不可用。

        不同资源类型有不同的 DOWN_PROVIDERS 环境变量，
        如 CITIES_DOWN_PROVIDERS、HOTELS_DOWN_PROVIDERS 等。

        Args:
            provider: 提供者名称
            down_env: 不可用列表的环境变量名

        Returns:
            True 表示该提供者不可用
        """
        down_list = [item.strip() for item in os.getenv(down_env, "").split(",") if item.strip()]
        return provider in down_list

    async def search_cities(self, query: str) -> Dict[str, Any]:
        """【核心】搜索城市，支持提供者故障转移、缓存和结果归一化。

        流程：
          1. 构建缓存键 "city:{query}"
          2. 解析提供者链，检查主提供者是否可用
          3. 查缓存，命中则直接返回（附加最新元数据）
          4. 缓存未命中，从模拟数据库中搜索
          5. 写入缓存并返回结果

        典型场景：用户搜索"成都"，返回成都的城市信息（名称、省份、简介、必游景点等）。

        Args:
            query: 搜索关键词（城市名/拼音/省份/描述）

        Returns:
            包含 data（城市列表）和 _meta（元数据）的字典
        """
        cache_key = f"city:{query}"
        providers = self._provider_chain(
            primary_env="CITIES_API_PROVIDER",
            fallback_env="CITIES_API_FALLBACK_PROVIDER",
            primary_default="mock-cities-provider",
            fallback_default="mock-cities-fallback",
        )
        primary_provider = providers[0]
        selected_provider = primary_provider
        fallback_used = False

        # 检查主提供者是否不可用，若不可用则切换到备用
        if self._is_provider_down_by_env(primary_provider, "CITIES_DOWN_PROVIDERS"):
            if len(providers) > 1 and not self._is_provider_down_by_env(providers[1], "CITIES_DOWN_PROVIDERS"):
                selected_provider = providers[1]
                fallback_used = True
                logger.warning(
                    "Cities primary provider unavailable, switched to fallback provider: %s -> %s",
                    primary_provider,
                    selected_provider,
                )
            else:
                raise RuntimeError(f"No available cities provider. primary={primary_provider}")

        source = f"cities_provider:{selected_provider}"
        ttl_seconds = 86400  # 城市数据缓存24小时

        # 尝试从缓存获取
        cached = self._get_cache(cache_key)
        if cached:
            cached_result = dict(cached)
            cached_meta = dict(cached_result.get("_meta", {}))
            cached_result["_meta"] = {
                **cached_meta,
                **self._build_meta(cache_key, source=source, ttl_seconds=ttl_seconds),
                "provider_chain": providers,
                "provider_used": selected_provider,
                "fallback_used": fallback_used,
            }
            return cached_result

        # 模拟网络延迟
        await asyncio.sleep(0.05)

        # ---- 模拟城市数据库 ----
        cities_db: List[Dict[str, Any]] = [
            {
                "id": "101010100",
                "name": "北京",
                "pinyin": "beijing",
                "province": "北京",
                "description": "中国首都，历史文化名城。",
                "highlights": ["故宫", "长城", "天坛", "颐和园"],
                "best_time": "春秋季",
                "weather": "四季分明",
                "rating": 4.8,
            },
            {
                "id": "101020100",
                "name": "上海",
                "pinyin": "shanghai",
                "province": "上海",
                "description": "国际化都市，城市休闲与人文并重。",
                "highlights": ["外滩", "豫园", "陆家嘴", "新天地"],
                "best_time": "春秋季",
                "weather": "亚热带季风气候",
                "rating": 4.7,
            },
            {
                "id": "101230400",
                "name": "丽江",
                "pinyin": "lijiang",
                "province": "云南",
                "description": "古城与雪山并存，适合慢游。",
                "highlights": ["丽江古城", "玉龙雪山", "束河古镇"],
                "best_time": "春秋季",
                "weather": "高原气候",
                "rating": 4.8,
            },
        ]

        # 多字段模糊搜索：匹配城市名/拼音/省份/描述
        q = query.lower().strip()
        results = [
            city
            for city in cities_db
            if q in city["name"].lower()
            or q in city["pinyin"].lower()
            or q in city["province"].lower()
            or q in city["description"].lower()
        ]
        # 无匹配结果时返回前2个城市作为推荐
        if not results:
            results = cities_db[:2]

        result = {
            "query": query,
            "total": len(results),
            "data": results,
            "_meta": {
                **self._build_meta(cache_key, source=source, ttl_seconds=ttl_seconds),
                "provider_chain": providers,
                "provider_used": selected_provider,
                "fallback_used": fallback_used,
            },
        }
        self._set_cache(cache_key, result)
        # 写入缓存后重新构建元数据（更新 fetched_at）
        result["_meta"] = {
            **self._build_meta(cache_key, source=source, ttl_seconds=ttl_seconds),
            "provider_chain": providers,
            "provider_used": selected_provider,
            "fallback_used": fallback_used,
        }
        return result

    async def search_attractions(
        self,
        city: str,
        category: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """搜索景点，支持提供者故障转移和分页。

        典型场景：查询"成都"的"historical"类别景点，返回宽窄巷子、武侯祠等。

        Args:
            city: 城市名称
            category: 景点类别（historical/natural/entertainment），None则返回全部
            page: 页码，从1开始
            page_size: 每页数量

        Returns:
            包含 data（景点列表）和 _meta 的字典
        """
        cache_key = f"attractions:{city}:{category}:{page}:{page_size}"
        providers = self._provider_chain(
            primary_env="ATTRACTIONS_API_PROVIDER",
            fallback_env="ATTRACTIONS_API_FALLBACK_PROVIDER",
            primary_default="mock-attractions-provider",
            fallback_default="mock-attractions-fallback",
        )
        primary_provider = providers[0]
        selected_provider = primary_provider
        fallback_used = False
        if self._is_provider_down_by_env(primary_provider, "ATTRACTIONS_DOWN_PROVIDERS"):
            if len(providers) > 1 and not self._is_provider_down_by_env(providers[1], "ATTRACTIONS_DOWN_PROVIDERS"):
                selected_provider = providers[1]
                fallback_used = True
                logger.warning(
                    "Attractions primary provider unavailable, switched to fallback provider: %s -> %s",
                    primary_provider,
                    selected_provider,
                )
            else:
                raise RuntimeError(f"No available attractions provider. primary={primary_provider}")
        source = f"attraction_provider:{selected_provider}"
        ttl_seconds = 21600  # 景点数据缓存6小时

        cached = self._get_cache(cache_key)
        if cached:
            cached_result = dict(cached)
            cached_meta = dict(cached_result.get("_meta", {}))
            cached_result["_meta"] = {
                **cached_meta,
                **self._build_meta(cache_key, source=source, ttl_seconds=ttl_seconds),
                "provider_chain": providers,
                "provider_used": selected_provider,
                "fallback_used": fallback_used,
            }
            return cached_result

        await asyncio.sleep(0.08)

        # ---- 模拟景点数据库 ----
        attractions_db: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
            "北京": {
                "historical": [
                    {"id": "a001", "name": "故宫", "desc": "明清皇宫", "ticket": "60元", "hours": "8:30-17:00", "rating": 4.9},
                    {"id": "a002", "name": "八达岭长城", "desc": "长城经典段", "ticket": "40-65元", "hours": "7:00-18:00", "rating": 4.8},
                ],
                "natural": [
                    {"id": "a003", "name": "颐和园", "desc": "皇家园林", "ticket": "30元", "hours": "6:30-18:00", "rating": 4.8},
                ],
            },
            "上海": {
                "historical": [
                    {"id": "a101", "name": "豫园", "desc": "江南古典园林", "ticket": "40元", "hours": "8:30-17:00", "rating": 4.6},
                ],
                "entertainment": [
                    {"id": "a102", "name": "外滩", "desc": "黄浦江沿岸地标", "ticket": "免费", "hours": "全天", "rating": 4.8},
                ],
            },
        }

        city_bucket = attractions_db.get(city, {})
        if category:
            items = city_bucket.get(category, [])
        else:
            # 无类别时，合并所有类别的景点
            items = [it for values in city_bucket.values() for it in values]

        # 分页计算
        start = max(0, (page - 1) * page_size)
        data = items[start : start + page_size]
        result = {
            "city": city,
            "category": category,
            "page": page,
            "page_size": page_size,
            "total": len(items),
            "data": data,
            "_meta": {
                **self._build_meta(cache_key, source=source, ttl_seconds=ttl_seconds),
                "provider_chain": providers,
                "provider_used": selected_provider,
                "fallback_used": fallback_used,
            },
        }
        self._set_cache(cache_key, result)
        result["_meta"] = {
            **self._build_meta(cache_key, source=source, ttl_seconds=ttl_seconds),
            "provider_chain": providers,
            "provider_used": selected_provider,
            "fallback_used": fallback_used,
        }
        return result

    async def search_hotels(
        self,
        city: str,
        district: Optional[str] = None,
        check_in: Optional[str] = None,
        check_out: Optional[str] = None,
        price_range: Optional[tuple] = None,
        page: int = 1,
        page_size: int = 20,
        bypass_cache: bool = False,
    ) -> Dict[str, Any]:
        """搜索酒店，支持日期归一化、缓存和故障转移。

        典型场景：成都3日游，查询成都"市中心"区域的酒店，价格区间300-800元。

        Args:
            city: 城市名称
            district: 商圈/区域筛选
            check_in: 入住日期（暂未使用）
            check_out: 退房日期（暂未使用）
            price_range: 价格区间元组，如 (300, 800)
            page: 页码
            page_size: 每页数量
            bypass_cache: 是否绕过缓存（强制刷新酒店价格）

        Returns:
            包含 data（酒店列表）和 _meta 的字典
        """
        _ = (check_in, check_out)  # 预留字段，暂未使用
        cache_key = f"hotels:{city}:{district}:{price_range}:{page}:{page_size}"
        providers = self._provider_chain(
            primary_env="HOTELS_API_PROVIDER",
            fallback_env="HOTELS_API_FALLBACK_PROVIDER",
            primary_default="mock-hotels-provider",
            fallback_default="mock-hotels-fallback",
        )
        primary_provider = providers[0]
        selected_provider = primary_provider
        fallback_used = False
        if self._is_provider_down_by_env(primary_provider, "HOTELS_DOWN_PROVIDERS"):
            if len(providers) > 1 and not self._is_provider_down_by_env(providers[1], "HOTELS_DOWN_PROVIDERS"):
                selected_provider = providers[1]
                fallback_used = True
                logger.warning(
                    "Hotels primary provider unavailable, switched to fallback provider: %s -> %s",
                    primary_provider,
                    selected_provider,
                )
            else:
                raise RuntimeError(f"No available hotels provider. primary={primary_provider}")
        source = f"hotel_provider:{selected_provider}"
        ttl_seconds = 1800  # 酒店数据缓存30分钟（价格变化快）

        cached = self._get_cache(cache_key, bypass_cache=bypass_cache)
        if cached:
            cached_result = dict(cached)
            cached_meta = dict(cached_result.get("_meta", {}))
            cached_result["_meta"] = {
                **cached_meta,
                **self._build_meta(cache_key, source=source, ttl_seconds=ttl_seconds),
                **self._refresh_meta(refresh_attempted=False, refresh_success=False),
                "provider_chain": providers,
                "provider_used": selected_provider,
                "fallback_used": fallback_used,
            }
            return cached_result

        await asyncio.sleep(0.1)

        # ---- 模拟酒店数据库 ----
        hotels = [
            {"id": "h001", "name": f"{city}中心酒店", "district": "市中心", "rating": 4.7, "price": 580},
            {"id": "h002", "name": f"{city}商务酒店", "district": "金融区", "rating": 4.5, "price": 420},
            {"id": "h003", "name": f"{city}度假酒店", "district": "景区", "rating": 4.8, "price": 760},
        ]
        # 按区域筛选
        if district:
            hotels = [h for h in hotels if h["district"] == district]
        # 按价格区间筛选
        if price_range:
            hotels = [h for h in hotels if price_range[0] <= h["price"] <= price_range[1]]

        start = max(0, (page - 1) * page_size)
        result = {
            "city": city,
            "page": page,
            "page_size": page_size,
            "total": len(hotels),
            "data": hotels[start : start + page_size],
            "_meta": {
                **self._build_meta(cache_key, source=source, ttl_seconds=ttl_seconds),
                **self._refresh_meta(refresh_attempted=bypass_cache, refresh_success=bypass_cache),
                "provider_chain": providers,
                "provider_used": selected_provider,
                "fallback_used": fallback_used,
            },
        }
        self._set_cache(cache_key, result)
        result["_meta"] = {
            **self._build_meta(cache_key, source=source, ttl_seconds=ttl_seconds),
            **self._refresh_meta(refresh_attempted=bypass_cache, refresh_success=bypass_cache),
            "provider_chain": providers,
            "provider_used": selected_provider,
            "fallback_used": fallback_used,
        }
        return result

    async def get_weather(self, city: str, days: int = 7, bypass_cache: bool = False) -> Dict[str, Any]:
        """获取天气预报，支持缓存刷新和提供者故障转移。

        典型场景：成都3日游出发前，查询成都未来7天天气，决定是否带伞。

        Args:
            city: 城市名称
            days: 查询天数，默认7天
            bypass_cache: 是否绕过缓存（强制获取最新天气）

        Returns:
            包含 current（当前天气）、forecast（未来预报）和 _meta 的字典
        """
        cache_key = f"weather:{city}:{days}"
        ttl_seconds = 1800  # 天气数据缓存30分钟
        providers = self._weather_provider_chain()
        primary_provider = providers[0]

        # 尝试从缓存获取
        cached = self._get_cache(cache_key, bypass_cache=bypass_cache)
        if cached:
            cached_result = dict(cached)
            cached_meta = dict(cached_result.get("_meta", {}))
            source = str(cached_meta.get("source", f"weather_provider:{primary_provider}"))
            cached_result["_meta"] = {
                **cached_meta,
                **self._build_meta(cache_key, source=source, ttl_seconds=ttl_seconds),
                **self._refresh_meta(refresh_attempted=False, refresh_success=False),
            }
            return cached_result

        # 检查提供者可用性
        selected_provider = primary_provider
        fallback_used = False
        if self._is_provider_down(primary_provider):
            if len(providers) > 1 and not self._is_provider_down(providers[1]):
                selected_provider = providers[1]
                fallback_used = True
                logger.warning(
                    "Weather primary provider unavailable, switched to fallback provider: %s -> %s",
                    primary_provider,
                    selected_provider,
                )
            else:
                raise RuntimeError(f"No available weather provider. primary={primary_provider}")

        await asyncio.sleep(0.08)

        # ---- 模拟天气数据 ----
        weather_types = ["晴", "多云", "阴", "小雨", "晴"]
        temps = [(18, 28), (20, 30), (19, 27), (17, 25), (20, 29)]

        today = datetime.now(timezone.utc).date()
        forecast = []
        for i in range(max(1, days)):
            low, high = temps[i % len(temps)]
            forecast.append(
                {
                    "date": (today + timedelta(days=i)).isoformat(),
                    "weather": weather_types[i % len(weather_types)],
                    "temp_low": low,       # 最低温度
                    "temp_high": high,     # 最高温度
                    "wind": "东南风3-4级",
                    "pm25": "35",
                }
            )

        result = {
            "city": city,
            "current": {                  # 当前天气
                "weather": "晴",
                "temp": 25,               # 当前温度
                "humidity": "65%",        # 湿度
                "wind": "东南风2级",      # 风力
            },
            "forecast": forecast,         # 未来天气预报列表
            "_meta": {
                **self._build_meta(
                    cache_key,
                    source=f"weather_provider:{selected_provider}",
                    ttl_seconds=ttl_seconds,
                ),
                **self._refresh_meta(refresh_attempted=bypass_cache, refresh_success=bypass_cache),
                "provider_chain": providers,
                "provider_used": selected_provider,
                "fallback_used": fallback_used,
            },
        }
        self._set_cache(cache_key, result)
        result["_meta"] = {
            **self._build_meta(
                cache_key,
                source=f"weather_provider:{selected_provider}",
                ttl_seconds=ttl_seconds,
            ),
            **self._refresh_meta(refresh_attempted=bypass_cache, refresh_success=bypass_cache),
            "provider_chain": providers,
            "provider_used": selected_provider,
            "fallback_used": fallback_used,
        }
        return result


# ---- 单例模式 ----
# 全局唯一的API客户端实例，避免重复创建连接
_travel_api_client: Optional[TravelAPIClient] = None


def get_travel_api_client() -> TravelAPIClient:
    """获取旅行API客户端的单例实例。

    单例模式（Singleton）：确保整个应用只创建一个 TravelAPIClient 实例，
    共享缓存和连接资源，避免重复初始化。

    Returns:
        TravelAPIClient 单例实例
    """
    global _travel_api_client
    if _travel_api_client is None:
        _travel_api_client = TravelAPIClient()
    return _travel_api_client
