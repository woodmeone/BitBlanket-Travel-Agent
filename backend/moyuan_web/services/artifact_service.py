"""旅行计划产物检索服务，从会话消息历史中解析持久化的产物。

产物（Artifact）说明：
    旅行计划产物是 Agent 执行后生成的完整旅行计划数据结构，
    包含行程安排、酒店信息、景点推荐等。产物存储在助手消息的
    diagnostics 字段中，本服务负责从消息历史中检索和提取。

应用场景：
    - 用户查看最新的旅行计划：get_latest_artifact
    - 用户浏览历史计划版本：get_artifact_history
"""

from __future__ import annotations

from typing import Any

from ..api.schemas import normalize_trip_plan_artifact
from ..repositories.session_repository import SessionRepository


class ArtifactService:
    """从会话消息历史中检索持久化的旅行计划产物。"""

    def __init__(self, repository: SessionRepository) -> None:
        """存储用于查找会话产物的仓库。

        Args:
            repository: 会话持久化仓库
        """
        self._repository = repository

    @staticmethod
    def _artifact_entry_from_message(message: dict[str, Any], message_index: int) -> dict[str, Any] | None:
        """从会话消息中提取规范化的产物历史条目（当产物存在时）。

        只有助手消息的 diagnostics 字段中包含 artifact 时才返回条目，
        否则返回 None。

        Args:
            message: 会话消息字典
            message_index: 消息在列表中的索引位置

        Returns:
            规范化的产物条目字典，或 None
        """
        diagnostics = message.get("diagnostics")
        if not isinstance(diagnostics, dict):
            return None

        artifact = diagnostics.get("artifact")
        if not isinstance(artifact, dict) or not artifact:
            return None

        return {
            "artifact": normalize_trip_plan_artifact(artifact),
            "run_id": diagnostics.get("runId") or diagnostics.get("run_id"),
            "message_timestamp": message.get("timestamp"),
            "message_index": message_index,
        }

    async def get_latest_artifact(self, session_id: str) -> dict[str, Any]:
        """返回指定会话中最新的规范化产物。

        从消息列表末尾向前搜索，找到第一个包含产物的助手消息即返回。

        应用场景：用户打开会话时，前端请求最新旅行计划用于渲染。
        """
        session = await self._repository.get(session_id)
        if not session:
            return {"success": False, "error": "SESSION_NOT_FOUND"}

        messages = session.get("messages", [])
        for reverse_index, message in enumerate(reversed(messages)):
            if not isinstance(message, dict):
                continue
            message_index = len(messages) - reverse_index - 1
            entry = self._artifact_entry_from_message(message, message_index)
            if entry:
                return {
                    "success": True,
                    "session_id": session_id,
                    "artifact_found": True,
                    **entry,
                }

        return {
            "success": True,
            "session_id": session_id,
            "artifact_found": False,
            "artifact": None,
            "run_id": None,
            "message_timestamp": None,
            "message_index": None,
        }

    async def get_artifact_history(self, session_id: str, *, limit: int = 10) -> dict[str, Any]:
        """返回指定会话中最新的规范化产物快照列表。

        从消息列表末尾向前搜索，收集所有包含产物的消息，
        最多返回 limit 条。

        应用场景：用户查看历史旅行计划版本列表。
        """
        session = await self._repository.get(session_id)
        if not session:
            return {"success": False, "error": "SESSION_NOT_FOUND"}

        messages = session.get("messages", [])
        entries: list[dict[str, Any]] = []

        for reverse_index, message in enumerate(reversed(messages)):
            if not isinstance(message, dict):
                continue
            message_index = len(messages) - reverse_index - 1
            entry = self._artifact_entry_from_message(message, message_index)
            if not entry:
                continue
            entries.append(entry)
            if len(entries) >= max(limit, 1):
                break

        return {
            "success": True,
            "session_id": session_id,
            "count": len(entries),
            "entries": entries,
        }
