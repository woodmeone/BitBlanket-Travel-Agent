"""Unit tests for the complexity budget gate script."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import complexity_budget


def test_evaluate_budget_entries_reports_over_budget_file(tmp_path: Path) -> None:
    """Report a violation when a tracked file grows beyond its budget."""

    tracked = tmp_path / "module.py"
    tracked.write_text("a\nb\nc\n", encoding="utf-8")

    entries = [
        complexity_budget.BudgetEntry(
            path="module.py",
            max_lines=2,
            note="test hotspot",
        )
    ]

    violations, summary_lines = complexity_budget.evaluate_budget_entries(tmp_path, entries)

    assert len(violations) == 1
    assert violations[0].kind == "over_budget"
    assert "exceeds max_lines=2" in violations[0].details
    assert summary_lines == ["module.py|current=3|max=2|delta=+1"]


def test_evaluate_budget_entries_reports_missing_tracked_file(tmp_path: Path) -> None:
    """Report a violation when a tracked hotspot disappears from the baseline path."""

    entries = [
        complexity_budget.BudgetEntry(
            path="missing.py",
            max_lines=10,
            note="test hotspot",
        )
    ]

    violations, summary_lines = complexity_budget.evaluate_budget_entries(tmp_path, entries)

    assert summary_lines == []
    assert len(violations) == 1
    assert violations[0].kind == "missing"
    assert violations[0].path == "missing.py"


def test_write_baseline_file_round_trip_preserves_budget_entries(tmp_path: Path) -> None:
    """Persist and reload baseline entries without losing budget metadata."""

    baseline_path = tmp_path / "complexity-budget.json"
    entries = [
        complexity_budget.BudgetEntry(
            path="agent/demo.py",
            max_lines=42,
            note="demo hotspot",
        )
    ]

    complexity_budget.write_baseline_file(baseline_path, entries)
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))

    assert payload["budgets"][0]["path"] == "agent/demo.py"
    assert payload["budgets"][0]["max_lines"] == 42
    assert payload["budgets"][0]["note"] == "demo hotspot"

    round_trip = complexity_budget.load_budget_entries(baseline_path)
    assert round_trip == entries
