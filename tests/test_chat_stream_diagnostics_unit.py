"""Unit tests for persisted chat stream diagnostics helpers."""

from __future__ import annotations

import pytest

import moyuan_web.observability as observability  # noqa: E402
from moyuan_web.services.chat.stream_diagnostics import ChatStreamDiagnostics  # noqa: E402


class _StateStub:
    def __init__(self) -> None:
        self.tools_used = ["search_city"]
        self.verification_passed = True
        self.stale_result_count = 0
        self.fallback_steps = 1
        self.plan_id = "plan-123"
        self.execution_stats = {"latencyMs": 1200}
        self.final_artifact = {"itinerary": {"plan_id": "plan-123"}}
        self.subagent_events = [{"subagent": "planning", "status": "completed"}]
        self.run_id = "run-123"

    def resolved_session_id(self) -> str:
        return "session-123"


@pytest.mark.parametrize("builder_name", ["build_success_diagnostics", "build_failure_diagnostics"])
def test_chat_stream_diagnostics_include_session_id(monkeypatch: pytest.MonkeyPatch, builder_name: str) -> None:
    monkeypatch.setattr(
        observability,
        "get_request_context",
        lambda: {"request_id": "request-123", "trace_id": "trace-123"},
    )

    diagnostics = getattr(ChatStreamDiagnostics(), builder_name)(_StateStub())

    assert diagnostics["sessionId"] == "session-123"
    assert diagnostics["runId"] == "run-123"
    assert diagnostics["requestId"] == "request-123"
    assert diagnostics["traceId"] == "trace-123"
