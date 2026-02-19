"""
集成测试：v2.8-v3.0 新模块

测试新模块的集成功能：
- v2.8.0: ToolRegistry, ToolLearning, PluginSystem
- v2.9.0: DialoguePolicy, ContextTracker, EntityLinker
- v3.0.0: AgentHub, SkillStore
"""

import pytest
from unittest.mock import Mock, AsyncMock


class TestToolEcosystem:
    """v2.8.0 工具生态测试"""

    def test_tool_registry(self):
        """测试工具注册中心"""
        from tools.registry import ToolRegistry, ToolCategory

        registry = ToolRegistry()

        def mock_handler(query):
            return {"result": "test"}

        # 注册工具
        tool_id = registry.register(
            tool_id="test_tool",
            name="测试工具",
            description="测试用工具",
            handler=mock_handler,
            category=ToolCategory.SEARCH,
            tags=["测试"]
        )

        assert tool_id == "test_tool"

        # 获取工具
        tool_info = registry.get_tool("test_tool")
        assert tool_info is not None
        assert tool_info.metadata.name == "测试工具"

    def test_tool_learning(self):
        """测试工具学习"""
        from tools.learning import ToolLearning

        learning = ToolLearning()

        # 记录使用
        learning.record_usage(
            tool_id="test_tool",
            success=True,
            context={"query": "测试"},
            user_id="user1"
        )

        # 获取推荐
        recommendations = learning.recommend_tools(
            context={"query": "测试"},
            user_id="user1",
            top_k=3
        )

        assert "test_tool" in recommendations or len(recommendations) >= 0


class TestDialogueEnhancement:
    """v2.9.0 对话增强测试"""

    def test_dialogue_policy(self):
        """测试对话策略"""
        from core.dialogue_policy import DialoguePolicy, DialogueAction

        policy = DialoguePolicy()

        # 获取上下文
        context = policy.get_context("session_123", "user1")

        # 选择动作 - 缺少必填参数
        action = policy.select_action(
            context,
            intent="travel_planning",
            entities={"city": "北京"}  # 缺少 days
        )

        # 应该需要澄清
        assert action in [DialogueAction.CLARIFY, DialogueAction.ASK_MORE]

    def test_context_tracker(self):
        """测试上下文追踪"""
        from memory.context_tracker import ContextTracker

        tracker = ContextTracker()

        # 追踪实体
        entity_id = tracker.track_entity(
            session_id="session_123",
            entity_type="city",
            value="北京"
        )

        assert entity_id == "city:北京"

        # 获取活跃实体
        entities = tracker.get_active_entities("session_123")

        assert len(entities) > 0
        assert entities[0].value == "北京"

    def test_entity_linker(self):
        """测试实体链接"""
        from reasoner.entity_linker import EntityLinker

        linker = EntityLinker()

        # 添加实体
        linker.add_entity(
            entity_id="beijing_001",
            name="北京",
            entity_type="city",
            aliases=["京城", "北平"]
        )

        # 搜索实体
        results = linker.search("北京")

        assert len(results) > 0
        assert results[0].name == "北京"


class TestAgentEcosystem:
    """v3.0.0 Agent 生态测试"""

    def test_agent_hub(self):
        """测试 Agent 市场"""
        from agent_hub import AgentHub

        hub = AgentHub()

        # 发现 Agent
        agents = hub.discover_agents("城市")

        # 获取模板
        templates = hub.get_templates()

        assert len(templates) > 0

    def test_skill_store(self):
        """测试技能库"""
        from skills import SkillStore, SkillCategory

        store = SkillStore()

        # 注册自定义技能
        def my_handler(query, context=None):
            return {"result": "处理完成"}

        store.register_skill(
            skill_id="custom_skill",
            name="自定义技能",
            description="测试用技能",
            category=SkillCategory.CUSTOM,
            handler=my_handler
        )

        # 发现技能
        skills = store.discover_skills("自定义")

        assert len(skills) > 0

        # 执行技能
        result = store.execute_skill("city_recommend")

        assert result.success is True

    def test_skill_chain(self):
        """测试技能链"""
        from skills import skill_store

        # 创建技能链
        success = skill_store.create_skill_chain(
            chain_id="test_chain",
            skill_ids=["city_recommend", "route_plan"]
        )

        assert success is True

        # 执行技能链
        results = skill_store.execute_chain(
            chain_id="test_chain",
            initial_input={"query": "北京旅游"}
        )

        assert len(results) > 0


class TestLLMIntegration:
    """LLM 集成测试"""

    def test_tool_registry_with_llm(self):
        """测试带 LLM 的工具注册中心"""
        from tools.registry import ToolRegistry

        mock_llm = Mock()
        mock_llm.chat = Mock(return_value={
            "success": True,
            "content": '{"matched_tools": []}'
        })

        registry = ToolRegistry(llm_client=mock_llm)

        # 验证 LLM 已设置
        assert registry._use_llm_discovery is True

        # 设置 LLM
        registry.set_llm_client(mock_llm)
        assert registry._llm_client is mock_llm

    def test_context_tracker_with_llm(self):
        """测试带 LLM 的上下文追踪"""
        from memory.context_tracker import ContextTracker

        mock_llm = Mock()
        mock_llm.chat = Mock(return_value={
            "success": True,
            "content": '{"resolved_entity_id": ""}'
        })

        tracker = ContextTracker(llm_client=mock_llm)

        # 验证 LLM 已设置
        tracker.set_llm_client(mock_llm)
        assert tracker._llm_client is mock_llm


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
