"""Dependency providers for web application services."""

from __future__ import annotations

import os
from typing import Optional

from ..bootstrap import PROJECT_ROOT, ensure_project_paths
from ..config.runtime import get_llm_config_path

ensure_project_paths()

from ..repositories.session_repository_impl import SessionRepositoryImpl
from ..services.chat_service import ChatService
from ..services.session_service import SessionService
from ..storage.session_storage import FileSessionStorage
from agent.travel_agent.graph.memory_integration import get_agent_memory_manager

_storage: Optional[FileSessionStorage] = None
_repository: Optional[SessionRepositoryImpl] = None
_session_service: Optional[SessionService] = None
_chat_service: Optional[ChatService] = None


def _get_storage() -> FileSessionStorage:
    """Create or reuse file-backed session storage singleton."""
    global _storage
    if _storage is None:
        session_file = os.path.join(str(PROJECT_ROOT), "data", "sessions", "sessions.json")
        _storage = FileSessionStorage(session_file)
    return _storage


def provide_session_repository() -> SessionRepositoryImpl:
    """Create or reuse session repository singleton."""
    global _repository
    if _repository is None:
        _repository = SessionRepositoryImpl(_get_storage())
    return _repository


def provide_session_service() -> SessionService:
    """Create or reuse session service singleton with memory integration."""
    global _session_service
    if _session_service is None:
        _session_service = SessionService(
            provide_session_repository(),
            memory_manager=get_agent_memory_manager(max_history=10, summary_threshold=20),
        )
    return _session_service


def provide_chat_service() -> ChatService:
    """Create or reuse chat service singleton."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService(provide_session_repository())
    return _chat_service


def provide_travel_agent():
    """Build one travel agent instance using configured LLM and tools."""
    from agent.travel_agent.llm.langchain_adapter import create_from_yaml_config
    from agent.travel_agent.tools.travel_tools import get_travel_tools
    from agent.travel_agent.graph.builder import build_travel_agent

    config_path = get_llm_config_path()
    llm_adapter = create_from_yaml_config(config_path)
    llm = llm_adapter.chat_model
    tools = get_travel_tools()
    return build_travel_agent(llm, tools)
