"""Unit tests for the extracted verification pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

from langchain_core.messages import HumanMessage


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.travel_agent.graph.nodes import VerifyIssue, VerifyResult, VerifyStageOutput  # noqa: E402
from agent.travel_agent.graph.runtime_config import get_runtime_config  # noqa: E402
from agent.travel_agent.pipelines import VerificationPipeline  # noqa: E402


def _validate_stage_output(model, payload):
    return model.model_validate(payload).model_dump()


def _last_user_text(state):
    messages = list(state.get("messages", []) or [])
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return str(message.content or "").strip()
    return ""


def _is_high_risk_query(text: str, intent: str) -> bool:
    return str(intent or "").lower() == "budget" or "价格" in str(text or "")


def _build_pipeline():
    return VerificationPipeline(
        runtime_config=get_runtime_config(),
        refreshable_tools={"get_weather", "query_hotels"},
        stage_output_model=VerifyStageOutput,
        issue_model=VerifyIssue,
        result_model=VerifyResult,
        validate_stage_output=_validate_stage_output,
        last_user_text=_last_user_text,
        is_high_risk_query=_is_high_risk_query,
    )


def test_verification_pipeline_requests_retry_for_missing_required_tools():
    pipeline = _build_pipeline()

    result = pipeline.build(
        {
            "intent": "budget",
            "messages": [HumanMessage(content="给我北京三天预算价格")],
            "verify_retry_count": 0,
            "strategy_detail": {
                "requires_verification": True,
                "required_tools": ["calculate_budget"],
            },
            "tool_results": {
                "s1:query_attractions": {
                    "success": True,
                    "tool_name": "query_attractions",
                    "is_stale": False,
                }
            },
        }
    )

    verify = result["verify_result"]
    issue_types = {item["issue_type"] for item in verify["issues"]}
    assert verify["passed"] is False
    assert verify["should_retry"] is True
    assert result["verify_retry_count"] == 1
    assert "required_tools_missing" in issue_types


def test_verification_pipeline_degrades_after_stale_refresh_failure():
    pipeline = _build_pipeline()

    result = pipeline.build(
        {
            "intent": "general",
            "messages": [HumanMessage(content="请给我北京天气")],
            "verify_retry_count": 1,
            "strategy_detail": {
                "requires_verification": False,
                "required_tools": [],
            },
            "tool_results": {
                "s1:get_weather": {
                    "success": True,
                    "tool_name": "get_weather",
                    "is_stale": True,
                    "fetched_at": "2026-03-26T00:00:00+00:00",
                }
            },
        }
    )

    verify = result["verify_result"]
    issue_types = {item["issue_type"] for item in verify["issues"]}
    assert verify["passed"] is False
    assert verify["should_retry"] is False
    assert result["verify_retry_count"] == 1
    assert "stale_refresh_failed" in issue_types
