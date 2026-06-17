"""聊天历史持久化 Mixin，负责会话管理、消息存储和记忆同步。

本模块提供聊天服务的持久化能力，包括：
- 会话的创建和查找
- 用户/助手消息的持久化存储
- 对话历史的构建（用于 LLM 上下文注入）
- 记忆管理器的读写同步

记忆管理器说明：
    记忆管理器维护长期对话上下文，支持摘要压缩和查询相关记忆检索。
    与简单的历史消息列表不同，记忆管理器会在对话过长时自动生成摘要，
    并根据当前查询检索最相关的历史片段，减少 token 消耗。
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ChatHistoryMixin:
    """聊天持久化方法 Mixin，提供会话和消息历史管理能力。

    被 ChatService 通过多继承混入，负责所有与持久化相关的方法。
    """

    def _build_memory_context_messages(self, session_id: str) -> list[Any]:
        """构建基线记忆上下文消息，用于图（Graph）调用时的上下文注入。

        返回该会话的所有记忆上下文消息，不针对特定查询做筛选。
        """
        if self._memory_manager is None:
            return []
        try:
            return self._memory_manager.build_context_messages(session_id)
        except Exception as exc:
            logger.warning("Failed to build memory context messages: %s", exc)
            return []

    def _build_relevant_memory_context_messages(self, session_id: str, user_message: str) -> list[Any]:
        """构建查询相关的记忆上下文消息，减少 token 占用。

        与 _build_memory_context_messages 不同，此方法根据用户当前查询
        检索最相关的历史片段（最多8条），避免注入过多无关上下文。

        应用场景：用户问"上次推荐的酒店还有房吗"，只检索与酒店相关的历史，
        而不是加载全部对话记录。
        """
        if self._memory_manager is None:
            return []
        try:
            return self._memory_manager.build_context_messages_for_query(session_id, user_message, max_messages=8)
        except Exception as exc:
            logger.warning("Failed to build relevant memory context messages: %s", exc)
            return []

    async def _build_history_messages(
        self,
        session_id: str,
        limit: int = 12,
        exclude_last_user_message: Optional[str] = None,
    ) -> list[Any]:
        """将持久化的会话聊天历史转换为模型消息对象列表。

        Args:
            session_id: 会话 ID
            limit: 最多加载的历史消息条数，默认12条
            exclude_last_user_message: 若指定，则排除与该内容匹配的最后一条用户消息
                （避免在 direct 模式下重复注入当前用户消息）

        Returns:
            LangChain 消息对象列表（HumanMessage / AIMessage）
        """
        from langchain_core.messages import AIMessage, HumanMessage

        session = await self._repository.get(session_id)
        if not session:
            return []

        history = session.get("messages", [])
        if exclude_last_user_message and history:
            last = history[-1]
            if last.get("role") == "user" and last.get("content") == exclude_last_user_message:
                history = history[:-1]
        history = history[-limit:]  # 只取最近 limit 条消息，控制上下文长度
        result: list[Any] = []
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if not content:
                continue
            if role == "assistant":
                result.append(AIMessage(content=content))  # 助手消息
            else:
                result.append(HumanMessage(content=content))  # 用户消息
        return result

    async def _ensure_session(self, session_id: Optional[str]) -> str:
        """【核心】解析或创建会话标识符，确保写入聊天数据前会话已存在。

        逻辑：
        1. 如果传入了 session_id 且对应会话存在，直接返回
        2. 如果传入了 session_id 但会话不存在，用该 ID 创建新会话
        3. 如果未传入 session_id，生成新的 UUID 作为会话 ID

        应用场景：用户首次聊天时无 session_id，自动创建新会话；
        后续请求携带 session_id，复用已有会话。
        """
        normalized_session_id = session_id.strip() if session_id else None

        if normalized_session_id:
            session = await self._repository.get(normalized_session_id)
            if session:
                return normalized_session_id
            sid = normalized_session_id
        else:
            sid = str(uuid.uuid4())

        await self._repository.create(
            {
                "session_id": sid,
                "name": "新会话",
                "model_id": self._llm_adapter.config.get("model", "MiniMax-M2.5") if self._llm_adapter else "MiniMax-M2.5",
                "messages": [],
                "user_preferences": {},
            }
        )
        return sid

    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        reasoning: Optional[str] = None,
        diagnostics: Optional[dict[str, Any]] = None,
        model_content: Optional[str] = None,
    ) -> dict[str, Any]:
        """【核心】持久化一条聊天消息到仓库，并可选同步记忆档案。

        Args:
            session_id: 会话 ID
            role: 消息角色（"user" / "assistant"）
            content: 消息展示内容
            reasoning: 推理过程文本（仅助手消息）
            diagnostics: 诊断信息（仅助手消息，含工具使用、产物等）
            model_content: 模型专用内容（与展示内容可能不同，如含原始指令）

        Returns:
            {"success": True} 或 {"success": False, "error": "..."}
        """
        session = await self._repository.get(session_id)
        if not session:
            return {"success": False, "error": "SESSION_NOT_FOUND"}

        messages = session.get("messages", [])
        entry: dict[str, Any] = {
            "role": role,
            "content": content,
            "reasoning": reasoning,
            "timestamp": self._get_timestamp(),
        }
        if diagnostics:
            entry["diagnostics"] = diagnostics
        if model_content:
            entry["model_content"] = model_content
        messages.append(entry)

        await self._repository.update(
            session_id,
            {
                "messages": messages,
                "message_count": len(messages),
            },
        )
        return {"success": True}

    async def _save_user_message(
        self,
        session_id: str,
        content: str,
        *,
        model_content: Optional[str] = None,
    ) -> dict[str, Any]:
        """保存用户消息，兼容旧版测试替身（不支持 model_content 参数的情况）。"""
        try:
            return await self.save_message(
                session_id,
                "user",
                content,
                model_content=model_content,
            )
        except TypeError as exc:
            if "unexpected keyword argument 'model_content'" not in str(exc):
                raise
            return await self.save_message(session_id, "user", content)

    async def get_messages(self, session_id: str) -> dict[str, Any]:
        """返回会话的公共消息列表，排除仅用于模型的字段（如 model_content）。

        只返回 role/content/reasoning/timestamp/diagnostics 五个公共字段，
        防止内部字段（如 model_content）泄露到前端。
        """
        session = await self._repository.get(session_id)
        if not session:
            return {"success": False, "error": "SESSION_NOT_FOUND", "messages": []}

        public_messages: list[dict[str, Any]] = []
        for message in session.get("messages", []):
            if not isinstance(message, dict):
                continue
            public_messages.append(
                {
                    key: value
                    for key, value in message.items()
                    if key in {"role", "content", "reasoning", "timestamp", "diagnostics"}
                }
            )

        return {"success": True, "messages": public_messages}

    async def cleanup_expired_sessions(self, max_age_seconds: int = 86400) -> int:
        """清理过期会话和陈旧数据，默认清理超过24小时的会话。"""
        return await self._repository.cleanup_expired(max_age_seconds)

    @staticmethod
    def _get_timestamp() -> str:
        """返回当前时间戳字符串，用于持久化消息记录。格式：HH:MM:SS"""
        return datetime.now().strftime("%H:%M:%S")

    async def _write_memory_user(self, session_id: str, message: str) -> bool:
        """将用户消息写入记忆管理器，吞除非致命记忆错误。

        记忆写入失败不影响主流程，仅记录警告日志。
        """
        if self._memory_manager is None:
            return False
        try:
            await self._memory_manager.add_message(session_id, "user", message)
            return True
        except Exception as exc:
            logger.warning("Failed to write user memory: %s", exc)
            return False

    async def _write_memory_assistant(self, session_id: str, message: str) -> bool:
        """将助手回答写入记忆管理器，吞并非致命记忆错误。

        记忆写入失败不影响主流程，仅记录警告日志。
        """
        if self._memory_manager is None:
            return False
        try:
            await self._memory_manager.add_message(session_id, "assistant", message)
            return True
        except Exception as exc:
            logger.warning("Failed to write assistant memory: %s", exc)
            return False
