"""Supervisor graph builder compatible with the current LangGraph runtime."""

from __future__ import annotations

from typing import Any, Callable, Optional

from langchain_core.runnables import Runnable
from langchain_core.tools import Tool

from ..graph.builder import TravelAgentGraph
from ..graph.state import TRAVEL_AGENT_SYSTEM_PROMPT
from ..skills import SkillRegistry, build_default_skill_registry
from .nodes import SupervisorNodes


class SupervisorTravelAgentGraph(TravelAgentGraph):
    """Compatibility graph that swaps in supervisor-aware nodes and skill registry metadata."""

    def __init__(
        self,
        llm: Runnable,
        tools: list[Tool],
        system_prompt: str = TRAVEL_AGENT_SYSTEM_PROMPT,
        planner_hooks: Optional[dict[str, Callable[[dict], list[dict]]]] = None,
        checkpointer: Any = None,
        routing_llm: Optional[Runnable] = None,
        skill_registry: Optional[SkillRegistry] = None,
    ):
        """Initialize the supervisor graph while keeping the current graph topology intact."""
        self.llm = llm
        self.tools = tools
        self.system_prompt = system_prompt
        self.skill_registry = skill_registry or build_default_skill_registry(tools)
        self.nodes = SupervisorNodes(
            llm=llm,
            tools=tools,
            system_prompt=system_prompt,
            planner_hooks=planner_hooks,
            routing_llm=routing_llm,
            skill_registry=self.skill_registry,
        )
        self.checkpointer = checkpointer
        self._graph = None


def build_supervisor_agent(
    llm: Runnable,
    tools: list[Tool],
    system_prompt: str = TRAVEL_AGENT_SYSTEM_PROMPT,
    planner_hooks: Optional[dict[str, Callable[[dict], list[dict]]]] = None,
    checkpointer: Any = None,
    routing_llm: Optional[Runnable] = None,
    skill_registry: Optional[SkillRegistry] = None,
) -> SupervisorTravelAgentGraph:
    """Create and compile the phase-1 supervisor graph wrapper."""
    agent = SupervisorTravelAgentGraph(
        llm=llm,
        tools=tools,
        system_prompt=system_prompt,
        planner_hooks=planner_hooks,
        checkpointer=checkpointer,
        routing_llm=routing_llm,
        skill_registry=skill_registry,
    )
    agent.build()
    return agent
