"""Unit tests for the extracted planning pipeline."""

from __future__ import annotations

import json


from agent.travel_agent.graph.nodes import AgentNodes, PlanStageOutput  # noqa: E402
from agent.travel_agent.graph.runtime_config import get_runtime_config  # noqa: E402
from agent.travel_agent.pipelines import PlanningPipeline  # noqa: E402


def _validate_stage_output(model, payload):
    return model.model_validate(payload).model_dump()


def _build_validation_result(*, tool_name: str, code: str, message: str, timestamp: str):
    return {
        "success": False,
        "tool_name": tool_name,
        "result": "",
        "attempt": 0,
        "error_code": code,
        "error": message,
        "started_at": timestamp,
        "ended_at": timestamp,
    }


def _step_signature(tool_name: str, params: dict[str, object]) -> str:
    return f"{tool_name}:{json.dumps(params, ensure_ascii=False, sort_keys=True)}"


def _build_pipeline(*, tool_names: set[str], planner_hooks):
    return PlanningPipeline(
        runtime_config=get_runtime_config(),
        tool_names=tool_names,
        planner_hooks=planner_hooks,
        stage_output_model=PlanStageOutput,
        validate_stage_output=_validate_stage_output,
        build_execution_summary=AgentNodes._build_execution_summary,
        validation_result_builder=_build_validation_result,
        step_signature=_step_signature,
    )


def test_planning_pipeline_injects_required_tools_without_optional_when_hook_used():
    def itinerary_hook(_entities):
        return [
            {
                "step": 1,
                "step_id": "s1",
                "tool": "query_attractions",
                "params": {"city": "Shanghai"},
                "description": "query pool",
                "depends_on": [],
            }
        ]

    pipeline = _build_pipeline(
        tool_names={"query_attractions", "plan_itinerary", "get_weather"},
        planner_hooks={"itinerary": itinerary_hook},
    )

    result = pipeline.build(
        {
            "intent": "itinerary",
            "intent_detail": {"entities": {"city": "Shanghai", "days": 2}},
            "strategy_detail": {
                "primary_intent": "itinerary",
                "required_tools": ["plan_itinerary"],
                "optional_tools": ["get_weather"],
            },
        }
    )

    assert [step["tool"] for step in result["plan"]] == ["query_attractions", "plan_itinerary"]
    assert result["validation_status"] == "pass"
    assert result["execution_state"]["blocked"] == []


def test_planning_pipeline_marks_unregistered_steps_as_blocked():
    def broken_hook(_entities):
        return [
            {
                "step": 1,
                "step_id": "s1",
                "tool": "not_registered_tool",
                "params": {},
                "description": "broken",
                "depends_on": [],
            }
        ]

    pipeline = _build_pipeline(
        tool_names={"search_cities"},
        planner_hooks={"recommend": broken_hook},
    )

    result = pipeline.build(
        {
            "intent": "recommend",
            "intent_detail": {"entities": {"query": "weekend"}},
            "strategy_detail": {
                "primary_intent": "recommend",
                "required_tools": [],
                "optional_tools": [],
            },
        }
    )

    assert result["validation_status"] == "fail"
    assert result["execution_state"]["blocked"] == ["s1"]
    assert result["tool_results"]["s1:not_registered_tool"]["error_code"] == "TOOL_NOT_REGISTERED"
    assert result["execution_summary"]["blocked_steps"] == 1
