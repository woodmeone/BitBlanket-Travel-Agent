"""
工具学习器

提供工具使用记录、用户偏好学习和智能推荐功能。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from collections import defaultdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ToolUsage:
    """工具使用记录"""
    tool_id: str
    timestamp: str
    success: bool
    context: Dict = field(default_factory=dict)
    duration: float = 0.0


@dataclass
class UserToolPreferences:
    """用户工具偏好"""
    user_id: str
    frequently_used: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    successful_tools: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    failed_tools: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    last_used: Dict[str, str] = field(default_factory=dict)


class ToolLearning:
    """工具学习器

    特性：
    - 记录工具使用情况
    - 学习用户偏好
    - 智能推荐工具
    """

    def __init__(self, redis_client=None):
        self._usage_history: List[ToolUsage] = []
        self._user_preferences: Dict[str, UserToolPreferences] = {}
        self._context_tools: Dict[str, List[str]] = defaultdict(list)
        self._redis = redis_client
        self._max_history = 10000
        logger.info("ToolLearning initialized")

    def record_usage(
        self,
        tool_id: str,
        success: bool,
        context: Optional[Dict] = None,
        duration: float = 0.0,
        user_id: Optional[str] = None
    ):
        """记录工具使用

        Args:
            tool_id: 工具ID
            success: 是否成功
            context: 使用上下文
            duration: 执行时长
            user_id: 用户ID
        """
        usage = ToolUsage(
            tool_id=tool_id,
            timestamp=datetime.now().isoformat(),
            success=success,
            context=context or {},
            duration=duration
        )

        self._usage_history.append(usage)

        # 限制历史长度
        if len(self._usage_history) > self._max_history:
            self._usage_history = self._usage_history[-self._max_history:]

        # 更新用户偏好
        if user_id:
            self._update_preferences(user_id, tool_id, success)

        # 更新上下文关联
        if context:
            self._update_context_association(tool_id, context)

    def recommend_tools(
        self,
        context: Optional[Dict] = None,
        user_id: Optional[str] = None,
        top_k: int = 3
    ) -> List[str]:
        """推荐工具

        Args:
            context: 当前上下文
            user_id: 用户ID
            top_k: 推荐数量

        Returns:
            推荐的工具ID列表
        """
        scores = defaultdict(float)

        # 基于用户的推荐
        if user_id and user_id in self._user_preferences:
            prefs = self._user_preferences[user_id]
            for tool_id, count in prefs.frequently_used.items():
                scores[tool_id] += count * 2.0

        # 基于上下文的推荐
        if context:
            query = context.get("query", "").lower()
            intent = context.get("intent", "")

            # 查询关键词关联
            for tool_id, related_queries in self._context_tools.items():
                for related in related_queries:
                    if related.lower() in query:
                        scores[tool_id] += 1.0

            # 意图关联
            if intent:
                for tool_id, related_intents in self._context_tools.items():
                    if intent in related_intents:
                        scores[tool_id] += 1.5

        # 基于历史的推荐
        recent_tools = [u.tool_id for u in self._usage_history[-10:]]
        for tool_id in recent_tools:
            scores[tool_id] += 0.5

        # 排序返回
        sorted_tools = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [t[0] for t in sorted_tools[:top_k]]

    def infer_preferences(self, user_id: str) -> UserToolPreferences:
        """推断用户偏好

        Args:
            user_id: 用户ID

        Returns:
            用户偏好
        """
        if user_id not in self._user_preferences:
            self._user_preferences[user_id] = UserToolPreferences(user_id=user_id)

        return self._user_preferences[user_id]

    def get_popular_tools(self, limit: int = 10) -> List[tuple]:
        """获取热门工具

        Returns:
            [(tool_id, usage_count), ...]
        """
        counts = defaultdict(int)
        for usage in self._usage_history:
            counts[usage.tool_id] += 1

        sorted_tools = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_tools[:limit]

    def get_success_rate(self, tool_id: str) -> float:
        """获取工具成功率

        Args:
            tool_id: 工具ID

        Returns:
            成功率 (0-1)
        """
        tool_usage = [u for u in self._usage_history if u.tool_id == tool_id]
        if not tool_usage:
            return 0.0

        success_count = sum(1 for u in tool_usage if u.success)
        return success_count / len(tool_usage)

    def get_usage_history(
        self,
        tool_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[ToolUsage]:
        """获取使用历史

        Args:
            tool_id: 工具ID过滤
            user_id: 用户ID过滤
            limit: 返回数量

        Returns:
            使用记录列表
        """
        results = self._usage_history

        if tool_id:
            results = [u for u in results if u.tool_id == tool_id]

        # 注意: user_id 存储在 context 中，这里简化处理
        if user_id:
            results = [u for u in results if u.context.get("user_id") == user_id]

        return results[-limit:]

    def clear_history(self):
        """清空使用历史"""
        self._usage_history.clear()
        logger.info("Tool usage history cleared")

    def _update_preferences(self, user_id: str, tool_id: str, success: bool):
        """更新用户偏好"""
        if user_id not in self._user_preferences:
            self._user_preferences[user_id] = UserToolPreferences(user_id=user_id)

        prefs = self._user_preferences[user_id]
        prefs.frequently_used[tool_id] += 1
        prefs.last_used[tool_id] = datetime.now().isoformat()

        if success:
            prefs.successful_tools[tool_id] += 1
        else:
            prefs.failed_tools[tool_id] += 1

    def _update_context_association(self, tool_id: str, context: Dict):
        """更新上下文关联"""
        query = context.get("query", "")
        intent = context.get("intent", "")

        if query:
            self._context_tools[tool_id].append(query)
            # 限制每个工具的上下文数量
            if len(self._context_tools[tool_id]) > 100:
                self._context_tools[tool_id] = self._context_tools[tool_id][-100:]

        if intent:
            key = f"intent:{intent}"
            if key not in self._context_tools[tool_id]:
                self._context_tools[tool_id].append(key)


# 全局单例
tool_learning = ToolLearning()
