"""
LLM 响应缓存

提供简单的 LLM 响应缓存功能，减少重复调用。
"""

from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


class LLMCache:
    """LLM 响应缓存

    简单的内存缓存，支持 TTL 过期。
    """

    def __init__(self, ttl_seconds: int = 300, max_size: int = 1000):
        """
        初始化缓存

        Args:
            ttl_seconds: 缓存过期时间（秒）
            max_size: 最大缓存条目数
        """
        self._cache: Dict[str, Dict] = {}
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    def _make_key(self, messages: list, temperature: float = 0.7) -> str:
        """生成缓存键

        Args:
            messages: 消息列表
            temperature: 温度参数

        Returns:
            缓存键
        """
        # 简单序列化
        content = json.dumps({
            "messages": messages,
            "temperature": temperature
        }, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()

    def get(self, messages: list, temperature: float = 0.7) -> Optional[Dict]:
        """获取缓存

        Args:
            messages: 消息列表
            temperature: 温度参数

        Returns:
            缓存的响应或 None
        """
        key = self._make_key(messages, temperature)

        if key in self._cache:
            entry = self._cache[key]
            # 检查是否过期
            age = (datetime.now() - entry["timestamp"]).total_seconds()
            if age < self._ttl:
                self._hits += 1
                logger.debug(f"Cache hit: {key[:8]}")
                return entry["response"]
            else:
                # 过期删除
                del self._cache[key]

        self._misses += 1
        return None

    def set(self, messages: list, response: Dict, temperature: float = 0.7):
        """设置缓存

        Args:
            messages: 消息列表
            response: LLM 响应
            temperature: 温度参数
        """
        # 清理过期条目
        self._cleanup()

        key = self._make_key(messages, temperature)
        self._cache[key] = {
            "response": response,
            "timestamp": datetime.now()
        }

    def _cleanup(self):
        """清理过期和多余的缓存"""
        now = datetime.now()

        # 删除过期条目
        expired_keys = []
        for key, entry in self._cache.items():
            age = (now - entry["timestamp"]).total_seconds()
            if age >= self._ttl:
                expired_keys.append(key)

        for key in expired_keys:
            del self._cache[key]

        # 如果还是太大，删除最老的
        while len(self._cache) >= self._max_size:
            oldest_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k]["timestamp"]
            )
            del self._cache[oldest_key]

    def get_stats(self) -> Dict:
        """获取缓存统计"""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0

        return {
            "size": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.2%}"
        }

    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._hits = 0
        self._misses = 0


# 全局缓存实例
llm_cache = LLMCache()
