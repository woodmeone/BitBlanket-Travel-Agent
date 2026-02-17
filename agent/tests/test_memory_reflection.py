"""
反思机制单元测试
"""

import pytest
import asyncio
from memory.reflection import ReflectionMechanism, ReflectionResult


class TestReflectionMechanism:
    """测试反思机制"""

    def test_initialization(self):
        """测试初始化"""
        reflector = ReflectionMechanism(trigger_interval=10)
        assert reflector.trigger_interval == 10
        assert reflector.min_messages == 5

    def test_should_reflect(self):
        """测试是否应该触发反思"""
        reflector = ReflectionMechanism(trigger_interval=10)
        assert reflector.should_reflect(10) is True
        assert reflector.should_reflect(15) is False
        assert reflector.should_reflect(20) is True

    def test_rule_based_reflect(self):
        """测试基于规则的反思"""
        reflector = ReflectionMechanism()
        conversation = [
            {"role": "user", "content": "我想去海边旅游"},
            {"role": "assistant", "content": "好的，推荐你去三亚"},
            {"role": "user", "content": "预算5000元"},
        ]
        result = reflector._rule_based_reflect(conversation)
        assert isinstance(result, ReflectionResult)
        assert result.timestamp != ""

    def test_rule_based_reflect_empty(self):
        """测试空对话"""
        reflector = ReflectionMechanism()
        result = reflector._rule_based_reflect([])
        assert isinstance(result, ReflectionResult)
        assert result.key_insights == []

    def test_extract_keywords(self):
        """测试关键词提取"""
        reflector = ReflectionMechanism()
        keywords = reflector._extract_keywords("我想去海边旅游")
        assert isinstance(keywords, list)

    def test_reflect_insufficient_messages(self):
        """测试消息不足时的反思"""
        reflector = ReflectionMechanism(min_messages=5)
        conversation = [
            {"role": "user", "content": "你好"},
        ]
        result = asyncio.run(reflector.reflect(conversation))
        assert isinstance(result, ReflectionResult)

    def test_clear_cache(self):
        """测试清除缓存"""
        reflector = ReflectionMechanism()
        reflector._reflection_cache["test"] = ReflectionResult(
            key_insights=["test"]
        )
        reflector.clear_cache("test")
        assert "test" not in reflector._reflection_cache
        reflector.clear_cache()
        assert len(reflector._reflection_cache) == 0

    def test_get_stats(self):
        """测试统计信息"""
        reflector = ReflectionMechanism(trigger_interval=15)
        stats = reflector.get_stats()
        assert stats["trigger_interval"] == 15
        assert "cache_size" in stats


class TestReflectionResult:
    """测试反思结果"""

    def test_to_dict(self):
        """测试转换为字典"""
        result = ReflectionResult(
            key_insights=["insight1"],
            user_intents=["intent1"],
            knowledge_gaps=["gap1"],
            successful_actions=["action1"],
            user_preferences={"budget": "5000"}
        )
        data = result.to_dict()
        assert data["key_insights"] == ["insight1"]
        assert data["user_intents"] == ["intent1"]
        assert data["user_preferences"]["budget"] == "5000"
