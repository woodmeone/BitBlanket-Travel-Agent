"""
智能淘汰策略单元测试
"""

import pytest
from datetime import datetime, timedelta
from memory.eviction_policy import SmartEvictionPolicy, AdaptiveEvictionPolicy, EvictionWeights


class TestSmartEvictionPolicy:
    """测试智能淘汰策略"""

    def test_initialization(self):
        """测试初始化"""
        policy = SmartEvictionPolicy()
        assert policy.max_size == 50
        assert policy.weights.importance == 0.4
        assert policy.weights.time_decay == 0.3
        assert policy.weights.access_frequency == 0.3

    def test_compute_priority(self):
        """测试优先级计算"""
        policy = SmartEvictionPolicy()
        msg = {
            "importance": 0.8,
            "timestamp": datetime.now().isoformat(),
            "access_count": 5
        }
        priority = policy.compute_priority(msg)
        assert 0 <= priority <= 1

    def test_compute_priority_no_timestamp(self):
        """测试无时间戳"""
        policy = SmartEvictionPolicy()
        msg = {"importance": 0.5}
        priority = policy.compute_priority(msg)
        assert 0 <= priority <= 1

    def test_compute_priority_old_message(self):
        """测试旧消息的时间衰减"""
        policy = SmartEvictionPolicy()
        old_time = (datetime.now() - timedelta(hours=48)).isoformat()
        msg = {
            "importance": 0.8,
            "timestamp": old_time,
            "access_count": 1
        }
        priority = policy.compute_priority(msg)
        # 旧消息优先级应该较低
        assert priority < 0.8

    def test_should_evict(self):
        """测试是否应该淘汰"""
        policy = SmartEvictionPolicy(max_size=10)
        assert policy.should_evict(9, 1) is False
        assert policy.should_evict(10, 1) is True
        assert policy.should_evict(5, 10) is True

    def test_get_eviction_candidates(self):
        """测试获取淘汰候选"""
        policy = SmartEvictionPolicy(max_size=10)
        messages = [
            {"importance": 0.1, "timestamp": "", "access_count": 1},
            {"importance": 0.9, "timestamp": "", "access_count": 1},
            {"importance": 0.3, "timestamp": "", "access_count": 1},
        ]
        candidates = policy.get_eviction_candidates(messages, count=1)
        assert len(candidates) == 1

    def test_sort_by_priority(self):
        """测试按优先级排序"""
        policy = SmartEvictionPolicy()
        messages = [
            {"importance": 0.1, "timestamp": "", "access_count": 1},
            {"importance": 0.9, "timestamp": "", "access_count": 1},
            {"importance": 0.5, "timestamp": "", "access_count": 1},
        ]
        sorted_msgs = policy.sort_by_priority(messages)
        # 降序排列，高优先级在前
        assert sorted_msgs[0]["importance"] == 0.9

    def test_get_stats(self):
        """测试统计信息"""
        policy = SmartEvictionPolicy(max_size=100)
        stats = policy.get_stats()
        assert stats["max_size"] == 100
        assert "weights" in stats


class TestAdaptiveEvictionPolicy:
    """测试自适应淘汰策略"""

    def test_initialization(self):
        """测试初始化"""
        policy = AdaptiveEvictionPolicy()
        assert isinstance(policy, SmartEvictionPolicy)
        assert len(policy._access_history) == 0

    def test_record_access(self):
        """测试记录访问"""
        policy = AdaptiveEvictionPolicy()
        policy.record_access(0.8)
        assert len(policy._access_history) == 1

    def test_adjust_weights(self):
        """测试权重调整"""
        policy = AdaptiveEvictionPolicy()
        # 添加足够的高优先级访问
        for _ in range(10):
            policy.record_access(0.8)
        policy.adjust_weights()
        # 权重应该被调整
        assert policy.weights.importance > 0
