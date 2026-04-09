"""Graph execution entrypoints kept outside the graph assembly module."""

from __future__ import annotations

from typing import Any, Callable

from langchain_core.runnables import Runnable
from langchain_core.tools import Tool

from ..contracts import (
    SupervisorPlanPreview,
    SupervisorPlanPreviewRequest,
    SupervisorRunRequest,
    SupervisorRuntimeContext,
    SupervisorToolHealthDiagnostics,
)
from ..runtime_event_emitters import SupervisorEventEmitter
from ..runtime_sources import (
    GraphRuntimeSource,
    PlanPreviewSource,
    build_memory_graph_source,
    build_memory_plan_preview_source,
    build_supervisor_plan_preview_source,
    build_supervisor_streaming_source,
    create_default_checkpointer,
)
from .nodes import AgentNodes
from .runtime_config import get_runtime_config
from .state import TRAVEL_AGENT_SYSTEM_PROMPT, create_initial_state

async def stream_supervisor_run(
    *,
    request: SupervisorRunRequest,
    context: SupervisorRuntimeContext,
):
    """Run one supervisor-stream request through the graph execution flow."""
    source = build_supervisor_streaming_source(request=request, context=context)
    async for event in _stream_graph_source(
        source=source,
        user_message=request.user_message,
        session_id=request.session_id,
        persist_memory=request.persist_memory,
        run_id=request.run_id,
    ):
        yield event


def generate_supervisor_plan_preview(
    *,
    request: SupervisorPlanPreviewRequest,
    context: SupervisorRuntimeContext,
) -> SupervisorPlanPreview:
    """Run one supervisor preview request through the graph execution flow."""
    source = build_supervisor_plan_preview_source(request=request, context=context)
    return SupervisorPlanPreview.from_dict(_generate_plan_preview_from_source(source))


def collect_supervisor_tool_health_diagnostics() -> SupervisorToolHealthDiagnostics:
    """Return the typed diagnostics contract exposed by the graph execution flow."""
    return SupervisorToolHealthDiagnostics.from_dict(get_tool_health_diagnostics())


def _extract_text_from_chunk(chunk: Any) -> str:
    """Normalize LangChain 1.x chunk payload into plain text."""
    if chunk is None:
        return ""

    content = getattr(chunk, "content", chunk)
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    if isinstance(content, dict):
        text = content.get("text")
        if isinstance(text, str):
            return text
    return str(content)


async def _persist_memory_snapshot(
    *,
    memory_manager: Any,
    session_id: str,
    user_message: str,
    answer: str,
) -> None:
    """Persist one user/assistant exchange when a memory manager is available."""

    if memory_manager is None:
        return
    await memory_manager.add_message(session_id, "user", user_message)
    await memory_manager.add_message(session_id, "assistant", answer)


async def _stream_graph_source(
    *,
    source: GraphRuntimeSource,
    user_message: str,
    session_id: str,
    persist_memory: bool,
    run_id: str | None,
):
    """Stream normalized supervisor events from one prebuilt graph source."""

    emitter = SupervisorEventEmitter(session_id=session_id, run_id=run_id)

    try:
        yield emitter.emit_initial()
        async for event in source.agent.astream_events(source.initial_state):
            event_type = event.get("event")

            if event_type == "on_node_start":
                node_name = str(event.get("name", ""))
                for stage_event in emitter.emit_node_start(node_name):
                    yield stage_event

            elif event_type == "on_chat_model_stream":
                content = _extract_text_from_chunk((event.get("data") or {}).get("chunk"))
                chunk_event = emitter.emit_chat_chunk(content)
                if chunk_event:
                    yield chunk_event

            elif event_type == "on_tool_start":
                tool_name = str(event.get("name", ""))
                for stage_event in emitter.emit_tool_start(tool_name):
                    yield stage_event

            elif event_type == "on_tool_end":
                tool_name = str(event.get("name", ""))
                result = (event.get("data") or {}).get("output")
                yield emitter.emit_tool_end(tool_name, result)

            elif event_type == "on_chain_end":
                output = (event.get("data") or {}).get("output")
                emitter.record_chain_output(output)

    except Exception:
        if persist_memory:
            try:
                await _persist_memory_snapshot(
                    memory_manager=source.memory_manager,
                    session_id=session_id,
                    user_message=user_message,
                    answer=emitter.interrupted_answer(),
                )
            except Exception:
                pass
        raise

    if persist_memory:
        await _persist_memory_snapshot(
            memory_manager=source.memory_manager,
            session_id=session_id,
            user_message=user_message,
            answer=emitter.persisted_answer(),
        )

    for completion_event in emitter.emit_completion_events():
        yield completion_event


def _generate_plan_preview_from_source(source: PlanPreviewSource) -> dict[str, Any]:
    """Generate one normalized plan preview from a prebuilt preview source."""

    intent_state = dict(source.initial_state)
    intent_state.update(source.nodes.intent_node(intent_state))
    plan_state = dict(intent_state)
    plan_state.update(source.nodes.plan_node(intent_state))

    return {
        "plan_id": plan_state.get("plan_id"),
        "intent": plan_state.get("intent"),
        "intent_detail": plan_state.get("intent_detail", {}),
        "plan_explanation": plan_state.get("plan_explanation"),
        "validation_status": plan_state.get("validation_status", "pass"),
        "validation_errors": plan_state.get("validation_errors", []),
        "plan": plan_state.get("plan", []),
    }


async def run_travel_agent(
    user_message: str,
    llm: Runnable,
    tools: list[Tool],
    session_id: str = "default",
    system_prompt: str | None = None,
    run_id: str | None = None,
    chat_mode: str | None = None,
    routing_llm: Runnable | None = None,
) -> dict:
    """Run the graph once in non-streaming mode and return final answer/result fields."""
    from .builder import build_travel_agent

    agent = build_travel_agent(
        llm,
        tools,
        system_prompt or TRAVEL_AGENT_SYSTEM_PROMPT,
        checkpointer=create_default_checkpointer(),
        routing_llm=routing_llm,
    )
    initial_state = create_initial_state(
        user_message=user_message,
        session_id=session_id,
        system_message=system_prompt or TRAVEL_AGENT_SYSTEM_PROMPT,
        run_id=run_id,
        chat_mode=chat_mode,
    )
    result = await agent.ainvoke(initial_state)
    return {
        "success": True,
        "answer": result.get("answer", ""),
        "intent": result.get("intent"),
        "tools_used": result.get("tools_used", []),
        "reasoning": result.get("reasoning"),
        "messages": result.get("messages", []),
    }


async def run_travel_agent_streaming(
    user_message: str,
    llm: Runnable,
    tools: list[Tool],
    session_id: str = "default",
    system_prompt: str | None = None,
    run_id: str | None = None,
    chat_mode: str | None = None,
    on_token: Callable | None = None,
    on_tool_start: Callable | None = None,
    on_tool_end: Callable | None = None,
    routing_llm: Runnable | None = None,
) -> dict:
    """Run the graph in streaming mode and yield normalized chunks for UI consumption."""
    from .builder import build_travel_agent

    agent = build_travel_agent(
        llm,
        tools,
        system_prompt or TRAVEL_AGENT_SYSTEM_PROMPT,
        checkpointer=create_default_checkpointer(),
        routing_llm=routing_llm,
    )
    initial_state = create_initial_state(
        user_message=user_message,
        session_id=session_id,
        system_message=system_prompt or TRAVEL_AGENT_SYSTEM_PROMPT,
        run_id=run_id,
        chat_mode=chat_mode,
    )

    answer = ""
    tools_used: list[str] = []

    async for event in agent.astream_events(initial_state):
        event_type = event.get("event")

        if event_type == "on_chat_model_stream":
            chunk = _extract_text_from_chunk((event.get("data") or {}).get("chunk"))
            if chunk:
                answer += chunk
                if on_token:
                    await on_token(chunk)

        elif event_type == "on_tool_start":
            tool_name = event.get("name", "")
            tools_used.append(tool_name)
            if on_tool_start:
                await on_tool_start(tool_name)

        elif event_type == "on_tool_end":
            tool_name = event.get("name", "")
            result = (event.get("data") or {}).get("output")
            if on_tool_end:
                await on_tool_end(tool_name, result)

    return {"success": True, "answer": answer, "tools_used": tools_used, "run_id": run_id}


async def run_travel_agent_with_memory(
    user_message: str,
    llm: Runnable,
    tools: list[Tool],
    session_id: str = "default",
    memory_manager=None,
    system_prompt: str | None = None,
    chat_mode: str | None = None,
    on_token: Callable | None = None,
    on_tool_start: Callable | None = None,
    on_tool_end: Callable | None = None,
    persist_memory: bool = True,
    run_id: str | None = None,
    routing_llm: Runnable | None = None,
) -> dict:
    """Run non-streaming graph execution with memory context injection."""

    source = build_memory_graph_source(
        user_message=user_message,
        llm=llm,
        tools=tools,
        session_id=session_id,
        memory_manager=memory_manager,
        system_prompt=system_prompt,
        chat_mode=chat_mode,
        run_id=run_id,
        routing_llm=routing_llm,
        manager_defaults={"max_history": 10, "summary_threshold": 15},
    )

    answer = ""
    tools_used: list[str] = []
    async for event in source.agent.astream_events(source.initial_state):
        event_type = event.get("event")
        if event_type == "on_chat_model_stream":
            content = _extract_text_from_chunk((event.get("data") or {}).get("chunk"))
            if content:
                answer += content
                if on_token:
                    await on_token(content)
        elif event_type == "on_tool_start":
            tool_name = event.get("name", "")
            tools_used.append(tool_name)
            if on_tool_start:
                await on_tool_start(tool_name)
        elif event_type == "on_tool_end":
            tool_name = event.get("name", "")
            result = (event.get("data") or {}).get("output")
            if on_tool_end:
                await on_tool_end(tool_name, result)

    if persist_memory:
        await _persist_memory_snapshot(
            memory_manager=source.memory_manager,
            session_id=session_id,
            user_message=user_message,
            answer=answer,
        )

    return {
        "success": True,
        "answer": answer,
        "tools_used": tools_used,
        "session_id": session_id,
        "run_id": run_id,
    }


async def run_travel_agent_streaming_with_memory(
    user_message: str,
    llm: Runnable,
    tools: list[Tool],
    session_id: str = "default",
    memory_manager=None,
    system_prompt: str | None = None,
    persist_memory: bool = True,
    run_id: str | None = None,
    chat_mode: str | None = None,
    routing_llm: Runnable | None = None,
):
    """Run streaming graph execution with memory context and normalized event payloads."""

    source = build_memory_graph_source(
        user_message=user_message,
        llm=llm,
        tools=tools,
        session_id=session_id,
        memory_manager=memory_manager,
        system_prompt=system_prompt,
        chat_mode=chat_mode,
        run_id=run_id,
        routing_llm=routing_llm,
    )
    async for event in _stream_graph_source(
        source=source,
        user_message=user_message,
        session_id=session_id,
        persist_memory=persist_memory,
        run_id=run_id,
    ):
        yield event


def generate_plan_preview_with_memory(
    user_message: str,
    llm: Runnable,
    tools: list[Tool],
    session_id: str = "default",
    memory_manager=None,
    system_prompt: str | None = None,
    chat_mode: str | None = None,
    routing_llm: Runnable | None = None,
) -> dict:
    """Generate a memory-aware plan preview without executing full tool orchestration."""

    source = build_memory_plan_preview_source(
        user_message=user_message,
        llm=llm,
        tools=tools,
        session_id=session_id,
        memory_manager=memory_manager,
        system_prompt=system_prompt,
        chat_mode=chat_mode,
        routing_llm=routing_llm,
    )
    return _generate_plan_preview_from_source(source)


def get_tool_health_diagnostics() -> dict[str, Any]:
    """Return aggregated tool-health diagnostics for monitoring and health endpoints."""
    return {
        "runtime_config": get_runtime_config().to_dict(),
        **AgentNodes.get_global_tool_health_snapshot(),
    }
