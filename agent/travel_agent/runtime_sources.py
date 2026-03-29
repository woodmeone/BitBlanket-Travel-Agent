"""Shared runtime-source adapters for the typed supervisor compatibility seam."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional

from langchain_core.runnables import Runnable
from langchain_core.tools import Tool

from .contracts import (
    SupervisorPlanPreviewRequest,
    SupervisorRunRequest,
    SupervisorRuntimeContext,
)
from .graph.builder import build_travel_agent
from .graph.memory_integration import AgentStateWithMemory, get_agent_memory_manager
from .graph.nodes import AgentNodes
from .graph.state import TRAVEL_AGENT_SYSTEM_PROMPT

_DEFAULT_CHECKPOINTER = None


@dataclass(slots=True)
class LegacyGraphSourceAdapter:
    """Carry one compiled graph plus the initial state used by memory-aware legacy paths."""

    agent: Any
    initial_state: dict[str, Any]
    memory_manager: Any


@dataclass(slots=True)
class LegacyPlanPreviewSourceAdapter:
    """Carry one planner-node adapter plus preview state for contract-based preview paths."""

    nodes: AgentNodes
    initial_state: dict[str, Any]
    memory_manager: Any


def create_default_checkpointer() -> Any:
    """Create the shared legacy checkpointer with persistent-first fallback behavior."""

    global _DEFAULT_CHECKPOINTER
    if _DEFAULT_CHECKPOINTER is not None:
        return _DEFAULT_CHECKPOINTER
    try:
        from .graph.persistent_checkpointer import PersistentSqliteSaver

        default_db_path = os.path.abspath(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..",
                "..",
                "data",
                "langgraph_checkpoints.sqlite3",
            )
        )
        db_path = os.getenv("AGENT_CHECKPOINT_DB", default_db_path)
        max_checkpoints = int(os.getenv("AGENT_CHECKPOINT_MAX_PER_THREAD", "200"))
        compaction_interval = int(os.getenv("AGENT_CHECKPOINT_COMPACTION_INTERVAL", "50"))
        _DEFAULT_CHECKPOINTER = PersistentSqliteSaver(
            db_path=db_path,
            max_checkpoints_per_thread_ns=max_checkpoints,
            compaction_interval=compaction_interval,
        )
        return _DEFAULT_CHECKPOINTER
    except Exception:
        try:
            from langgraph.checkpoint.memory import InMemorySaver

            _DEFAULT_CHECKPOINTER = InMemorySaver()
            return _DEFAULT_CHECKPOINTER
        except Exception:
            return None


def build_memory_graph_source(
    *,
    user_message: str,
    llm: Runnable,
    tools: list[Tool],
    session_id: str = "default",
    memory_manager: Any = None,
    system_prompt: Optional[str] = None,
    chat_mode: Optional[str] = None,
    run_id: Optional[str] = None,
    routing_llm: Optional[Runnable] = None,
    manager_defaults: dict[str, Any] | None = None,
) -> LegacyGraphSourceAdapter:
    """Build the memory-aware graph source used by legacy run and stream adapters."""

    resolved_system_prompt = system_prompt or TRAVEL_AGENT_SYSTEM_PROMPT
    resolved_manager = memory_manager or get_agent_memory_manager(
        llm=llm,
        **(manager_defaults or {}),
    )
    initial_state = AgentStateWithMemory.create(
        user_message=user_message,
        session_id=session_id,
        memory_manager=resolved_manager,
        system_prompt=resolved_system_prompt,
        chat_mode=chat_mode,
    )
    if run_id:
        initial_state["run_id"] = run_id

    agent = build_travel_agent(
        llm,
        tools,
        resolved_system_prompt,
        checkpointer=create_default_checkpointer(),
        routing_llm=routing_llm,
    )
    return LegacyGraphSourceAdapter(
        agent=agent,
        initial_state=initial_state,
        memory_manager=resolved_manager,
    )


def build_memory_plan_preview_source(
    *,
    user_message: str,
    llm: Runnable,
    tools: list[Tool],
    session_id: str = "default",
    memory_manager: Any = None,
    system_prompt: Optional[str] = None,
    chat_mode: Optional[str] = None,
    routing_llm: Optional[Runnable] = None,
    manager_defaults: dict[str, Any] | None = None,
) -> LegacyPlanPreviewSourceAdapter:
    """Build the memory-aware preview source used by typed and compatibility preview paths."""

    resolved_system_prompt = system_prompt or TRAVEL_AGENT_SYSTEM_PROMPT
    resolved_manager = memory_manager or get_agent_memory_manager(
        llm=llm,
        **(manager_defaults or {}),
    )
    initial_state = AgentStateWithMemory.create(
        user_message=user_message,
        session_id=session_id,
        memory_manager=resolved_manager,
        system_prompt=resolved_system_prompt,
        chat_mode=chat_mode,
    )
    nodes = AgentNodes(llm, tools, resolved_system_prompt, routing_llm=routing_llm)
    return LegacyPlanPreviewSourceAdapter(
        nodes=nodes,
        initial_state=initial_state,
        memory_manager=resolved_manager,
    )


def build_supervisor_streaming_source(
    *,
    request: SupervisorRunRequest,
    context: SupervisorRuntimeContext,
) -> LegacyGraphSourceAdapter:
    """Build the memory-aware source for the typed supervisor streaming seam."""

    return build_memory_graph_source(
        user_message=request.user_message,
        llm=context.llm,
        tools=context.tools,
        session_id=request.session_id,
        memory_manager=context.memory_manager,
        system_prompt=request.resolved_system_prompt(TRAVEL_AGENT_SYSTEM_PROMPT),
        chat_mode=request.chat_mode,
        run_id=request.run_id,
        routing_llm=context.routing_llm,
    )


def build_supervisor_plan_preview_source(
    *,
    request: SupervisorPlanPreviewRequest,
    context: SupervisorRuntimeContext,
) -> LegacyPlanPreviewSourceAdapter:
    """Build the memory-aware source for the typed supervisor preview seam."""

    return build_memory_plan_preview_source(
        user_message=request.user_message,
        llm=context.llm,
        tools=context.tools,
        session_id=request.session_id,
        memory_manager=context.memory_manager,
        system_prompt=request.resolved_system_prompt(TRAVEL_AGENT_SYSTEM_PROMPT),
        chat_mode=request.chat_mode,
        routing_llm=context.routing_llm,
    )
