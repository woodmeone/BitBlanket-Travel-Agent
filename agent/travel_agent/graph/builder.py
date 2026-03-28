"""Graph assembly and execution entrypoints for the travel agent runtime."""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any, Callable, Optional

from langchain_core.runnables import Runnable
from langchain_core.tools import Tool
from langgraph.graph import END, StateGraph

from .nodes import AgentNodes
from .runtime_config import get_runtime_config
from .state import AgentState, TRAVEL_AGENT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def _resolve_stream_events_version() -> str:
    """Resolve the configured LangGraph stream-events version for compatibility across runtimes.
    
    Purpose:
        Explain how this routine updates graph state, tool execution flow, and downstream decision logic.
    
    Returns:
        str: Normalized text string used by downstream logic.
    """
    return get_runtime_config().stream_events_version


class TravelAgentGraph:
    """LangGraph wrapper for travel-agent orchestration."""

    def __init__(
        self,
        llm: Runnable,
        tools: list[Tool],
        system_prompt: str = TRAVEL_AGENT_SYSTEM_PROMPT,
        planner_hooks: Optional[dict[str, Callable[[dict], list[dict]]]] = None,
        checkpointer: Any = None,
        routing_llm: Optional[Runnable] = None,
    ):
        """Initialize the graph wrapper with LLMs, tool registry, prompts, and optional checkpoint integration.
        
        Purpose:
            Explain how this routine updates graph state, tool execution flow, and downstream decision logic.
        
        Args:
            llm: Primary chat model runnable used for reasoning and answer generation.
            tools: Registered tool list available for planner/execution stages.
            system_prompt: System prompt text injected at the beginning of model context.
            planner_hooks: Optional hooks used to override planner behavior in tests/experiments.
            checkpointer: Optional LangGraph checkpointer used to persist per-session graph state.
            routing_llm: Optional model used for intent/strategy routing when different from main llm.
        
        Returns:
            Any: Runtime-dependent object returned to the calling layer.
        """
        self.llm = llm
        self.tools = tools
        self.system_prompt = system_prompt
        self.nodes = AgentNodes(llm, tools, system_prompt, planner_hooks=planner_hooks, routing_llm=routing_llm)
        self.checkpointer = checkpointer
        self._graph: Optional[StateGraph] = None

    def build(self) -> StateGraph:
        """Construct and compile the LangGraph state machine used by the travel agent runtime.
        
        Purpose:
            Explain how this routine updates graph state, tool execution flow, and downstream decision logic.
        
        Returns:
            StateGraph: Compiled LangGraph state machine instance.
        """
        graph = StateGraph(AgentState)
        graph.add_node("intent", self.nodes.intent_node)
        graph.add_node("strategy", self.nodes.strategy_node)
        graph.add_node("plan", self.nodes.plan_node)
        graph.add_node("react", self.nodes.plan_node)
        graph.add_node("execute", self.nodes.execute_node)
        graph.add_node("verify", self.nodes.verify_node)
        graph.add_node("answer", self.nodes.answer_node)
        graph.add_node("direct_answer", self.nodes.direct_answer_node)
        graph.add_node("self_check", self.nodes.self_check_node)

        graph.set_entry_point("intent")
        graph.add_edge("intent", "strategy")
        # Strategy is the first major branch point: simple requests can answer directly,
        # while more complex requests choose between planned and reactive execution.
        graph.add_conditional_edges(
            "strategy",
            self.nodes.routing_decision,
            {"plan": "plan", "react": "react", "direct": "direct_answer"},
        )
        graph.add_edge("plan", "execute")
        graph.add_edge("react", "execute")
        # Execute may loop to gather more evidence; verify decides whether the current
        # tool results are strong enough to draft a final answer.
        graph.add_conditional_edges(
            "execute",
            self.nodes.should_continue,
            {"execute": "execute", "answer": "verify"},
        )
        graph.add_conditional_edges(
            "verify",
            self.nodes.verify_decision,
            {"execute": "execute", "answer": "answer"},
        )
        graph.add_edge("answer", "self_check")
        graph.add_edge("direct_answer", "self_check")
        graph.add_edge("self_check", END)

        compile_kwargs = {}
        if self.checkpointer is not None:
            compile_kwargs["checkpointer"] = self.checkpointer

        self._graph = graph.compile(**compile_kwargs)
        logger.info("[Graph Builder] Graph built successfully")
        return self._graph

    @property
    def graph(self) -> StateGraph:
        """Return a compiled graph instance and lazily build it when first requested.
        
        Purpose:
            Explain how this routine updates graph state, tool execution flow, and downstream decision logic.
        
        Returns:
            StateGraph: Compiled LangGraph state machine instance.
        """
        if self._graph is None:
            self.build()
        return self._graph

    def _build_thread_config(self, state: dict) -> dict[str, dict[str, str]]:
        """Build per-session thread config so checkpoints and event streams remain session-scoped.
        
        Purpose:
            Explain how this routine updates graph state, tool execution flow, and downstream decision logic.
        
        Args:
            state: Mutable LangGraph state snapshot passed between node stages.
        
        Returns:
            dict[str, dict[str, str]]: Nested config mapping passed to LangGraph runtime.
        """
        session_id = state.get("session_id")
        if not session_id:
            return {}
        return {"configurable": {"thread_id": str(session_id)}}

    def invoke(self, state: dict) -> dict:
        """Run one synchronous graph invocation with async fallback for async-only nodes.
        
        Purpose:
            Explain how this routine updates graph state, tool execution flow, and downstream decision logic.
        
        Args:
            state: Mutable LangGraph state snapshot passed between node stages.
        
        Returns:
            dict: Structured dictionary result for upstream callers.
        """
        config = self._build_thread_config(state)
        resolved_config = config if config else None
        try:
            return self.graph.invoke(state, config=resolved_config)
        except TypeError as exc:
            if "No synchronous function provided" not in str(exc):
                raise
            logger.info("[Graph Builder] Falling back to async invoke due to async-only node execution")
            return self._run_ainvoke_sync(state, resolved_config)

    async def ainvoke(self, state: dict) -> dict:
        """Run one asynchronous graph invocation and return final merged state snapshot.
        
        Purpose:
            Explain how this routine updates graph state, tool execution flow, and downstream decision logic.
        
        Args:
            state: Mutable LangGraph state snapshot passed between node stages.
        
        Returns:
            dict: Structured dictionary result for upstream callers.
        """
        config = self._build_thread_config(state)
        return await self.graph.ainvoke(state, config=config if config else None)

    async def astream(self, state: dict):
        """Stream value-mode graph updates used by progressive UI rendering.
        
        Purpose:
            Explain how this routine updates graph state, tool execution flow, and downstream decision logic.
        
        Args:
            state: Mutable LangGraph state snapshot passed between node stages.
        
        Returns:
            Any: Runtime-dependent object returned to the calling layer.
        """
        config = self._build_thread_config(state)
        async for chunk in self.graph.astream(state, stream_mode="values", config=config if config else None):
            yield chunk

    async def astream_events(self, state: dict):
        """Stream structured graph events for telemetry, stage updates, and SSE transport.
        
        Purpose:
            Explain how this routine updates graph state, tool execution flow, and downstream decision logic.
        
        Args:
            state: Mutable LangGraph state snapshot passed between node stages.
        
        Returns:
            Any: Runtime-dependent object returned to the calling layer.
        """
        config = self._build_thread_config(state)
        async for event in self.graph.astream_events(
            state,
            version=_resolve_stream_events_version(),
            config=config if config else None,
        ):
            yield event

    def _run_ainvoke_sync(self, state: dict, config: dict | None) -> dict:
        """Bridge async graph execution into sync call-sites while preserving event-loop safety.
        
        Purpose:
            Explain how this routine updates graph state, tool execution flow, and downstream decision logic.
        
        Args:
            state: Mutable LangGraph state snapshot passed between node stages.
            config: Optional invocation config passed to LangGraph runtime.
        
        Returns:
            dict: Structured dictionary result for upstream callers.
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.graph.ainvoke(state, config=config))

        result_holder: dict[str, Any] = {}
        error_holder: dict[str, Exception] = {}

        def _runner() -> None:
            """Run asynchronous graph invocation inside a bridge thread.
            
            Purpose:
                Explain how this routine updates graph state, tool execution flow, and downstream decision logic.
            
            Returns:
                None: No explicit return value; side effects happen in-place.
            """
            try:
                result_holder["result"] = asyncio.run(self.graph.ainvoke(state, config=config))
            except Exception as inner_exc:  # pragma: no cover - defensive bridge
                error_holder["error"] = inner_exc

        thread = threading.Thread(target=_runner, name="travel-agent-ainvoke-bridge", daemon=True)
        thread.start()
        thread.join()

        if "error" in error_holder:
            raise error_holder["error"]
        return dict(result_holder.get("result") or {})


def build_travel_agent(
    llm: Runnable,
    tools: list[Tool],
    system_prompt: str = TRAVEL_AGENT_SYSTEM_PROMPT,
    planner_hooks: Optional[dict[str, Callable[[dict], list[dict]]]] = None,
    checkpointer: Any = None,
    routing_llm: Optional[Runnable] = None,
) -> TravelAgentGraph:
    """Create and compile a travel-agent graph instance with runtime defaults.
    
    Purpose:
        Explain how this routine updates graph state, tool execution flow, and downstream decision logic.
    
    Args:
        llm: Primary chat model runnable used for reasoning and answer generation.
        tools: Registered tool list available for planner/execution stages.
        system_prompt: System prompt text injected at the beginning of model context.
        planner_hooks: Optional hooks used to override planner behavior in tests/experiments.
        checkpointer: Optional LangGraph checkpointer used to persist per-session graph state.
        routing_llm: Optional model used for intent/strategy routing when different from main llm.
    
    Returns:
        TravelAgentGraph: Initialized travel-agent graph wrapper.
    """
    return TravelAgentGraph(
        llm,
        tools,
        system_prompt,
        planner_hooks=planner_hooks,
        checkpointer=checkpointer,
        routing_llm=routing_llm,
    )

from .legacy_runtime import (  # noqa: E402
    _extract_text_from_chunk,
    generate_plan_preview_with_memory,
    get_tool_health_diagnostics,
    run_travel_agent,
    run_travel_agent_streaming,
    run_travel_agent_streaming_with_memory,
    run_travel_agent_with_memory,
)
