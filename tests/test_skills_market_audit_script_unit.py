"""Unit tests for the governed skills-market audit script."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from agent.travel_agent.contracts import (
    SkillContract,
    SkillInputContract,
    SkillMarketMetadata,
    SkillOutputContract,
)
from agent.travel_agent.skills import SkillRegistry


def _load_module():
    root = Path(__file__).resolve().parents[1]
    module_path = root / "scripts" / "skills_market_audit.py"
    spec = importlib.util.spec_from_file_location("skills_market_audit", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_default_skills_market_audit_report_has_no_findings():
    """Default governed skill catalog should satisfy the four-piece audit."""

    module = _load_module()

    report = module.build_skills_market_audit_report()

    assert report["audited_skills"] >= 1
    assert report["required_onboarding_requirements"] == ["schema", "tests", "docs", "eval"]
    assert report["findings"] == []


def test_skills_market_audit_reports_missing_governance_requirements(monkeypatch):
    """Audit should report skills that skip tests/docs/eval governance hooks."""

    module = _load_module()
    registry = SkillRegistry(
        [
            SkillContract(
                name="BrokenSkill",
                description="Broken governed skill.",
                allowed_subagents=[],
                input_contract=SkillInputContract(required_context=[]),
                output_contract=SkillOutputContract(artifact=None, fields=[]),
                market_metadata=SkillMarketMetadata(
                    owner="",
                    version="",
                    docs_path=None,
                    test_fixture=None,
                    eval_fixture=None,
                    onboarding_requirements=["schema"],
                ),
                metadata={},
            )
        ]
    )

    monkeypatch.setattr(
        module,
        "build_default_skill_registry",
        lambda: registry,
    )

    report = module.build_skills_market_audit_report()
    messages = [f"{item['field']}|{item['message']}" for item in report["findings"]]

    assert any("market_metadata.onboarding_requirements|missing onboarding requirements: tests, docs, eval" in message for message in messages)
    assert any("market_metadata.test_fixture|missing test_fixture" in message for message in messages)
    assert any("market_metadata.docs_path|missing docs_path" in message for message in messages)
    assert any("market_metadata.eval_fixture|missing eval_fixture" in message for message in messages)
    assert any("metadata.onboarding_doc|missing onboarding_doc pointer" in message for message in messages)
