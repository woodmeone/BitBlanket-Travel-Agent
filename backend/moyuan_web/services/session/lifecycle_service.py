"""会话生命周期编排服务，协调 CRUD 操作和记忆副作用。"""

from __future__ import annotations

from typing import Any

from ...repositories.session_repository import SessionRepository
from .runtime import DEFAULT_SESSION_NAME, MemoryManagerFactory, SessionMemoryManager


class SessionLifecycleService:
    """协调会话 CRUD 操作和记忆副作用。

    每个操作在修改持久化数据后，同步更新记忆管理器，
    确保会话数据和记忆状态一致。
    """

    def __init__(
        self,
        repository: SessionRepository,
        *,
        memory_manager: SessionMemoryManager | None,
        memory_manager_factory: MemoryManagerFactory | None,
        default_model_id: str,
        default_session_name: str = DEFAULT_SESSION_NAME,
    ) -> None:
        """存储仓库和记忆协作者，用于会话生命周期操作。

        Args:
            repository: 会话持久化仓库
            memory_manager: 记忆管理器实例（可选，延迟创建）
            memory_manager_factory: 记忆管理器工厂函数（当 memory_manager 为 None 时使用）
            default_model_id: 默认模型 ID
            default_session_name: 默认会话名称
        """
        self._repository = repository
        self._memory_manager = memory_manager
        self._memory_manager_factory = memory_manager_factory
        self._default_model_id = default_model_id
        self._default_session_name = default_session_name

    async def create_session(self, name: str | None = None) -> dict[str, Any]:
        """创建新会话记录，含规范化显示名和默认模型。"""
        session_name = (name or self._default_session_name).strip() or self._default_session_name
        session_id = await self._repository.create(
            {
                "name": session_name,
                "model_id": self._default_model_id,
            }
        )
        return {"success": True, "session_id": session_id, "name": session_name}

    async def list_sessions(self, include_empty: bool = False) -> dict[str, Any]:
        """列出会话并包含总数，用于 API 响应载荷。"""
        sessions = await self._repository.list_all(include_empty=include_empty)
        return {"success": True, "sessions": sessions, "total": len(sessions)}

    async def delete_session(self, session_id: str) -> dict[str, Any]:
        """删除会话数据及关联的记忆快照。

        先删除持久化数据，再清理记忆管理器中的会话数据。
        记忆清理失败不影响删除结果（静默吞异常）。
        """
        deleted = await self._repository.delete(session_id)
        if deleted:
            try:
                await self._get_memory_manager().delete_session(session_id)
            except Exception:
                pass
            return {"success": True}
        return self._not_found()

    async def update_session_name(self, session_id: str, name: str) -> dict[str, Any]:
        """更新会话显示名，存在性校验后执行。"""
        session = await self._repository.get(session_id)
        if not session:
            return self._not_found()

        await self._repository.update(session_id, {"name": name})
        return {"success": True, "name": name}

    async def update_session_model(self, session_id: str, model_id: str) -> dict[str, Any]:
        """更新指定会话的模型绑定。"""
        session = await self._repository.get(session_id)
        if not session:
            return self._not_found()

        await self._repository.update(session_id, {"model_id": model_id})
        return {"success": True, "model_id": model_id}

    async def get_session_model(self, session_id: str) -> dict[str, Any]:
        """返回目标会话配置的活跃模型 ID。"""
        session = await self._repository.get(session_id)
        if not session:
            return self._not_found()

        return {"success": True, "model_id": session.get("model_id", self._default_model_id)}

    async def clear_chat(self, session_id: str) -> dict[str, Any]:
        """清除会话的持久化聊天消息和内存对话缓存。"""
        session = await self._repository.get(session_id)
        if not session:
            return self._not_found()

        await self._repository.update(session_id, {"messages": [], "message_count": 0})
        try:
            await self._get_memory_manager().clear_session_messages(session_id)
        except Exception:
            pass
        return {"success": True}

    async def get_session_info(self, session_id: str) -> dict[str, Any]:
        """根据会话 ID 返回完整会话元数据载荷。"""
        session = await self._repository.get(session_id)
        if not session:
            return self._not_found()

        return {"success": True, "session": session}

    @staticmethod
    def _not_found() -> dict[str, Any]:
        """构建会话操作共享的规范"未找到"载荷。"""
        return {"success": False, "error": "会话不存在"}

    def _get_memory_manager(self) -> SessionMemoryManager:
        """延迟解析记忆管理器，使轻量操作避免导入 Agent 模块。

        记忆管理器依赖 Agent 模块（较重的导入），延迟到首次使用时
        才创建，避免 list_sessions 等轻量操作触发不必要的导入。
        """
        if self._memory_manager is None:
            if self._memory_manager_factory is None:
                raise RuntimeError("Session memory manager is not configured")
            self._memory_manager = self._memory_manager_factory()
        return self._memory_manager
