"""Public exports for the travel-agent graph package."""

from __future__ import annotations

from importlib import import_module
from typing import Any


_EXPORTS: dict[str, tuple[str, str]] = {
    "TravelAgentGraph": (".builder", "TravelAgentGraph"),
    "build_travel_agent": (".builder", "build_travel_agent"),
    "generate_plan_preview_with_memory": (".runtime_flow", "generate_plan_preview_with_memory"),
    "run_travel_agent": (".runtime_flow", "run_travel_agent"),
    "run_travel_agent_streaming": (".runtime_flow", "run_travel_agent_streaming"),
    "run_travel_agent_streaming_with_memory": (".runtime_flow", "run_travel_agent_streaming_with_memory"),
    "run_travel_agent_with_memory": (".runtime_flow", "run_travel_agent_with_memory"),
    "PersistentPostgresSaver": (".postgres_checkpointer", "PersistentPostgresSaver"),
    "PersistentSqliteSaver": (".persistent_checkpointer", "PersistentSqliteSaver"),
    "AgentNodes": (".nodes", "AgentNodes"),
    "IntentResult": (".nodes", "IntentResult"),
    "PlanStep": (".nodes", "PlanStep"),
    "create_nodes": (".nodes", "create_nodes"),
    "AgentRuntimeConfig": (".runtime_config", "AgentRuntimeConfig"),
    "get_runtime_config": (".runtime_config", "get_runtime_config"),
    "AgentState": (".state", "AgentState"),
    "TRAVEL_AGENT_SYSTEM_PROMPT": (".state", "TRAVEL_AGENT_SYSTEM_PROMPT"),
    "create_initial_state": (".state", "create_initial_state"),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:
    """Resolve graph exports lazily so lightweight imports avoid heavy runtime dependencies."""

    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = target
    module = import_module(module_name, __name__)
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value
