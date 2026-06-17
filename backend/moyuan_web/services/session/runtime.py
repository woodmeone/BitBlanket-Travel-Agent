"""会话服务的延迟运行时工具和协议定义。

本模块定义会话服务所需的基础常量、协议和工厂函数，
采用延迟导入策略避免在轻量操作中触发 Agent 模块的重导入。

Protocol 说明：
    SessionMemoryManager 使用 Python 的 Protocol 定义记忆管理器的最小合约，
    实现类只需提供 delete_session 和 clear_session_messages 两个异步方法即可，
    无需显式继承。这种鸭子类型设计使测试替身（Mock）更容易创建。
"""

from __future__ import annotations

from typing import Any, Callable, Protocol

DEFAULT_SESSION_NAME = "新会话"  # 新建会话的默认名称
DEFAULT_MODEL_ID = "gpt-4o-mini"  # 默认模型 ID


class SessionMemoryManager(Protocol):
    """会话服务使用的最小记忆管理器合约（Protocol）。"""

    async def delete_session(self, session_id: str) -> Any:
        """删除与指定会话关联的所有记忆产物。"""

    async def clear_session_messages(self, session_id: str) -> Any:
        """清除轮次级对话记忆，保留会话档案状态。"""


MemoryManagerFactory = Callable[[], SessionMemoryManager]  # 记忆管理器工厂函数类型


def resolve_default_model_id(default_model_id: str = DEFAULT_MODEL_ID) -> str:
    """从运行时配置解析默认模型 ID，带回退保护。

    优先从配置管理器获取，获取失败时使用传入的默认值。
    """
    try:
        from ...config.runtime import get_model_config_manager

        return get_model_config_manager().get_default_model_id()
    except Exception:
        return default_model_id


def build_default_memory_manager() -> SessionMemoryManager:
    """延迟构建默认记忆管理器，避免过早导入 Agent 模块。

    Agent 模块导入较重（涉及 LangChain、模型加载等），
    通过工厂函数延迟到首次使用时才导入和创建。
    """
    from agent.travel_agent.graph.memory_integration import get_agent_memory_manager

    return get_agent_memory_manager(max_history=10, summary_threshold=20)
