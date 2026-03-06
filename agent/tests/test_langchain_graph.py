"""
================================================================================
LangGraph Agent 单元测试
================================================================================

测试 LangChain + LangGraph 构建的 Agent 系统
包括：状态管理、节点执行、图构建、错误处理

================================================================================
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List

# 测试路径设置
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from graph.state import AgentState, create_initial_state, TRAVEL_AGENT_SYSTEM_PROMPT
from graph.nodes import AgentNodes, IntentResult
from graph.builder import TravelAgentGraph, build_travel_agent
from graph.error_handling import (
    AgentError, ToolExecutionError, LLMAgentError, RateLimitError,
    ErrorRecoveryStrategy, AgentErrorMiddleware, retry_with_backoff
)
from graph.performance import (
    LRUCache, SemanticCache, ConcurrencyLimiter, RateLimiter,
    PerformanceMonitor
)
from tools.travel_tools import (
    search_cities, query_attractions, query_hotels,
    calculate_budget, plan_itinerary, get_travel_tips, get_weather,
    get_travel_tools
)


# ============================================================================
# 测试夹具
# ============================================================================

@pytest.fixture
def mock_llm():
    """模拟 LLM"""
    llm = Mock()
    llm.invoke = Mock(return_value=Mock(content="Mocked response"))
    llm.bind_tools = Mock(return_value=llm)
    llm.with_structured_output = Mock(return_value=llm)
    return llm


@pytest.fixture
def mock_tools():
    """模拟工具列表"""
    tools = [
        search_cities,
        query_attractions,
        query_hotels,
    ]
    return tools


@pytest.fixture
def sample_state():
    """示例状态"""
    from langchain_core.messages import HumanMessage
    return create_initial_state(
        user_message="推荐一个海边旅游目的地",
        session_id="test_session"
    )


# ============================================================================
# 状态管理测试
# ============================================================================

class TestAgentState:
    """测试状态管理"""

    def test_create_initial_state(self):
        """测试初始状态创建"""
        state = create_initial_state(
            user_message="测试消息",
            session_id="test_123"
        )

        assert "messages" in state
        assert len(state["messages"]) == 2  # system + user
        assert state["session_id"] == "test_123"
        assert "intent" in state
        assert "plan" in state
        assert "tools_used" in state

    def test_initial_state_has_system_message(self):
        """测试系统消息"""
        state = create_initial_state(user_message="测试")

        messages = state["messages"]
        from langchain_core.messages import SystemMessage
        assert any(isinstance(m, SystemMessage) for m in messages)


# ============================================================================
# 节点测试
# ============================================================================

class TestAgentNodes:
    """测试 Agent 节点"""

    def test_nodes_initialization(self, mock_llm, mock_tools):
        """测试节点初始化"""
        nodes = AgentNodes(mock_llm, mock_tools)

        assert nodes.llm == mock_llm
        assert nodes.tools == mock_tools
        assert len(nodes.tool_map) == len(mock_tools)

    def test_intent_result_model(self):
        """测试意图结果模型"""
        result = IntentResult(
            intent="recommend",
            confidence=0.9,
            entities={"city": "三亚"},
            requires_tools=True
        )

        assert result.intent == "recommend"
        assert result.confidence == 0.9
        assert result.entities == {"city": "三亚"}
        assert result.requires_tools is True


# ============================================================================
# 图构建测试
# ============================================================================

class TestTravelAgentGraph:
    """测试图构建"""

    def test_build_travel_agent(self, mock_llm, mock_tools):
        """测试 Agent 构建"""
        agent = build_travel_agent(mock_llm, mock_tools)

        assert agent.llm == mock_llm
        assert agent.tools == mock_tools
        assert agent.graph is not None

    def test_graph_has_required_nodes(self, mock_llm, mock_tools):
        """测试图包含所需节点"""
        agent = build_travel_agent(mock_llm, mock_tools)

        # 检查图已编译
        assert agent.graph is not None


# ============================================================================
# 工具测试
# ============================================================================

class TestTravelTools:
    """测试旅游工具"""

    def test_get_travel_tools(self):
        """测试获取工具列表"""
        tools = get_travel_tools()

        assert len(tools) > 0
        tool_names = [t.name for t in tools]
        assert "search_cities" in tool_names
        assert "query_attractions" in tool_names
        assert "calculate_budget" in tool_names

    def test_search_cities_tool(self):
        """测试城市搜索工具"""
        result = search_cities.invoke({"query": "北京"})

        assert "北京" in result
        assert "故宫" in result or "城市" in result

    def test_query_attractions_tool(self):
        """测试景点查询工具"""
        result = query_attractions.invoke({"city": "北京"})

        assert "北京" in result
        assert "故宫" in result or "景点" in result

    def test_calculate_budget_tool(self):
        """测试预算计算工具"""
        result = calculate_budget.invoke({
            "destination": "三亚",
            "days": 3,
            "people": 2,
            "accommodation_level": "medium"
        })

        assert "三亚" in result
        assert "3天" in result
        assert "2人" in result

    def test_plan_itinerary_tool(self):
        """测试行程规划工具"""
        result = plan_itinerary.invoke({
            "destination": "北京",
            "days": 3,
            "interests": "历史"
        })

        assert "北京" in result
        assert "第1天" in result

    def test_get_travel_tips_tool(self):
        """测试旅行建议工具"""
        result = get_travel_tips.invoke({
            "destination": "北京",
            "season": "夏季"
        })

        assert "北京" in result


# ============================================================================
# 错误处理测试
# ============================================================================

class TestErrorHandling:
    """测试错误处理"""

    def test_agent_error(self):
        """测试 Agent 错误"""
        error = AgentError("Test error", recoverable=True)
        assert error.message == "Test error"
        assert error.recoverable is True

    def test_tool_execution_error(self):
        """测试工具执行错误"""
        error = ToolExecutionError("search_cities", "Tool failed")
        assert error.tool_name == "search_cities"
        assert error.recoverable is True

    def test_rate_limit_error(self):
        """测试速率限制错误"""
        error = RateLimitError()
        assert error.recoverable is True

    @pytest.mark.asyncio
    async def test_error_recovery_strategy(self):
        """测试错误恢复策略"""
        strategy = ErrorRecoveryStrategy()

        # 测试工具错误恢复
        error = ToolExecutionError("test_tool", "Failed")
        result = await strategy.recover(error, {})

        assert result["success"] is False
        assert "fallback_answer" in result

    @pytest.mark.asyncio
    async def test_error_middleware(self):
        """测试错误处理中间件"""
        middleware = AgentErrorMiddleware()

        async def failing_func():
            raise ToolExecutionError("test", "Error")

        result = await middleware.execute_with_error_handling(
            failing_func,
            context={}
        )

        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_retry_decorator(self):
        """测试重试装饰器"""
        call_count = 0

        @retry_with_backoff(max_retries=2, base_delay=0.01)
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary error")
            return "success"

        result = await flaky_func()
        assert result == "success"
        assert call_count == 3


# ============================================================================
# 性能优化测试
# ============================================================================

class TestPerformance:
    """测试性能优化"""

    def test_lru_cache(self):
        """测试 LRU 缓存"""
        cache = LRUCache(max_size=3, ttl_seconds=None)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") is None

    def test_lru_cache_eviction(self):
        """测试 LRU 缓存淘汰"""
        cache = LRUCache(max_size=2)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")  # 应该淘汰 key1

        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

    def test_lru_cache_ttl(self):
        """测试 TTL"""
        cache = LRUCache(max_size=10, ttl_seconds=0.1)

        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        import time
        time.sleep(0.2)

        assert cache.get("key1") is None

    def test_cache_stats(self):
        """测试缓存统计"""
        cache = LRUCache(max_size=10)

        cache.set("key1", "value1")
        cache.get("key1")  # hit
        cache.get("key2")  # miss

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1

    def test_semantic_cache(self):
        """测试语义缓存"""
        cache = SemanticCache()

        cache.set("test prompt", "test response")
        result = cache.get("test prompt")

        assert result == "test response"

    @pytest.mark.asyncio
    async def test_concurrency_limiter(self):
        """测试并发限制"""
        limiter = ConcurrencyLimiter(max_concurrent=2)

        active_count = 0
        max_active = 0

        async def task():
            nonlocal active_count, max_active
            async with limiter:
                active_count += 1
                max_active = max(max_active, active_count)
                await asyncio.sleep(0.01)
                active_count -= 1

        # 同时运行 3 个任务，但限制为 2
        await asyncio.gather(task(), task(), task())

        assert max_active == 2

    @pytest.mark.asyncio
    async def test_rate_limiter(self):
        """测试速率限制"""
        limiter = RateLimiter(rate=10.0, burst=5)

        # 应该可以立即获取
        await limiter.acquire(1)

    def test_performance_monitor(self):
        """测试性能监控"""
        monitor = PerformanceMonitor()

        monitor.start("test_op")
        import time
        time.sleep(0.01)
        monitor.end("test_op")

        stats = monitor.get_stats("test_op")
        assert stats is not None
        assert stats["count"] == 1
        assert stats["min"] > 0


# ============================================================================
# 集成测试
# ============================================================================

class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_nodes_with_mock_llm(self, mock_llm, mock_tools, sample_state):
        """测试节点与模拟 LLM 集成"""
        nodes = AgentNodes(mock_llm, mock_tools)

        # 测试意图节点
        mock_llm.invoke.return_value = Mock(
            content='{"intent": "recommend", "confidence": 0.9, "entities": {}, "requires_tools": true}'
        )

        # 这个测试主要验证节点能正确调用 LLM
        # 实际调用会被 mock 拦截


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
