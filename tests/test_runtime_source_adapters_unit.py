"""Unit tests for runtime source adapters used by the supervisor execution seam."""

from __future__ import annotations

from types import SimpleNamespace

from agent.travel_agent.contracts import (
    SupervisorPlanPreviewRequest,
    SupervisorRunRequest,
    SupervisorRuntimeContext,
)
from agent.travel_agent.runtime_sources import (
    GraphRuntimeSource,
    PlanPreviewSource,
    build_memory_graph_source,
    build_memory_plan_preview_source,
    build_supervisor_plan_preview_source,
    build_supervisor_streaming_source,
)


def test_build_memory_graph_source_prepares_state_and_graph(monkeypatch):
    """Memory graph source should own state preparation instead of runtime_flow."""

    observed: dict[str, object] = {}
    memory_manager = SimpleNamespace(name="memory")
    agent = SimpleNamespace(name="agent")
    checkpointer = SimpleNamespace(name="checkpointer")

    def _fake_get_agent_memory_manager(*, llm, **kwargs):
        observed["memory_manager_llm"] = llm
        observed["manager_defaults"] = kwargs
        return memory_manager

    def _fake_create(*, user_message, session_id, memory_manager, system_prompt, chat_mode):
        observed["initial_state_args"] = {
            "user_message": user_message,
            "session_id": session_id,
            "memory_manager": memory_manager,
            "system_prompt": system_prompt,
            "chat_mode": chat_mode,
        }
        return {"session_id": session_id, "chat_mode": chat_mode}

    def _fake_build_travel_agent(llm, tools, system_prompt, *, checkpointer, routing_llm):
        observed["build_agent_args"] = {
            "llm": llm,
            "tools": tools,
            "system_prompt": system_prompt,
            "checkpointer": checkpointer,
            "routing_llm": routing_llm,
        }
        return agent

    monkeypatch.setattr("agent.travel_agent.runtime_sources.get_agent_memory_manager", _fake_get_agent_memory_manager)
    monkeypatch.setattr("agent.travel_agent.runtime_sources.AgentStateWithMemory.create", _fake_create)
    monkeypatch.setattr("agent.travel_agent.runtime_sources.build_travel_agent", _fake_build_travel_agent)
    monkeypatch.setattr("agent.travel_agent.runtime_sources.create_default_checkpointer", lambda: checkpointer)

    source = build_memory_graph_source(
        user_message="plan a trip",
        llm=SimpleNamespace(name="llm"),
        tools=[SimpleNamespace(name="search_cities")],
        session_id="session-1",
        system_prompt="system",
        chat_mode="plan",
        run_id="run-1",
        routing_llm=SimpleNamespace(name="router"),
        manager_defaults={"max_history": 10, "summary_threshold": 15},
    )

    assert isinstance(source, GraphRuntimeSource)
    assert source.agent is agent
    assert source.memory_manager is memory_manager
    assert source.initial_state["run_id"] == "run-1"
    assert observed["manager_defaults"] == {"max_history": 10, "summary_threshold": 15}
    assert observed["initial_state_args"]["system_prompt"] == "system"
    assert observed["build_agent_args"]["checkpointer"] is checkpointer


def test_build_memory_plan_preview_source_prepares_nodes_and_state(monkeypatch):
    """Plan preview adapter should build preview state outside the runtime flow."""

    observed: dict[str, object] = {}
    memory_manager = SimpleNamespace(name="memory")
    nodes = SimpleNamespace(name="nodes")

    def _fake_create(*, user_message, session_id, memory_manager, system_prompt, chat_mode):
        observed["initial_state_args"] = {
            "user_message": user_message,
            "session_id": session_id,
            "memory_manager": memory_manager,
            "system_prompt": system_prompt,
            "chat_mode": chat_mode,
        }
        return {"session_id": session_id}

    def _fake_agent_nodes(llm, tools, system_prompt, *, routing_llm):
        observed["nodes_args"] = {
            "llm": llm,
            "tools": tools,
            "system_prompt": system_prompt,
            "routing_llm": routing_llm,
        }
        return nodes

    monkeypatch.setattr("agent.travel_agent.runtime_sources.AgentStateWithMemory.create", _fake_create)
    monkeypatch.setattr("agent.travel_agent.runtime_sources.AgentNodes", _fake_agent_nodes)

    source = build_memory_plan_preview_source(
        user_message="preview a trip",
        llm=SimpleNamespace(name="llm"),
        tools=[SimpleNamespace(name="plan_itinerary")],
        session_id="session-2",
        memory_manager=memory_manager,
        system_prompt="preview-system",
        chat_mode="react",
        routing_llm=SimpleNamespace(name="router"),
    )

    assert isinstance(source, PlanPreviewSource)
    assert source.nodes is nodes
    assert source.memory_manager is memory_manager
    assert observed["initial_state_args"]["chat_mode"] == "react"
    assert observed["nodes_args"]["system_prompt"] == "preview-system"


def test_supervisor_source_builders_forward_resolved_contract_inputs(monkeypatch):
    """Supervisor adapter helpers should forward typed request/context inputs unchanged."""

    observed: dict[str, object] = {}
    graph_source = SimpleNamespace(kind="graph")
    preview_source = SimpleNamespace(kind="preview")

    def _fake_build_memory_graph_source(**kwargs):
        observed["graph_kwargs"] = kwargs
        return graph_source

    def _fake_build_memory_plan_preview_source(**kwargs):
        observed["preview_kwargs"] = kwargs
        return preview_source

    monkeypatch.setattr("agent.travel_agent.runtime_sources.build_memory_graph_source", _fake_build_memory_graph_source)
    monkeypatch.setattr(
        "agent.travel_agent.runtime_sources.build_memory_plan_preview_source",
        _fake_build_memory_plan_preview_source,
    )

    request = SupervisorRunRequest(
        user_message="plan a weekend",
        session_id="session-3",
        system_prompt="supervisor-system",
        run_id="run-3",
        chat_mode="plan",
    )
    preview_request = SupervisorPlanPreviewRequest(
        user_message="preview weekend",
        session_id="session-4",
        system_prompt="preview-system",
        chat_mode="react",
    )
    context = SupervisorRuntimeContext(
        llm=SimpleNamespace(name="llm"),
        tools=[SimpleNamespace(name="search_cities")],
        memory_manager=SimpleNamespace(name="memory"),
        routing_llm=SimpleNamespace(name="router"),
    )

    assert build_supervisor_streaming_source(request=request, context=context) is graph_source
    assert build_supervisor_plan_preview_source(request=preview_request, context=context) is preview_source
    assert observed["graph_kwargs"]["user_message"] == "plan a weekend"
    assert observed["graph_kwargs"]["system_prompt"] == "supervisor-system"
    assert observed["graph_kwargs"]["routing_llm"] is context.routing_llm
    assert observed["preview_kwargs"]["user_message"] == "preview weekend"
    assert observed["preview_kwargs"]["system_prompt"] == "preview-system"
    assert observed["preview_kwargs"]["memory_manager"] is context.memory_manager
