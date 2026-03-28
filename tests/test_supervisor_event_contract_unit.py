"""Unit tests for normalized supervisor runtime event contracts."""

from __future__ import annotations

from agent.travel_agent.contracts import (
    SupervisorChunkEvent,
    SupervisorDoneEvent,
    SupervisorReasoningEvent,
    SupervisorStageEvent,
    SupervisorToolEndEvent,
    SupervisorToolStartEvent,
)


def test_supervisor_stage_event_omits_empty_subagent():
    payload = SupervisorStageEvent(stage="parse", progress=10, label="解析需求").to_dict()

    assert payload == {
        "type": "stage",
        "stage": "parse",
        "progress": 10,
        "label": "解析需求",
    }


def test_supervisor_stage_event_includes_subagent_when_present():
    payload = SupervisorStageEvent(
        stage="query",
        progress=45,
        label="查询数据",
        subagent="research",
    ).to_dict()

    assert payload["subagent"] == "research"
    assert payload["label"] == "查询数据"


def test_supervisor_reasoning_and_chunk_events_keep_normalized_shape():
    reasoning = SupervisorReasoningEvent(content="分析用户意图...").to_dict()
    chunk = SupervisorChunkEvent(content="上海").to_dict()

    assert reasoning == {"type": "reasoning", "content": "分析用户意图..."}
    assert chunk == {"type": "chunk", "content": "上海"}


def test_supervisor_tool_events_keep_runtime_progress_payload():
    tool_start = SupervisorToolStartEvent(tool="search_cities", progress=55).to_dict()
    tool_end = SupervisorToolEndEvent(tool="search_cities", result="ok", progress=55).to_dict()

    assert tool_start == {"type": "tool_start", "tool": "search_cities", "progress": 55}
    assert tool_end == {
        "type": "tool_end",
        "tool": "search_cities",
        "result": "ok",
        "progress": 55,
    }


def test_supervisor_done_event_keeps_terminal_fields_stable():
    payload = SupervisorDoneEvent(
        answer="done",
        tools_used=["search_cities"],
        session_id="session-1",
        run_id="run-1",
        plan_id="plan-1",
        intent="itinerary",
        execution_stats={"steps": []},
        verification_passed=True,
        stale_result_count=0,
        fallback_steps=1,
    ).to_dict()

    assert payload == {
        "type": "done",
        "answer": "done",
        "tools_used": ["search_cities"],
        "session_id": "session-1",
        "run_id": "run-1",
        "plan_id": "plan-1",
        "intent": "itinerary",
        "execution_stats": {"steps": []},
        "verification_passed": True,
        "stale_result_count": 0,
        "fallback_steps": 1,
    }
