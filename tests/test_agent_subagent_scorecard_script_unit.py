"""Unit tests for replay-backed subagent scorecard generation."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def _load_scorecard_module():
    root = Path(__file__).resolve().parents[1]
    module_path = root / "scripts" / "agent_subagent_scorecard.py"
    spec = importlib.util.spec_from_file_location("agent_subagent_scorecard", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_subagent_scorecard_generates_reports_and_surfaces_missing_budget_coverage(tmp_path: Path):
    scorecard = _load_scorecard_module()
    fixture = {
        "modes": {
            "direct": {"key_events": {}},
            "plan": {
                "key_events": {
                    "subagent_starts": [
                        {
                            "subagent": "planning",
                            "skills": ["PlanSynthesisSkill"],
                            "tool_names": ["plan_itinerary"],
                        },
                        {
                            "subagent": "research",
                            "skills": ["CityResearchSkill"],
                            "tool_names": ["search_cities"],
                        },
                        {
                            "subagent": "verification",
                            "skills": ["BudgetAggregationSkill"],
                            "tool_names": [],
                        },
                    ],
                    "subagent_ends": [
                        {"subagent": "planning"},
                        {"subagent": "research"},
                        {"subagent": "verification"},
                    ],
                    "artifact_patches": [
                        {"subagent": "planning"},
                        {"subagent": "verification"},
                    ],
                    "tool_starts": [
                        {"tool": "plan_itinerary"},
                        {"tool": "search_cities"},
                    ],
                    "tool_ends": [
                        {"tool": "plan_itinerary"},
                        {"tool": "search_cities"},
                    ],
                }
            },
            "react": {"key_events": {}},
        }
    }

    report = scorecard.build_subagent_scorecard(fixture)
    json_path, md_path = scorecard.write_report(report, tmp_path)

    budget_row = next(item for item in report["subagents"] if item["subagent"] == "budget")
    verification_row = next(item for item in report["subagents"] if item["subagent"] == "verification")

    assert report["aggregate"]["expected_subagents"] == ["research", "planning", "budget", "verification"]
    assert report["aggregate"]["missing_subagents"] >= 1
    assert budget_row["status"] == "missing"
    assert "fixture coverage missing" in budget_row["issues"]
    assert verification_row["status"] == "mismatch"
    assert any("unexpected skills" in issue for issue in verification_row["issues"])
    assert json_path.exists()
    assert md_path.exists()
    assert "Agent Subagent Scorecard" in md_path.read_text(encoding="utf-8")


def test_generate_scorecard_report_uses_fixture_file(tmp_path: Path):
    scorecard = _load_scorecard_module()
    fixture = {
        "modes": {
            "plan": {
                "key_events": {
                    "subagent_starts": [{"subagent": "planning", "skills": ["PlanSynthesisSkill"]}],
                    "subagent_ends": [{"subagent": "planning"}],
                    "artifact_patches": [{"subagent": "planning"}],
                    "tool_starts": [{"tool": "plan_itinerary"}],
                    "tool_ends": [{"tool": "plan_itinerary"}],
                }
            },
            "react": {"key_events": {}},
        }
    }
    source_path = tmp_path / "fixture.json"
    source_path.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")

    json_path, md_path = scorecard.generate_scorecard_report(source_path, tmp_path)
    report = json.loads(json_path.read_text(encoding="utf-8"))

    assert json_path.exists()
    assert md_path.exists()
    assert report["source_fixture"].endswith("fixture.json")
    assert any(item["subagent"] == "planning" for item in report["subagents"])
