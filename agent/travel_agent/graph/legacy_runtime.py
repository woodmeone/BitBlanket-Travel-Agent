"""Legacy graph execution entrypoints kept outside the graph assembly module."""

from __future__ import annotations

from typing import Any, Callable, Optional

from langchain_core.runnables import Runnable
from langchain_core.tools import Tool

from ..contracts import (
    SupervisorChunkEvent,
    SupervisorDoneEvent,
    SupervisorPlanPreview,
    SupervisorPlanPreviewRequest,
    SupervisorReasoningEvent,
    SupervisorRunRequest,
    SupervisorRuntimeContext,
    SupervisorStageEvent,
    SupervisorToolHealthDiagnostics,
    SupervisorToolEndEvent,
    SupervisorToolStartEvent,
)
from ..runtime_sources import (
    LegacyGraphSourceAdapter,
    LegacyPlanPreviewSourceAdapter,
    build_memory_graph_source,
    build_memory_plan_preview_source,
    build_supervisor_plan_preview_source,
    build_supervisor_streaming_source,
    create_default_checkpointer,
)
from .nodes import AgentNodes
from .runtime_config import get_runtime_config
from .state import TRAVEL_AGENT_SYSTEM_PROMPT, create_initial_state

TOOL_RESULT_PREVIEW_LIMIT = 200
_INCOMPLETE_ANSWER_FALLBACK = (
    "The main steps are complete, but the current response may be truncated. "
    "Tell me whether you want me to fill in the budget, itinerary, or hotel details first."
)
_NODE_STAGE_CONFIG: dict[str, dict[str, Any]] = {
    "intent": {
        "stage": "parse",
        "progress": 10,
        "label": "Analyze request",
        "reasoning": "Analyzing user intent...",
    },
    "strategy": {
        "stage": "parse",
        "progress": 18,
        "label": "Select strategy",
        "reasoning": "Selecting the execution strategy...",
    },
    "plan": {
        "stage": "query",
        "progress": 25,
        "label": "Build plan",
        "subagent": "planning",
        "reasoning": "Preparing the execution plan...",
    },
    "react": {
        "stage": "query",
        "progress": 25,
        "label": "Run reactive planner",
        "subagent": "planning",
        "reasoning": "Preparing the reactive tool loop...",
    },
    "execute": {
        "stage": "query",
        "progress": 45,
        "label": "Query data",
        "subagent": "research",
        "reasoning": "Running tools...",
    },
    "answer": {
        "stage": "generate",
        "progress": 80,
        "label": "Draft answer",
    },
    "direct_answer": {
        "stage": "generate",
        "progress": 80,
        "label": "Draft answer",
    },
    "verify": {
        "stage": "generate",
        "progress": 72,
        "label": "Verify results",
        "subagent": "verification",
        "reasoning": "Checking price, policy, and date consistency...",
    },
    "self_check": {
        "stage": "finalize",
        "progress": 95,
        "label": "Self check answer",
    },
}


async def stream_supervisor_run(
    *,
    request: SupervisorRunRequest,
    context: SupervisorRuntimeContext,
):
    """Bridge one supervisor-stream request into the legacy graph runtime shim."""
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
    """Bridge one supervisor preview request into the legacy graph runtime shim."""
    source = build_supervisor_plan_preview_source(request=request, context=context)
    return SupervisorPlanPreview.from_dict(_generate_plan_preview_from_source(source))


def collect_supervisor_tool_health_diagnostics() -> SupervisorToolHealthDiagnostics:
    """Return the typed legacy-runtime diagnostics contract used by the bridge seam."""
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


def _is_answer_complete(answer: str) -> bool:
    """Heuristically detect whether generated answer text appears complete for early-stop control."""
    text = str(answer or "").strip()
    if len(text) < 8:
        return False
    return text[-1] in {".", "!", "?", "。", "！", "？"}


def _iter_node_stage_events(node_name: str) -> tuple[str | None, int | None, list[dict[str, Any]]]:
    """Map node-start events into normalized stage/reasoning payloads."""

    config = _NODE_STAGE_CONFIG.get(node_name)
    if not config:
        return None, None, []

    stage = str(config["stage"])
    progress = int(config["progress"])
    events: list[dict[str, Any]] = [
        SupervisorStageEvent(
            stage=stage,
            progress=progress,
            label=str(config["label"]),
            subagent=config.get("subagent"),
        ).to_dict()
    ]
    reasoning = config.get("reasoning")
    if reasoning:
        events.append(SupervisorReasoningEvent(content=str(reasoning)).to_dict())
    return stage, progress, events


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


def _normalize_done_payload(
    *,
    answer: str,
    tools_used: list[str],
    session_id: str,
    run_id: str | None,
    final_state: dict[str, Any],
) -> dict[str, Any]:
    """Build the terminal normalized payload for streaming legacy runtime shims."""

    resolved_answer = str(final_state.get("answer") or answer or "")
    resolved_tools_used = list(final_state.get("tools_used") or tools_used or [])
    execution_stats = final_state.get("execution_stats", {}) or {}
    execution_summary = final_state.get("execution_summary", {}) or {}
    verify_result = final_state.get("verify_result", {}) or {}
    strategy_detail = final_state.get("strategy_detail", {}) or {}
    tool_results = final_state.get("tool_results", {}) or {}
    plan_id = final_state.get("plan_id")
    intent = final_state.get("intent")

    verification_passed: Optional[bool]
    if isinstance(verify_result, dict) and "passed" in verify_result:
        verification_passed = bool(verify_result.get("passed"))
    elif bool(strategy_detail.get("requires_verification", False)):
        verification_passed = False
    else:
        verification_passed = True

    fallback_steps = int(execution_summary.get("fallback_steps", 0) or 0)
    if fallback_steps <= 0 and isinstance(execution_stats, dict):
        stats_steps = list(execution_stats.get("steps", []) or [])
        fallback_steps = sum(1 for item in stats_steps if bool(item.get("fallback_used", False)))

    stale_result_count = sum(
        1
        for result in (tool_results.values() if isinstance(tool_results, dict) else [])
        if isinstance(result, dict) and bool(result.get("success")) and bool(result.get("is_stale", False))
    )

    if not _is_answer_complete(resolved_answer):
        if resolved_answer:
            resolved_answer = f"{resolved_answer.rstrip()} {_INCOMPLETE_ANSWER_FALLBACK}"
        else:
            resolved_answer = _INCOMPLETE_ANSWER_FALLBACK

    return SupervisorDoneEvent(
        answer=resolved_answer,
        tools_used=resolved_tools_used,
        session_id=session_id,
        run_id=run_id,
        plan_id=plan_id,
        intent=intent,
        execution_stats=execution_stats if isinstance(execution_stats, dict) else {},
        verification_passed=verification_passed,
        stale_result_count=stale_result_count,
        fallback_steps=fallback_steps,
    ).to_dict()


async def _stream_graph_source(
    *,
    source: LegacyGraphSourceAdapter,
    user_message: str,
    session_id: str,
    persist_memory: bool,
    run_id: str | None,
):
    """Stream normalized supervisor events from one prebuilt legacy graph source."""

    answer = ""
    tools_used: list[str] = []
    final_state: dict[str, Any] = {}
    stage = "parse"
    progress = 5

    try:
        yield SupervisorStageEvent(stage=stage, progress=progress, label="Analyze request").to_dict()
        async for event in source.agent.astream_events(source.initial_state):
            event_type = event.get("event")

            if event_type == "on_node_start":
                node_name = str(event.get("name", ""))
                stage_update, progress_update, stage_events = _iter_node_stage_events(node_name)
                if stage_update is not None:
                    stage = stage_update
                if progress_update is not None:
                    progress = progress_update
                for stage_event in stage_events:
                    yield stage_event

            elif event_type == "on_chat_model_stream":
                content = _extract_text_from_chunk((event.get("data") or {}).get("chunk"))
                if content:
                    answer += content
                    yield SupervisorChunkEvent(content=content).to_dict()

            elif event_type == "on_tool_start":
                tool_name = str(event.get("name", ""))
                tools_used.append(tool_name)
                progress = min(75, progress + 5)
                yield SupervisorStageEvent(
                    stage="query",
                    progress=progress,
                    label=f"Query data: {tool_name}",
                ).to_dict()
                yield SupervisorToolStartEvent(tool=tool_name, progress=progress).to_dict()

            elif event_type == "on_tool_end":
                tool_name = str(event.get("name", ""))
                result = (event.get("data") or {}).get("output")
                yield SupervisorToolEndEvent(
                    tool=tool_name,
                    result=str(result)[:TOOL_RESULT_PREVIEW_LIMIT],
                    progress=progress,
                ).to_dict()

            elif event_type == "on_chain_end":
                output = (event.get("data") or {}).get("output")
                if isinstance(output, dict) and ("answer" in output or "execution_stats" in output):
                    final_state = output

    except Exception:
        if persist_memory:
            try:
                await _persist_memory_snapshot(
                    memory_manager=source.memory_manager,
                    session_id=session_id,
                    user_message=user_message,
                    answer=f"[INTERRUPTED]{answer}",
                )
            except Exception:
                pass
        raise

    if persist_memory:
        await _persist_memory_snapshot(
            memory_manager=source.memory_manager,
            session_id=session_id,
            user_message=user_message,
            answer=str(final_state.get("answer") or answer or ""),
        )

    yield SupervisorStageEvent(stage="finalize", progress=100, label="Complete").to_dict()
    yield _normalize_done_payload(
        answer=answer,
        tools_used=tools_used,
        session_id=session_id,
        run_id=run_id,
        final_state=final_state,
    )


def _generate_plan_preview_from_source(source: LegacyPlanPreviewSourceAdapter) -> dict[str, Any]:
    """Generate one normalized plan preview from a prebuilt legacy preview source."""

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
