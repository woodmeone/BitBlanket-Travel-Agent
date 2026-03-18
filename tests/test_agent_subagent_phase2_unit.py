"""Automated tests for phase-2 subagent runtime behavior."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from agent.travel_agent.runtime.agent_runtime import AgentRuntime
from agent.travel_agent.subagents import build_default_subagent_registry


def test_default_subagent_registry_resolves_stage_and_tool_mapping():
    skill_registry = SimpleNamespace(
        for_subagent=lambda name: {
            "research": [SimpleNamespace(name="CityResearchSkill", tool_names=["search_cities"])],
            "planning": [SimpleNamespace(name="PlanSynthesisSkill", tool_names=["plan_itinerary", "query_hotels"])],
            "verification": [SimpleNamespace(name="BudgetAggregationSkill", tool_names=["calculate_budget"])],
        }.get(name, [])
    )

    registry = build_default_subagent_registry(skill_registry)

    assert registry.names() == ["research", "planning", "verification"]
    assert registry.resolve_subagent_for_stage(stage="query", label="生成计划", explicit_subagent=None) == "planning"
    assert registry.resolve_subagent_for_stage(stage="generate", label="验证结果一致性", explicit_subagent=None) == "verification"
    assert registry.resolve_subagent_for_tool("search_cities") == "research"
    assert registry.resolve_subagent_for_tool("plan_itinerary") == "planning"
    assert registry.resolve_subagent_for_tool("calculate_budget") == "verification"


def test_runtime_emits_subagent_events_and_artifact_patches(monkeypatch):
    runtime = AgentRuntime(
        llm=SimpleNamespace(),
        tools=[
            SimpleNamespace(name="search_cities"),
            SimpleNamespace(name="plan_itinerary"),
            SimpleNamespace(name="calculate_budget"),
        ],
        memory_manager=SimpleNamespace(),
    )

    async def _fake_stream(**kwargs):
        _ = kwargs
        yield {"type": "stage", "stage": "query", "label": "生成计划", "subagent": "planning"}
        yield {"type": "tool_start", "tool": "plan_itinerary"}
        yield {"type": "tool_end", "tool": "plan_itinerary", "result": "ok"}
        yield {"type": "stage", "stage": "query", "label": "查询数据", "subagent": "research"}
        yield {"type": "tool_start", "tool": "search_cities"}
        yield {"type": "tool_end", "tool": "search_cities", "result": "ok"}
        yield {"type": "stage", "stage": "generate", "label": "验证结果一致性", "subagent": "verification"}
        yield {
            "type": "done",
            "answer": "hello",
            "intent": "itinerary",
            "tools_used": ["plan_itinerary", "search_cities", "calculate_budget"],
            "run_id": "run-2",
            "plan_id": "plan-2",
            "verification_passed": True,
            "stale_result_count": 0,
            "fallback_steps": 0,
            "execution_stats": {"steps": []},
        }

    monkeypatch.setattr("agent.travel_agent.runtime.agent_runtime.run_travel_agent_streaming_with_memory", _fake_stream)

    async def _collect():
        return [
            event
            async for event in runtime.stream_with_memory(
                user_message="plan and verify",
                session_id="session-2",
                persist_memory=False,
                run_id="run-2",
                chat_mode="plan",
            )
        ]

    events = asyncio.run(_collect())
    event_types = [event["type"] for event in events]

    assert "subagent_start" in event_types
    assert "subagent_end" in event_types
    assert "artifact_patch" in event_types
    assert event_types[-1] == "done"

    planning_start = next(event for event in events if event["type"] == "subagent_start" and event["subagent"] == "planning")
    verification_end = next(event for event in events if event["type"] == "subagent_end" and event["subagent"] == "verification")
    done_event = events[-1]

    assert "PlanSynthesisSkill" in planning_start["skills"]
    assert verification_end["status"] == "completed"
    assert done_event["artifact"]["verification"]["passed"] is True
    assert done_event["artifact"]["metadata"]["verification_subagent_completed"] is True
