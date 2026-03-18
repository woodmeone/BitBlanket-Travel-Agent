"""Supervisor node wrapper built on top of the current single-graph implementation."""

from __future__ import annotations

from typing import Any, Callable, Optional

from langchain_core.runnables import Runnable
from langchain_core.tools import Tool

from ..artifacts import build_trip_plan_artifact_from_state
from ..graph.nodes import AgentNodes
from ..skills import SkillRegistry, build_default_skill_registry


class SupervisorNodes(AgentNodes):
    """Phase-1 compatibility wrapper that introduces supervisor metadata and skills."""

    def __init__(
        self,
        llm: Runnable,
        tools: list[Tool],
        system_prompt: str,
        planner_hooks: Optional[dict[str, Callable[[dict], list[dict]]]] = None,
        routing_llm: Optional[Runnable] = None,
        skill_registry: Optional[SkillRegistry] = None,
    ):
        """Initialize phase-1 supervisor nodes while preserving current node behavior."""
        super().__init__(
            llm=llm,
            tools=tools,
            system_prompt=system_prompt,
            planner_hooks=planner_hooks,
            routing_llm=routing_llm,
        )
        self.skill_registry = skill_registry or build_default_skill_registry(tools)
        self.subagent_order = ["research", "planning", "budget", "verification"]

    def build_trip_plan_artifact(self, state: dict[str, Any]) -> dict[str, Any]:
        """Build an artifact-first payload from the current graph state."""
        return build_trip_plan_artifact_from_state(state)
