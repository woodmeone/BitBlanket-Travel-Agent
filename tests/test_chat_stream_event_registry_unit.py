"""Unit tests for public chat-stream SSE event registry."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from moyuan_web.api.events import CHAT_STREAM_EVENT_TYPES, validate_chat_stream_payload  # noqa: E402


def test_validate_chat_stream_payload_injects_request_context_ids():
    payload = validate_chat_stream_payload(
        {
            "type": "metadata",
            "run_id": "run-123",
            "total_steps": 1,
            "tools_used": ["search_cities"],
            "has_reasoning": True,
            "reasoning_length": 12,
            "answer_length": 20,
            "execution_stats": {},
            "verification_passed": True,
            "stale_result_count": 0,
            "fallback_steps": 0,
            "failure_clusters": {},
            "artifact": {},
        },
        request_id="req-123",
        trace_id="trace-123",
    )

    assert payload["type"] == "metadata"
    assert payload["request_id"] == "req-123"
    assert payload["trace_id"] == "trace-123"


def test_validate_chat_stream_payload_rejects_unknown_event_type():
    with pytest.raises(ValidationError):
        validate_chat_stream_payload({"type": "reasoning_metadata", "has_reasoning": True})


def test_registered_chat_stream_event_types_cover_public_runtime_events():
    assert "plan_preview" in CHAT_STREAM_EVENT_TYPES
    assert "artifact_patch" in CHAT_STREAM_EVENT_TYPES
    assert "done" in CHAT_STREAM_EVENT_TYPES


def test_validate_chat_stream_payload_normalizes_artifact_aliases():
    payload = validate_chat_stream_payload(
        {
            "type": "artifact_patch",
            "subagent": "planning",
            "artifact_patch": {
                "itinerary": {
                    "plan_id": "plan-123",
                    "validation_status": "warn",
                },
                "budget": {
                    "fallback_steps": 1,
                },
            },
        }
    )

    assert payload["artifact_patch"]["itinerary"]["planId"] == "plan-123"
    assert payload["artifact_patch"]["itinerary"]["validationStatus"] == "warn"
    assert payload["artifact_patch"]["budget"]["fallbackSteps"] == 1


def test_validate_chat_stream_payload_normalizes_execution_receipt_aliases():
    payload = validate_chat_stream_payload(
        {
            "type": "done",
            "run_id": "run-123",
            "artifact": {},
            "execution_receipt": {
                "session_id": "session-123",
                "run_id": "run-123",
                "chat_mode": "plan",
                "subagent_order": ["planning"],
                "tools_used": ["plan_itinerary"],
                "artifact_patch_subagents": ["planning"],
                "segments": [
                    {
                        "subagent": "planning",
                        "sequence": 1,
                        "tool_names": ["plan_itinerary"],
                        "tools_used": ["plan_itinerary"],
                        "artifact_patch_sections": ["itinerary"],
                    }
                ],
            },
        }
    )

    assert payload["execution_receipt"]["sessionId"] == "session-123"
    assert payload["execution_receipt"]["subagentOrder"] == ["planning"]
    assert payload["execution_receipt"]["segments"][0]["toolNames"] == ["plan_itinerary"]
    assert payload["execution_receipt"]["segments"][0]["artifactPatchSections"] == ["itinerary"]
