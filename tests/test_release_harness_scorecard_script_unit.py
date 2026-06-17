"""Unit tests for the release harness scorecard export script."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from agent.travel_agent.contracts import (
    SkillContract,
    SkillInputContract,
    SkillMarketMetadata,
    SkillOutputContract,
    SkillSelectionPolicy,
)


def _load_module():
    root = Path(__file__).resolve().parents[1]
    module_path = root / "scripts" / "release_harness_scorecard.py"
    spec = importlib.util.spec_from_file_location("release_harness_scorecard", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _healthy_skill() -> SkillContract:
    return SkillContract(
        name="PlanSynthesisSkill",
        description="Draft itinerary steps.",
        allowed_subagents=["planning"],
        input_contract=SkillInputContract(required_context=["user_intent"]),
        output_contract=SkillOutputContract(artifact="ItineraryDraft", fields=["dailySteps"]),
        market_metadata=SkillMarketMetadata(
            owner="planning-subagent",
            version="2026.03",
            docs_path="docs/reference/skills-market-catalog.md",
            eval_fixture="tests/test_skill_registry_unit.py",
        ),
        selection_policy=SkillSelectionPolicy(
            priority=10,
            intent_signals=["plan"],
            preferred_context=["research_dossier"],
            notes=["Primary planner."],
        ),
    )


def test_release_harness_scorecard_exports_pass_status(tmp_path: Path, monkeypatch):
    module = _load_module()
    golden_path = tmp_path / "golden.json"
    benchmark_path = tmp_path / "benchmark.json"
    subagent_path = tmp_path / "subagent.json"
    delivery_path = tmp_path / "delivery.snap"
    catalog_path = tmp_path / "skills.md"
    output_dir = tmp_path / "out"

    _write_json(golden_path, {"pass_rate": 0.98, "hallucination_rate": 0.0})
    _write_json(
        benchmark_path,
        {
            "aggregate": {
                "avg_success_rate": 0.75,
                "hallucination_rate": 0.0,
                "fallback_steps_total": 2,
            }
        },
    )
    _write_json(
        subagent_path,
        {
            "aggregate": {
                "expected_subagents": ["research", "planning", "budget", "verification"],
                "observed_subagents": ["research", "planning", "budget", "verification"],
                "healthy_subagents": 4,
                "partial_subagents": 0,
                "missing_subagents": 0,
                "mismatch_subagents": 0,
            }
        },
    )
    delivery_path.write_text(
        "\n".join(
            [
                "exports[`travel plan delivery replay snapshot > replays direct mode into stable delivery html 1`] = ``",
                "exports[`travel plan delivery replay snapshot > replays plan mode into stable delivery html 1`] = ``",
                "exports[`travel plan delivery replay snapshot > replays react mode into stable delivery html 1`] = ``",
                "Moyuan Travel Agent",
            ]
        ),
        encoding="utf-8",
    )
    catalog_path.write_text("## 当前 subagent selection policy 基线\n", encoding="utf-8")
    monkeypatch.setattr(module, "_load_default_skills", lambda: [_healthy_skill()])

    scorecard, json_path, markdown_path = module.export_release_harness_scorecard(
        output_dir,
        golden_report=golden_path,
        benchmark_report=benchmark_path,
        subagent_scorecard_report=subagent_path,
        delivery_snapshot=delivery_path,
        skills_catalog=catalog_path,
    )

    assert scorecard["status"] == "pass"
    assert scorecard["summary"] == {"error_count": 0, "warning_count": 0}
    assert json.loads(json_path.read_text(encoding="utf-8"))["delivery"]["modes_covered"] == [
        "direct",
        "plan",
        "react",
    ]
    assert "Release Harness Scorecard" in markdown_path.read_text(encoding="utf-8")


def test_release_harness_scorecard_surfaces_missing_delivery_mode_and_skill_contracts(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    golden_path = tmp_path / "golden.json"
    benchmark_path = tmp_path / "benchmark.json"
    subagent_path = tmp_path / "subagent.json"
    delivery_path = tmp_path / "delivery.snap"
    catalog_path = tmp_path / "skills.md"

    _write_json(golden_path, {"pass_rate": 0.98, "hallucination_rate": 0.0})
    _write_json(
        benchmark_path,
        {
            "aggregate": {
                "avg_success_rate": 0.75,
                "hallucination_rate": 0.0,
                "fallback_steps_total": 2,
            }
        },
    )
    _write_json(
        subagent_path,
        {
            "aggregate": {
                "expected_subagents": ["research", "planning", "budget", "verification"],
                "observed_subagents": ["research", "planning", "verification"],
                "healthy_subagents": 0,
                "partial_subagents": 2,
                "missing_subagents": 1,
                "mismatch_subagents": 1,
            }
        },
    )
    delivery_path.write_text(
        "exports[`travel plan delivery replay snapshot > replays plan mode into stable delivery html 1`] = ``\n",
        encoding="utf-8",
    )
    catalog_path.write_text("## 当前默认 catalog\n", encoding="utf-8")
    monkeypatch.setattr(
        module,
        "_load_default_skills",
        lambda: [
            SkillContract(
                name="TravelTipsSkill",
                description="Tips",
                allowed_subagents=[],
                market_metadata=SkillMarketMetadata(),
                selection_policy=SkillSelectionPolicy(priority=0, intent_signals=[]),
            )
        ],
    )

    scorecard = module.build_release_harness_scorecard(
        golden_report=golden_path,
        benchmark_report=benchmark_path,
        subagent_scorecard_report=subagent_path,
        delivery_snapshot=delivery_path,
        skills_catalog=catalog_path,
    )

    assert scorecard["status"] == "fail"
    messages = [item["message"] for item in scorecard["findings"]]
    assert any("delivery snapshot is missing replay modes" in message for message in messages)
    assert any("selection policy section" in message for message in messages)
    assert any("missing eval_fixture" in message for message in messages)
    assert any("missing a positive selection priority" in message for message in messages)
    assert any("missing subagent(s)" in message for message in messages)
