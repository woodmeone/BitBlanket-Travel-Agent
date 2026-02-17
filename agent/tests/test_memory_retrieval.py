"""
上下文感知检索单元测试
"""

import pytest
from memory.retrieval import ContextAwareRetrieval, RetrievedMemory


class TestContextAwareRetrieval:
    """测试上下文感知检索"""

    def test_initialization(self):
        """测试初始化"""
        retrieval = ContextAwareRetrieval()
        assert retrieval.default_top_k == 3
        assert retrieval.hierarchical_store is None
        assert retrieval.profile_store is None
        assert retrieval.vectorizer is None

    def test_initialization_custom(self):
        """测试自定义初始化"""
        retrieval = ContextAwareRetrieval(default_top_k=5)
        assert retrieval.default_top_k == 5

    def test_expand_query_empty(self):
        """测试空查询扩展"""
        retrieval = ContextAwareRetrieval()
        result = retrieval._expand_query("test", None)
        assert result == "test"

    def test_cosine_similarity(self):
        """测试余弦相似度"""
        import numpy as np
        retrieval = ContextAwareRetrieval()
        v1 = [1.0, 0.0, 0.0]
        v2 = [1.0, 0.0, 0.0]
        sim = retrieval._cosine_similarity(v1, v2)
        assert abs(sim - 1.0) < 0.01

    def test_cosine_similarity_opposite(self):
        """测试相反向量"""
        import numpy as np
        retrieval = ContextAwareRetrieval()
        v1 = [1.0, 0.0, 0.0]
        v2 = [-1.0, 0.0, 0.0]
        sim = retrieval._cosine_similarity(v1, v2)
        assert abs(sim - (-1.0)) < 0.01

    def test_get_stats(self):
        """测试统计信息"""
        retrieval = ContextAwareRetrieval()
        stats = retrieval.get_stats()
        assert "hierarchical_store" in stats
        assert "profile_store" in stats
        assert "vectorizer" in stats
        assert stats["default_top_k"] == 3
        assert stats["rrf_k"] == 60


class TestRetrievedMemory:
    """测试检索到的记忆"""

    def test_initialization(self):
        """测试初始化"""
        mem = RetrievedMemory(
            session_id="sess_1",
            content="test content",
            relevance_score=0.8,
            source="semantic",
            metadata={"key": "value"}
        )
        assert mem.session_id == "sess_1"
        assert mem.content == "test content"
        assert mem.relevance_score == 0.8
        assert mem.source == "semantic"
        assert mem.metadata["key"] == "value"
