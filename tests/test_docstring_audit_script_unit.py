"""Unit tests for docstring audit coverage and low-information rules."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.docstring_audit import (
    LowInfoDocstring,
    collect_low_info_docstrings,
    collect_missing_docstrings,
    load_low_info_baseline,
    write_low_info_baseline,
)


def test_collect_missing_docstrings_reports_functions_without_docstrings(tmp_path: Path):
    file_path = tmp_path / "sample_missing.py"
    file_path.write_text(
        "def missing_docstring():\n"
        "    return 1\n",
        encoding="utf-8",
    )

    findings = collect_missing_docstrings(file_path)

    assert any(item.kind == "module" and item.symbol == "<module>" for item in findings)
    assert any(item.kind == "function" and item.symbol == "missing_docstring" for item in findings)


def test_collect_low_info_docstrings_detects_template_docstrings(tmp_path: Path):
    file_path = tmp_path / "sample_low_info.py"
    file_path.write_text(
        '"""Module summary."""\n\n'
        "def low_info(name: str) -> str:\n"
        '    """Template docstring.\n\n'
        "    Purpose:\n"
        "        Explain how this routine updates graph state, tool execution flow, and downstream decision logic.\n\n"
        "    Args:\n"
        "        name: Input field `name` used for normalization or matching rules.\n\n"
        "    Returns:\n"
        "        Normalized text string used by downstream logic.\n"
        '    """\n'
        "    return name\n",
        encoding="utf-8",
    )

    findings = collect_low_info_docstrings(file_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.symbol == "low_info"
    assert "template_purpose" in finding.reasons
    assert "placeholder_return" in finding.reasons


def test_low_info_baseline_round_trip_uses_issue_keys(tmp_path: Path):
    baseline_path = tmp_path / "docstring-baseline.json"
    findings = [
        LowInfoDocstring(
            kind="function",
            file_path="agent/example.py",
            line=12,
            symbol="example",
            reasons=("placeholder_return", "template_purpose"),
        )
    ]

    written_path = write_low_info_baseline(baseline_path, findings)
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    loaded = load_low_info_baseline(written_path)

    assert written_path == baseline_path
    assert payload["finding_count"] == 1
    assert findings[0].issue_key in payload["findings"]
    assert findings[0].issue_key in loaded
