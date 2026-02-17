"""
对话向量化单元测试
"""

import pytest
import asyncio
import numpy as np
from memory.vectorizer import ConversationVectorizer


class TestConversationVectorizer:
    """测试对话向量化器"""

    def test_initialization(self):
        """测试初始化"""
        vec = ConversationVectorizer()
        assert vec.embedding_dim == 1536
        assert vec.use_tfidf_fallback is True
        assert vec.llm_client is None

    def test_embed_text_empty(self):
        """测试空文本"""
        vec = ConversationVectorizer()
        result = asyncio.run(vec.embed_text(""))
        assert isinstance(result, np.ndarray)
        assert result.shape[0] == 1536

    def test_embed_text_simple(self):
        """测试简单文本嵌入"""
        vec = ConversationVectorizer()
        result = asyncio.run(vec.embed_text("我想去海边旅游"))
        assert isinstance(result, np.ndarray)
        assert result.shape[0] == 1536

    def test_simple_hash_embed(self):
        """测试简单哈希嵌入"""
        vec = ConversationVectorizer()
        result = vec._simple_hash_embed("旅游")
        assert isinstance(result, np.ndarray)
        assert result.shape[0] == 1536
        # 验证归一化
        norm = np.linalg.norm(result)
        assert norm > 0

    def test_serialize_preferences(self):
        """测试偏好序列化"""
        vec = ConversationVectorizer()
        prefs = {
            "budget": "5000",
            "duration": "3天",
            "cities": ["三亚", "厦门"]
        }
        result = vec._serialize_preferences(prefs)
        assert "budget" in result
        assert "5000" in result

    def test_serialize_preferences_empty(self):
        """测试空偏好"""
        vec = ConversationVectorizer()
        result = vec._serialize_preferences({})
        assert result == ""

    @pytest.mark.asyncio
    async def test_compute_similarity(self):
        """测试相似度计算"""
        vec = ConversationVectorizer()
        v1 = np.array([1.0, 0.0, 0.0])
        v2 = np.array([1.0, 0.0, 0.0])
        sim = await vec.compute_similarity(v1, v2)
        assert abs(sim - 1.0) < 0.01

    @pytest.mark.asyncio
    async def test_compute_similarity_orthogonal(self):
        """测试正交向量"""
        vec = ConversationVectorizer()
        v1 = np.array([1.0, 0.0, 0.0])
        v2 = np.array([0.0, 1.0, 0.0])
        sim = await vec.compute_similarity(v1, v2)
        assert abs(sim) < 0.01

    @pytest.mark.asyncio
    async def test_compute_similarity_zero_vector(self):
        """测试零向量"""
        vec = ConversationVectorizer()
        v1 = np.array([0.0, 0.0, 0.0])
        v2 = np.array([1.0, 0.0, 0.0])
        sim = await vec.compute_similarity(v1, v2)
        assert sim == 0.0

    def test_vectorize_session(self):
        """测试会话向量化"""
        vec = ConversationVectorizer()
        session_data = {
            "summary": "用户想去海边旅游",
            "key_facts": ["预算5000", "3天"],
            "user_preferences": {"budget": "5000"},
            "topics": ["海岛", "旅游"]
        }
        result = asyncio.run(vec.vectorize_session(session_data))
        assert isinstance(result, np.ndarray)
        assert result.shape[0] == 1536

    def test_vectorize_session_empty(self):
        """测试空会话"""
        vec = ConversationVectorizer()
        result = asyncio.run(vec.vectorize_session({}))
        assert isinstance(result, np.ndarray)
        assert result.shape[0] == 1536

    def test_get_stats(self):
        """测试统计信息"""
        vec = ConversationVectorizer()
        stats = vec.get_stats()
        assert stats["embedding_dim"] == 1536
        assert "llm_client" in stats
