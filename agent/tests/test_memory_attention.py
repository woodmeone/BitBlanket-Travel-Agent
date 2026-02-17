"""
注意力窗口单元测试
"""

import pytest
from memory.attention import AttentionWindow


class TestAttentionWindow:
    """测试注意力窗口"""

    def test_initialization(self):
        """测试初始化"""
        window = AttentionWindow(window_size=5)
        assert window.window_size == 5
        assert window.weights["recency"] == 0.3
        assert window.weights["importance"] == 0.4
        assert window.weights["relevance"] == 0.3

    def test_compute_attention_empty(self):
        """测试空消息列表"""
        window = AttentionWindow()
        scores = window.compute_attention([], "query")
        assert scores == []

    def test_compute_attention_single(self):
        """测试单条消息"""
        window = AttentionWindow()
        messages = [{"content": "hello", "importance": 0.5}]
        scores = window.compute_attention(messages, "hello")
        assert len(scores) == 1
        assert abs(sum(scores) - 1.0) < 0.01  # 归一化和为 1

    def test_compute_attention_multiple(self):
        """测试多条消息"""
        window = AttentionWindow()
        messages = [
            {"content": "我想去海边旅游", "importance": 0.8},
            {"content": "今天天气不错", "importance": 0.3},
            {"content": "推荐一个行程", "importance": 0.9},
        ]
        scores = window.compute_attention(messages, "海边")
        assert len(scores) == 3
        assert abs(sum(scores) - 1.0) < 0.01

    def test_compute_relevance(self):
        """测试相关性计算"""
        window = AttentionWindow()
        # 关键词重叠
        score = window._compute_relevance("hello world", "world")
        assert score > 0
        # 无重叠
        score = window._compute_relevance("hello world", "python")
        assert score == 0

    def test_select_top_messages(self):
        """测试选择top消息"""
        window = AttentionWindow(window_size=2)
        messages = [
            {"content": "low priority", "importance": 0.1},
            {"content": "medium priority", "importance": 0.5},
            {"content": "high priority", "importance": 0.9},
        ]
        selected = window.select_top_messages(messages)
        assert len(selected) == 2
        # 验证高优先级的被选中
        assert any(m["content"] == "high priority" for m in selected)

    def test_tokenize(self):
        """测试分词"""
        window = AttentionWindow()
        tokens = window._tokenize("hello world test")
        assert "hello" in tokens
        assert "world" in tokens

    def test_get_stats(self):
        """测试统计信息"""
        window = AttentionWindow(window_size=10)
        stats = window.get_stats()
        assert stats["window_size"] == 10
        assert "weights" in stats
