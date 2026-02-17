"""
记忆回流单元测试
"""

import pytest
import asyncio
from memory.recirculation import MemoryRecirculation, RecirculationRule, MemoryContent


class TestMemoryRecirculation:
    """测试记忆回流"""

    def test_initialization(self):
        """测试初始化"""
        recir = MemoryRecirculation()
        assert recir.rule.threshold_trigger == 0.7
        assert recir.rule.frequency_trigger == 3

    def test_should_recirculate_threshold(self):
        """测试阈值触发"""
        recir = MemoryRecirculation()
        message = {"importance": 0.8, "content": "test"}
        assert recir.should_recirculate(message) is True

    def test_should_not_recirculate_low_importance(self):
        """测试低重要性不触发"""
        recir = MemoryRecirculation()
        message = {"importance": 0.3, "content": "test"}
        assert recir.should_recirculate(message) is False

    def test_extract_topic(self):
        """测试话题提取"""
        recir = MemoryRecirculation()
        # 目的地话题 - 包含"去"
        topic = recir._extract_topic("我想去北京旅游")
        assert topic == "目的地"

        # 预算话题
        topic = recir._extract_topic("预算5000元")
        assert topic == "预算"

        # 默认话题
        topic = recir._extract_topic("今天天气不错")
        assert topic == "general"

    def test_topic_tracking(self):
        """测试话题跟踪"""
        recir = MemoryRecirculation()
        # 确认话题计数存在
        assert "u1" not in recir._topic_frequency
        # 添加消息后应该创建话题跟踪（需要提供 session_history）
        message1 = {"content": "test", "user_id": "u1", "importance": 0.3}
        session_history = [{"content": "previous"}]
        recir.should_recirculate(message1, session_history)
        assert "u1" in recir._topic_frequency

    @pytest.mark.asyncio
    async def test_move_to_long_term_no_store(self):
        """测试无长期存储"""
        recir = MemoryRecirculation()
        message = {"content": "test", "importance": 0.5, "user_id": "u1"}
        result = await recir.move_to_long_term(message, "u1")
        # 没有长期存储，应该加入队列
        assert result is False
        assert recir.get_pending_count() == 1

    def test_extract_preferences(self):
        """测试偏好提取"""
        recir = MemoryRecirculation()
        session_data = {
            "summary": "用户预算5000元，计划3天行程",
            "user_preferences": {"budget": "5000"}
        }
        prefs = recir._extract_preferences(session_data)
        assert "budget" in prefs

    def test_get_stats(self):
        """测试统计信息"""
        recir = MemoryRecirculation()
        stats = recir.get_stats()
        assert "rule" in stats
        assert stats["rule"]["threshold_trigger"] == 0.7
        assert stats["pending_count"] == 0

    def test_clear_pending(self):
        """测试清除待处理队列"""
        recir = MemoryRecirculation()
        recir._pending_recirculation.append(
            MemoryContent("1", "test", 0.5)
        )
        recir.clear_pending()
        assert recir.get_pending_count() == 0


class TestRecirculationRule:
    """测试回流规则"""

    def test_default_values(self):
        """测试默认值"""
        rule = RecirculationRule()
        assert rule.threshold_trigger == 0.7
        assert rule.frequency_trigger == 3
        assert rule.time_trigger is True
        assert rule.manual_trigger is True

    def test_custom_values(self):
        """测试自定义值"""
        rule = RecirculationRule(
            threshold_trigger=0.8,
            frequency_trigger=5,
            time_trigger=False
        )
        assert rule.threshold_trigger == 0.8
        assert rule.frequency_trigger == 5
        assert rule.time_trigger is False
