"""Memory integration for LangGraph travel agent.

This module provides:
- Session-scoped memory manager with async APIs
- Lightweight conversation summarizer
- AgentStateWithMemory helper for building initial graph state with memory context
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage


@dataclass
class MemoryMessage:
    role: str
    content: str
    timestamp: str


class ConversationSummarizer:
    """Compact summarizer for long dialogue context.

    The implementation is deterministic and does not rely on an LLM call,
    so it is safe in sync/async paths and resilient in offline runs.
    """

    def __init__(self, llm: Any = None, summary_threshold: int = 20):
        self.llm = llm
        self.summary_threshold = max(2, summary_threshold)

    def summarize(self, messages: List[MemoryMessage]) -> str:
        if not messages:
            return ""

        if len(messages) <= self.summary_threshold:
            return ""

        cutoff = max(2, len(messages) - self.summary_threshold)
        head = messages[:cutoff]

        user_points: List[str] = []
        assistant_points: List[str] = []

        for msg in head:
            text = (msg.content or "").strip().replace("\n", " ")
            if not text:
                continue
            short = text[:80] + ("..." if len(text) > 80 else "")
            if msg.role == "user":
                user_points.append(short)
            elif msg.role == "assistant":
                assistant_points.append(short)

        bullets: List[str] = []
        if user_points:
            bullets.append("用户关键信息: " + " | ".join(user_points[-4:]))
        if assistant_points:
            bullets.append("助手已给建议: " + " | ".join(assistant_points[-4:]))

        return "\n".join(bullets).strip()


class AgentMemoryManager:
    """Session memory manager used by LangGraph integration."""

    def __init__(
        self,
        llm: Any = None,
        max_history: int = 10,
        summary_threshold: int = 20,
        persist_path: Optional[str] = None,
    ):
        self.max_history = max(2, max_history)
        self.summarizer = ConversationSummarizer(llm=llm, summary_threshold=summary_threshold)

        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

        self._persist_path = persist_path
        if self._persist_path:
            self._load_from_disk()

    async def add_message(self, session_id: str, role: str, content: str) -> None:
        with self._lock:
            session = self._sessions.setdefault(session_id, {"messages": [], "summary": ""})
            session["messages"].append(
                MemoryMessage(
                    role=role,
                    content=content,
                    timestamp=datetime.now().isoformat(),
                )
            )
            session["summary"] = self.summarizer.summarize(session["messages"])
            self._trim_messages(session)

            if self._persist_path:
                self._save_to_disk()

    async def get_recent_messages(self, session_id: str, limit: Optional[int] = None) -> List[MemoryMessage]:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return []
            cap = limit or self.max_history
            return list(session["messages"][-cap:])

    async def get_summary(self, session_id: str) -> str:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return ""
            return session.get("summary", "")

    def get_recent_messages_sync(self, session_id: str, limit: Optional[int] = None) -> List[MemoryMessage]:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return []
            cap = limit or self.max_history
            return list(session["messages"][-cap:])

    def get_summary_sync(self, session_id: str) -> str:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return ""
            return session.get("summary", "")

    def build_context_messages(self, session_id: str) -> List[BaseMessage]:
        summary = self.get_summary_sync(session_id)
        recent = self.get_recent_messages_sync(session_id, self.max_history)

        context: List[BaseMessage] = []
        if summary:
            context.append(SystemMessage(content=f"会话摘要:\n{summary}"))

        for msg in recent:
            if msg.role == "assistant":
                context.append(AIMessage(content=msg.content))
            else:
                context.append(HumanMessage(content=msg.content))

        return context

    def _trim_messages(self, session: Dict[str, Any]) -> None:
        keep = max(self.max_history * 3, self.max_history + 6)
        if len(session["messages"]) > keep:
            session["messages"] = session["messages"][-keep:]

    def _load_from_disk(self) -> None:
        if not self._persist_path or not os.path.exists(self._persist_path):
            return

        try:
            with open(self._persist_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception:
            return

        for session_id, session in raw.items():
            msgs = [
                MemoryMessage(
                    role=item.get("role", "user"),
                    content=item.get("content", ""),
                    timestamp=item.get("timestamp", datetime.now().isoformat()),
                )
                for item in session.get("messages", [])
            ]
            self._sessions[session_id] = {
                "messages": msgs,
                "summary": session.get("summary", ""),
            }

    def _save_to_disk(self) -> None:
        if not self._persist_path:
            return

        os.makedirs(os.path.dirname(self._persist_path), exist_ok=True)

        serializable: Dict[str, Any] = {}
        for session_id, session in self._sessions.items():
            serializable[session_id] = {
                "summary": session.get("summary", ""),
                "messages": [
                    {
                        "role": m.role,
                        "content": m.content,
                        "timestamp": m.timestamp,
                    }
                    for m in session.get("messages", [])
                ],
            }

        try:
            with open(self._persist_path, "w", encoding="utf-8") as f:
                json.dump(serializable, f, ensure_ascii=False, indent=2)
        except Exception:
            # Memory persistence is best-effort only.
            pass


class AgentStateWithMemory:
    """Factory helper to build initial agent state with conversation memory."""

    @staticmethod
    def create(
        user_message: str,
        session_id: str,
        memory_manager: AgentMemoryManager,
        system_prompt: str,
    ) -> Dict[str, Any]:
        messages: List[BaseMessage] = [SystemMessage(content=system_prompt)]

        if memory_manager is not None:
            messages.extend(memory_manager.build_context_messages(session_id))

        messages.append(HumanMessage(content=user_message))

        return {
            "messages": messages,
            "intent": None,
            "intent_detail": None,
            "plan": None,
            "current_step": 0,
            "tools_used": [],
            "tool_results": {},
            "answer": None,
            "reasoning": None,
            "session_id": session_id,
            "error": None,
        }


_DEFAULT_MANAGER: Optional[AgentMemoryManager] = None
_DEFAULT_LOCK = threading.Lock()


def get_agent_memory_manager(llm: Any = None, max_history: int = 10, summary_threshold: int = 20) -> AgentMemoryManager:
    """Return process-wide shared memory manager for agent sessions."""

    global _DEFAULT_MANAGER
    if _DEFAULT_MANAGER is not None:
        return _DEFAULT_MANAGER

    with _DEFAULT_LOCK:
        if _DEFAULT_MANAGER is not None:
            return _DEFAULT_MANAGER

        persist_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "..",
            "data",
            "agent_memory.json",
        )
        persist_path = os.path.abspath(persist_path)

        _DEFAULT_MANAGER = AgentMemoryManager(
            llm=llm,
            max_history=max_history,
            summary_threshold=summary_threshold,
            persist_path=persist_path,
        )

    return _DEFAULT_MANAGER
