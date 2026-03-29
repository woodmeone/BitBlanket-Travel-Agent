"""Unit tests for contract-first runtime event emitters."""

from __future__ import annotations

from agent.travel_agent.runtime_event_emitters import LegacySupervisorEventEmitter


def test_legacy_supervisor_event_emitter_emits_stage_chunk_tool_and_done_payloads():
    """Emitter should produce normalized contract payloads from runtime transitions."""

    emitter = LegacySupervisorEventEmitter(session_id="session-1", run_id="run-1")

    assert emitter.emit_initial() == {
        "type": "stage",
        "stage": "parse",
        "progress": 5,
        "label": "Analyze request",
    }
    assert emitter.emit_node_start("plan") == [
        {
            "type": "stage",
            "stage": "query",
            "progress": 25,
            "label": "Build plan",
            "subagent": "planning",
        },
        {
            "type": "reasoning",
            "content": "Preparing the execution plan...",
        },
    ]
    assert emitter.emit_chat_chunk("hello") == {
        "type": "chunk",
        "content": "hello",
    }
    assert emitter.emit_tool_start("search_cities") == [
        {
            "type": "stage",
            "stage": "query",
            "progress": 30,
            "label": "Query data: search_cities",
        },
        {
            "type": "tool_start",
            "tool": "search_cities",
            "progress": 30,
        },
    ]
    assert emitter.emit_tool_end("search_cities", {"city": "Shanghai"}) == {
        "type": "tool_end",
        "tool": "search_cities",
        "result": "{'city': 'Shanghai'}",
        "progress": 30,
    }

    emitter.record_chain_output(
        {
            "answer": "hello world.",
            "tools_used": ["search_cities"],
            "plan_id": "plan-1",
            "intent": "recommend",
            "execution_stats": {"steps": []},
            "verify_result": {"passed": True},
            "tool_results": {
                "search_cities": {"success": True, "is_stale": True},
            },
        }
    )

    assert emitter.persisted_answer() == "hello world."
    assert emitter.emit_completion_events() == [
        {
            "type": "stage",
            "stage": "finalize",
            "progress": 100,
            "label": "Complete",
        },
        {
            "type": "done",
            "answer": "hello world.",
            "tools_used": ["search_cities"],
            "session_id": "session-1",
            "run_id": "run-1",
            "plan_id": "plan-1",
            "intent": "recommend",
            "execution_stats": {"steps": []},
            "verification_passed": True,
            "stale_result_count": 1,
            "fallback_steps": 0,
        },
    ]


def test_legacy_supervisor_event_emitter_adds_incomplete_answer_fallback():
    """Emitter should patch truncated answers before the done payload is emitted."""

    emitter = LegacySupervisorEventEmitter(session_id="session-2", run_id="run-2")
    emitter.emit_chat_chunk("short")
    completion_events = emitter.emit_completion_events()
    done_event = completion_events[-1]

    assert done_event["type"] == "done"
    assert done_event["answer"].startswith("short ")
    assert "current response may be truncated" in done_event["answer"]
    assert emitter.interrupted_answer() == "[INTERRUPTED]short"
