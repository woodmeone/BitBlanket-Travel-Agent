"""Contracts that describe one supervisor runtime request and shared execution context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from langchain_core.runnables import Runnable
from langchain_core.tools import Tool


@dataclass(slots=True)
class SupervisorRuntimeContext:
    """Carry shared runtime dependencies used by the supervisor compatibility bridge."""

    llm: Runnable
    tools: list[Tool]
    memory_manager: Any = None
    routing_llm: Optional[Runnable] = None


@dataclass(slots=True)
class SupervisorRunRequest:
    """Describe one streaming supervisor run requested by the application layer."""

    user_message: str
    session_id: str = "default"
    system_prompt: Optional[str] = None
    persist_memory: bool = True
    run_id: Optional[str] = None
    chat_mode: Optional[str] = None

    def resolved_system_prompt(self, default: str) -> str:
        """Return the effective system prompt for this runtime request."""
        return self.system_prompt or default


@dataclass(slots=True)
class SupervisorPlanPreviewRequest:
    """Describe one supervisor plan-preview request issued through the runtime seam."""

    user_message: str
    session_id: str = "default"
    system_prompt: Optional[str] = None
    chat_mode: Optional[str] = None

    def resolved_system_prompt(self, default: str) -> str:
        """Return the effective system prompt for this preview request."""
        return self.system_prompt or default
