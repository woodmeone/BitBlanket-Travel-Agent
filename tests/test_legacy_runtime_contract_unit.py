"""Unit tests for the explicit contract seam around the legacy runtime shim."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from agent.travel_agent.contracts import (
    SupervisorPlanPreview,
    SupervisorPlanPreviewRequest,
    SupervisorRunRequest,
    SupervisorToolHealthDiagnostics,
    SupervisorRuntimeContext,
)
from agent.travel_agent.graph import legacy_runtime
from agent.travel_agent.runtime.legacy_bridge import DefaultLegacyRuntimeBridge


def test_stream_supervisor_run_uses_explicit_contract(monkeypatch):
    """Legacy runtime stream shim should consume supervisor request/context directly."""
    observed: dict[str, object] = {}
    source = SimpleNamespace(agent="agent", initial_state={"messages": []}, memory_manager="memory")

    def _fake_build_supervisor_streaming_source(*, request, context):
        observed["request"] = request
        observed["context"] = context
        return source

    async def _fake_stream_graph_source(**kwargs):
        observed.update(kwargs)
        yield {"type": "done", "answer": "ok"}

    monkeypatch.setattr(
        legacy_runtime,
        "build_supervisor_streaming_source",
        _fake_build_supervisor_streaming_source,
    )
    monkeypatch.setattr(
        legacy_runtime,
        "_stream_graph_source",
        _fake_stream_graph_source,
    )

    request = SupervisorRunRequest(
        user_message="plan a trip",
        session_id="session-1",
        system_prompt="system",
        persist_memory=False,
        run_id="run-1",
        chat_mode="plan",
    )
    context = SupervisorRuntimeContext(
        llm=SimpleNamespace(name="llm"),
        tools=[SimpleNamespace(name="search_cities")],
        memory_manager=SimpleNamespace(name="memory"),
        routing_llm=SimpleNamespace(name="router"),
    )

    async def _collect():
        return [event async for event in legacy_runtime.stream_supervisor_run(request=request, context=context)]

    events = asyncio.run(_collect())

    assert events == [{"type": "done", "answer": "ok"}]
    assert observed["request"] is request
    assert observed["context"] is context
    assert observed["source"] is source
    assert observed["user_message"] == "plan a trip"
    assert observed["session_id"] == "session-1"
    assert observed["persist_memory"] is False
    assert observed["run_id"] == "run-1"


def test_generate_supervisor_plan_preview_uses_explicit_contract(monkeypatch):
    """Legacy runtime preview shim should consume supervisor request/context directly."""
    observed: dict[str, object] = {}
    source = SimpleNamespace(nodes="nodes", initial_state={"messages": []}, memory_manager="memory")

    def _fake_build_supervisor_plan_preview_source(*, request, context):
        observed["request"] = request
        observed["context"] = context
        return source

    def _fake_generate_plan_preview_from_source(source_arg):
        observed["source"] = source_arg
        return {"plan_id": "preview-1"}

    monkeypatch.setattr(
        legacy_runtime,
        "build_supervisor_plan_preview_source",
        _fake_build_supervisor_plan_preview_source,
    )
    monkeypatch.setattr(
        legacy_runtime,
        "_generate_plan_preview_from_source",
        _fake_generate_plan_preview_from_source,
    )

    request = SupervisorPlanPreviewRequest(
        user_message="preview trip",
        session_id="session-2",
        system_prompt="system-preview",
        chat_mode="react",
    )
    context = SupervisorRuntimeContext(
        llm=SimpleNamespace(name="llm"),
        tools=[SimpleNamespace(name="plan_itinerary")],
        memory_manager=SimpleNamespace(name="memory"),
        routing_llm=SimpleNamespace(name="router"),
    )

    preview = legacy_runtime.generate_supervisor_plan_preview(request=request, context=context)

    assert isinstance(preview, SupervisorPlanPreview)
    assert preview.to_dict() == {
        "plan_id": "preview-1",
        "intent": None,
        "intent_detail": {},
        "plan_explanation": "",
        "validation_status": "pass",
        "validation_errors": [],
        "plan": [],
    }
    assert observed["request"] is request
    assert observed["context"] is context
    assert observed["source"] is source


def test_stream_graph_source_delegates_event_assembly_to_runtime_event_emitter(monkeypatch):
    """Legacy stream helper should delegate normalized event assembly to the emitter layer."""

    observed: dict[str, object] = {"emitter_calls": [], "memory_writes": []}

    class _FakeMemoryManager:
        async def add_message(self, session_id, role, content):
            observed["memory_writes"].append((session_id, role, content))

    class _FakeEmitter:
        def __init__(self, *, session_id, run_id):
            observed["emitter_init"] = (session_id, run_id)

        def emit_initial(self):
            observed["emitter_calls"].append("initial")
            return {"type": "stage", "label": "initial"}

        def emit_node_start(self, node_name):
            observed["emitter_calls"].append(("node", node_name))
            return [{"type": "stage", "node": node_name}]

        def emit_chat_chunk(self, content):
            observed["emitter_calls"].append(("chunk", content))
            return {"type": "chunk", "content": content}

        def emit_tool_start(self, tool_name):
            observed["emitter_calls"].append(("tool_start", tool_name))
            return [
                {"type": "stage", "tool": tool_name},
                {"type": "tool_start", "tool": tool_name},
            ]

        def emit_tool_end(self, tool_name, result):
            observed["emitter_calls"].append(("tool_end", tool_name, result))
            return {"type": "tool_end", "tool": tool_name}

        def record_chain_output(self, output):
            observed["emitter_calls"].append(("chain", output))

        def interrupted_answer(self):
            return "[INTERRUPTED]partial"

        def persisted_answer(self):
            return "final answer"

        def emit_completion_events(self):
            observed["emitter_calls"].append("complete")
            return [
                {"type": "stage", "label": "complete"},
                {"type": "done", "answer": "ok"},
            ]

    class _FakeAgent:
        async def astream_events(self, initial_state):
            observed["initial_state"] = initial_state
            yield {"event": "on_node_start", "name": "intent"}
            yield {"event": "on_chat_model_stream", "data": {"chunk": "hello"}}
            yield {"event": "on_tool_start", "name": "search_cities"}
            yield {"event": "on_tool_end", "name": "search_cities", "data": {"output": {"city": "Shanghai"}}}
            yield {"event": "on_chain_end", "data": {"output": {"answer": "hello", "execution_stats": {}}}}

    monkeypatch.setattr(legacy_runtime, "LegacySupervisorEventEmitter", _FakeEmitter)

    source = SimpleNamespace(
        agent=_FakeAgent(),
        initial_state={"session_id": "session-1"},
        memory_manager=_FakeMemoryManager(),
    )

    async def _collect():
        return [
            event
            async for event in legacy_runtime._stream_graph_source(
                source=source,
                user_message="plan a trip",
                session_id="session-1",
                persist_memory=True,
                run_id="run-1",
            )
        ]

    events = asyncio.run(_collect())

    assert events == [
        {"type": "stage", "label": "initial"},
        {"type": "stage", "node": "intent"},
        {"type": "chunk", "content": "hello"},
        {"type": "stage", "tool": "search_cities"},
        {"type": "tool_start", "tool": "search_cities"},
        {"type": "tool_end", "tool": "search_cities"},
        {"type": "stage", "label": "complete"},
        {"type": "done", "answer": "ok"},
    ]
    assert observed["emitter_init"] == ("session-1", "run-1")
    assert observed["initial_state"] == {"session_id": "session-1"}
    assert ("node", "intent") in observed["emitter_calls"]
    assert ("chunk", "hello") in observed["emitter_calls"]
    assert ("tool_start", "search_cities") in observed["emitter_calls"]
    assert observed["memory_writes"] == [
        ("session-1", "user", "plan a trip"),
        ("session-1", "assistant", "final answer"),
    ]


def test_default_legacy_runtime_bridge_delegates_to_contract_shim(monkeypatch):
    """Bridge should delegate to contract-based legacy runtime entrypoints without re-packing kwargs."""
    observed: dict[str, object] = {}

    async def _fake_stream_supervisor_run(*, request, context):
        observed["stream_request"] = request
        observed["stream_context"] = context
        yield {"type": "done", "answer": "ok"}

    def _fake_generate_supervisor_plan_preview(*, request, context):
        observed["preview_request"] = request
        observed["preview_context"] = context
        return SupervisorPlanPreview(plan_id="preview-2", intent="itinerary")

    monkeypatch.setattr(legacy_runtime, "stream_supervisor_run", _fake_stream_supervisor_run)
    monkeypatch.setattr(
        legacy_runtime,
        "generate_supervisor_plan_preview",
        _fake_generate_supervisor_plan_preview,
    )

    bridge = DefaultLegacyRuntimeBridge()
    request = SupervisorRunRequest(
        user_message="bridge trip",
        session_id="session-3",
        system_prompt="bridge-system",
        persist_memory=True,
        run_id="run-3",
        chat_mode="plan",
    )
    preview_request = SupervisorPlanPreviewRequest(
        user_message="bridge preview",
        session_id="session-4",
        system_prompt="bridge-preview-system",
        chat_mode="plan",
    )
    context = SupervisorRuntimeContext(
        llm=SimpleNamespace(name="llm"),
        tools=[SimpleNamespace(name="search_cities")],
        memory_manager=SimpleNamespace(name="memory"),
        routing_llm=SimpleNamespace(name="router"),
    )

    async def _collect():
        return [event async for event in bridge.stream_with_memory(request=request, context=context)]

    events = asyncio.run(_collect())
    preview = bridge.generate_plan_preview_with_memory(request=preview_request, context=context)

    assert events == [{"type": "done", "answer": "ok"}]
    assert isinstance(preview, SupervisorPlanPreview)
    assert preview.to_dict()["plan_id"] == "preview-2"
    assert preview.to_dict()["intent"] == "itinerary"
    assert observed["stream_request"] is request
    assert observed["stream_context"] is context
    assert observed["preview_request"] is preview_request
    assert observed["preview_context"] is context


def test_collect_supervisor_tool_health_diagnostics_uses_explicit_contract(monkeypatch):
    """Legacy runtime diagnostics shim should normalize raw monitoring dictionaries into one contract."""

    def _fake_get_tool_health_diagnostics():
        return {
            "runtime_config": {"stream_events_version": "v2"},
            "tool_count": 1,
            "open_circuit_count": 1,
            "tools": {
                "search_cities": {
                    "consecutive_failures": 2,
                    "open_until": 123.5,
                    "is_circuit_open": True,
                    "cooldown_remaining_seconds": 12,
                }
            },
        }

    monkeypatch.setattr(
        legacy_runtime,
        "get_tool_health_diagnostics",
        _fake_get_tool_health_diagnostics,
    )

    diagnostics = legacy_runtime.collect_supervisor_tool_health_diagnostics()

    assert isinstance(diagnostics, SupervisorToolHealthDiagnostics)
    assert diagnostics.runtime_config["stream_events_version"] == "v2"
    assert diagnostics.tool_count == 1
    assert diagnostics.open_circuit_count == 1
    assert diagnostics.tools["search_cities"].consecutive_failures == 2
    assert diagnostics.tools["search_cities"].is_circuit_open is True


def test_default_legacy_runtime_bridge_returns_tool_health_contract(monkeypatch):
    """Bridge should delegate tool-health diagnostics to the typed legacy-runtime seam."""
    expected = SupervisorToolHealthDiagnostics(
        runtime_config={"stream_events_version": "v1"},
        tool_count=2,
        open_circuit_count=0,
    )

    monkeypatch.setattr(
        legacy_runtime,
        "collect_supervisor_tool_health_diagnostics",
        lambda: expected,
    )

    diagnostics = DefaultLegacyRuntimeBridge().get_tool_health_diagnostics()

    assert diagnostics is expected
