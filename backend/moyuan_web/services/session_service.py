"""会话服务兼容性门面（Facade），委托给更小的协作者处理。

门面模式说明：
    SessionService 作为对外的统一 API 入口，内部将实际操作委托给
    SessionLifecycleService 处理。这种设计保持了对外接口的稳定性，
    同时允许内部实现自由重构。

    好处：
    1. 调用方只需依赖 SessionService，无需了解内部协作者
    2. 内部协作者可独立演进和测试
    3. 门面可以添加横切逻辑（如日志、缓存）而不影响协作者
"""

from __future__ import annotations

from ..repositories.session_repository import SessionRepository
from .session import (
    DEFAULT_MODEL_ID,
    DEFAULT_SESSION_NAME,
    SessionLifecycleService,
    build_default_memory_manager,
    resolve_default_model_id,
)


class SessionService:
    """会话服务门面，暴露现有 API 同时委托给更小的协作者。"""

    DEFAULT_SESSION_NAME = DEFAULT_SESSION_NAME
    DEFAULT_MODEL_ID = DEFAULT_MODEL_ID

    def __init__(self, repository: SessionRepository, memory_manager: object | None = None):
        """创建门面，包含生命周期协调器和延迟记忆绑定。

        Args:
            repository: 会话持久化仓库
            memory_manager: 可选的记忆管理器实例，未提供时延迟创建
        """
        self._repository = repository
        self._default_model_id = self._resolve_default_model_id()
        self._memory_manager = memory_manager
        self._lifecycle = SessionLifecycleService(  # 委托给生命周期服务处理实际操作
            repository,
            memory_manager=self._memory_manager,
            memory_manager_factory=build_default_memory_manager if memory_manager is None else None,  # 延迟创建记忆管理器
            default_model_id=self._default_model_id,
            default_session_name=self.DEFAULT_SESSION_NAME,
        )

    @classmethod
    def _resolve_default_model_id(cls) -> str:
        """从配置管理器解析默认模型 ID，带回退常量。"""
        return resolve_default_model_id(default_model_id=cls.DEFAULT_MODEL_ID)

    async def create_session(self, name: str | None = None) -> dict[str, object]:
        """创建新会话记录，含规范化显示名和默认模型。"""
        return await self._lifecycle.create_session(name=name)

    async def list_sessions(self, include_empty: bool = False) -> dict[str, object]:
        """列出会话并包含总数，用于 API 响应载荷。"""
        return await self._lifecycle.list_sessions(include_empty=include_empty)

    async def delete_session(self, session_id: str) -> dict[str, object]:
        """删除会话数据及关联的记忆快照。"""
        return await self._lifecycle.delete_session(session_id)

    async def update_session_name(self, session_id: str, name: str) -> dict[str, object]:
        """更新会话显示名，存在性校验后执行。"""
        return await self._lifecycle.update_session_name(session_id, name)

    async def update_session_model(self, session_id: str, model_id: str) -> dict[str, object]:
        """更新指定会话的模型绑定。"""
        return await self._lifecycle.update_session_model(session_id, model_id)

    async def get_session_model(self, session_id: str) -> dict[str, object]:
        """返回目标会话配置的活跃模型 ID。"""
        return await self._lifecycle.get_session_model(session_id)

    async def clear_chat(self, session_id: str) -> dict[str, object]:
        """清除会话的持久化聊天消息和内存对话缓存。"""
        return await self._lifecycle.clear_chat(session_id)

    async def get_session_info(self, session_id: str) -> dict[str, object]:
        """根据会话 ID 返回完整会话元数据载荷。"""
        return await self._lifecycle.get_session_info(session_id)
