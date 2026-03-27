"""Build replay-backed scorecards for supervisor subagent collaboration coverage."""

from __future__ import annotations

import argparse
import importlib.util
import json
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__:
    from .bootstrap_paths import PROJECT_ROOT as ROOT, ensure_project_paths
else:  # pragma: no cover - direct script execution / spec-loaded module path
    _bootstrap_path = Path(__file__).with_name("bootstrap_paths.py")
    _bootstrap_spec = importlib.util.spec_from_file_location("scripts.bootstrap_paths", _bootstrap_path)
    if _bootstrap_spec is None or _bootstrap_spec.loader is None:
        raise ImportError(f"Cannot load bootstrap helper from {_bootstrap_path}")
    _bootstrap_module = importlib.util.module_from_spec(_bootstrap_spec)
    _bootstrap_spec.loader.exec_module(_bootstrap_module)
    ROOT = _bootstrap_module.PROJECT_ROOT
    ensure_project_paths = _bootstrap_module.ensure_project_paths

ensure_project_paths()

warnings.filterwarnings(
    "ignore",
    message="Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater.",
    category=UserWarning,
)

from agent.travel_agent.skills import build_default_skill_registry
from agent.travel_agent.subagents import build_default_subagent_registry

DEFAULT_FIXTURE = ROOT / "tests" / "golden" / "chat_stream_golden_fixture.json"
DEFAULT_OUTPUT_DIR = ROOT / "docs" / "benchmarks"
EVAL_MODES = ("plan", "react")


def _repo_relative_text(path: Path) -> str:
    """Return a repo-relative POSIX path when possible for stable reports."""
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _event_array(key_events: dict[str, Any], key: str) -> list[dict[str, Any]]:
    """Return one key-event payload as a normalized list of records."""
    value = key_events.get(key)
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def _safe_str(value: Any) -> str:
    """Normalize possibly-empty scalar values into trimmed strings."""
    return str(value).strip() if value is not None else ""


def _seed_subagent_summary(name: str, expected_skills: list[str], expected_tools: list[str]) -> dict[str, Any]:
    """Create the mutable aggregation bucket for one expected subagent."""
    return {
        "subagent": name,
        "expected_skills": list(expected_skills),
        "expected_tools": list(expected_tools),
        "observed_skills": set(),
        "observed_tools": set(),
        "modes_seen": set(),
        "start_count": 0,
        "end_count": 0,
        "artifact_patch_count": 0,
        "tool_event_count": 0,
        "issues": [],
    }


def build_subagent_scorecard(source_fixture: dict[str, Any]) -> dict[str, Any]:
    """Aggregate replay fixture data into a per-subagent coverage scorecard."""
    skill_registry = build_default_skill_registry()
    subagent_registry = build_default_subagent_registry(skill_registry)
    expected_subagents = subagent_registry.names()
    summary_by_subagent = {
        name: _seed_subagent_summary(
            name,
            subagent_registry.skill_names(name),
            subagent_registry.get(name).tool_names() if subagent_registry.get(name) is not None else [],
        )
        for name in expected_subagents
    }
    mode_rows: list[dict[str, Any]] = []

    for mode_name in source_fixture.get("modes", {}):
        mode_fixture = source_fixture["modes"][mode_name]
        key_events = mode_fixture.get("key_events", {}) if isinstance(mode_fixture, dict) else {}
        starts = _event_array(key_events, "subagent_starts")
        ends = _event_array(key_events, "subagent_ends")
        patches = _event_array(key_events, "artifact_patches")
        tool_starts = _event_array(key_events, "tool_starts")
        tool_ends = _event_array(key_events, "tool_ends")

        observed_subagents: list[str] = []
        for event in starts:
            subagent = _safe_str(event.get("subagent"))
            if not subagent:
                continue
            observed_subagents.append(subagent)
            if subagent not in summary_by_subagent:
                summary_by_subagent[subagent] = _seed_subagent_summary(subagent, [], [])
            summary = summary_by_subagent[subagent]
            summary["start_count"] += 1
            summary["modes_seen"].add(mode_name)
            summary["observed_skills"].update(
                skill for skill in event.get("skills", []) if isinstance(skill, str) and skill.strip()
            )
            summary["observed_tools"].update(
                tool_name
                for tool_name in event.get("tool_names", [])
                if isinstance(tool_name, str) and tool_name.strip()
            )

        for event in ends:
            subagent = _safe_str(event.get("subagent"))
            if not subagent:
                continue
            if subagent not in summary_by_subagent:
                summary_by_subagent[subagent] = _seed_subagent_summary(subagent, [], [])
            summary_by_subagent[subagent]["end_count"] += 1
            summary_by_subagent[subagent]["modes_seen"].add(mode_name)

        for event in patches:
            subagent = _safe_str(event.get("subagent"))
            if not subagent:
                continue
            if subagent not in summary_by_subagent:
                summary_by_subagent[subagent] = _seed_subagent_summary(subagent, [], [])
            summary_by_subagent[subagent]["artifact_patch_count"] += 1
            summary_by_subagent[subagent]["modes_seen"].add(mode_name)

        for event in [*tool_starts, *tool_ends]:
            tool_name = _safe_str(event.get("tool"))
            if not tool_name:
                continue
            owner = subagent_registry.resolve_subagent_for_tool(tool_name)
            if owner is None:
                continue
            summary = summary_by_subagent[owner]
            summary["tool_event_count"] += 1
            summary["observed_tools"].add(tool_name)
            summary["modes_seen"].add(mode_name)

        mode_rows.append(
            {
                "mode": mode_name,
                "observed_subagents": list(dict.fromkeys(observed_subagents)),
                "subagent_start_count": len(starts),
                "subagent_end_count": len(ends),
                "artifact_patch_count": len(patches),
                "tool_event_count": len(tool_starts) + len(tool_ends),
            }
        )

    subagent_rows: list[dict[str, Any]] = []
    for name in expected_subagents:
        summary = summary_by_subagent[name]
        expected_skills = set(summary["expected_skills"])
        observed_skills = set(summary["observed_skills"])
        expected_tools = set(summary["expected_tools"])
        observed_tools = set(summary["observed_tools"])
        missing_skills = sorted(expected_skills - observed_skills)
        unexpected_skills = sorted(observed_skills - expected_skills)
        missing_tools = sorted(expected_tools - observed_tools)
        mode_coverage = len(summary["modes_seen"]) / len(EVAL_MODES) if EVAL_MODES else 1.0
        transition_coverage = (
            min(summary["start_count"], summary["end_count"]) / summary["start_count"]
            if summary["start_count"] > 0
            else 0.0
        )
        skill_coverage = len(expected_skills & observed_skills) / len(expected_skills) if expected_skills else 1.0
        tool_coverage = len(expected_tools & observed_tools) / len(expected_tools) if expected_tools else 1.0
        artifact_coverage = 1.0 if summary["artifact_patch_count"] > 0 else 0.0
        coverage_score = round(
            (mode_coverage + transition_coverage + skill_coverage + tool_coverage + artifact_coverage) / 5,
            4,
        )

        issues: list[str] = []
        if not summary["modes_seen"]:
            issues.append("fixture coverage missing")
        if unexpected_skills:
            issues.append(f"unexpected skills: {', '.join(unexpected_skills)}")
        if missing_skills:
            issues.append(f"missing skills: {', '.join(missing_skills)}")
        if missing_tools:
            issues.append(f"missing tools: {', '.join(missing_tools)}")
        if summary["artifact_patch_count"] == 0:
            issues.append("no artifact patch observed")
        if summary["start_count"] != summary["end_count"]:
            issues.append("subagent start/end imbalance")

        if not summary["modes_seen"]:
            status = "missing"
        elif unexpected_skills:
            status = "mismatch"
        elif coverage_score >= 0.8:
            status = "healthy"
        else:
            status = "partial"

        subagent_rows.append(
            {
                "subagent": name,
                "status": status,
                "coverage_score": coverage_score,
                "modes_seen": sorted(summary["modes_seen"]),
                "expected_skills": summary["expected_skills"],
                "observed_skills": sorted(observed_skills),
                "unexpected_skills": unexpected_skills,
                "expected_tools": summary["expected_tools"],
                "observed_tools": sorted(observed_tools),
                "start_count": summary["start_count"],
                "end_count": summary["end_count"],
                "artifact_patch_count": summary["artifact_patch_count"],
                "tool_event_count": summary["tool_event_count"],
                "issues": issues,
            }
        )

    observed_subagents = sorted(
        {
            row["subagent"]
            for row in subagent_rows
            if row["start_count"] > 0 or row["end_count"] > 0 or row["artifact_patch_count"] > 0
        }
    )
    aggregate = {
        "expected_subagents": expected_subagents,
        "observed_subagents": observed_subagents,
        "expected_eval_modes": list(EVAL_MODES),
        "modes_analyzed": [row["mode"] for row in mode_rows],
        "healthy_subagents": sum(1 for row in subagent_rows if row["status"] == "healthy"),
        "missing_subagents": sum(1 for row in subagent_rows if row["status"] == "missing"),
        "mismatch_subagents": sum(1 for row in subagent_rows if row["status"] == "mismatch"),
        "partial_subagents": sum(1 for row in subagent_rows if row["status"] == "partial"),
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_fixture": _repo_relative_text(DEFAULT_FIXTURE),
        "aggregate": aggregate,
        "subagents": subagent_rows,
        "modes": mode_rows,
    }


def write_report(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    """Persist the subagent scorecard as JSON and Markdown reports."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "agent_subagent_scorecard_latest.json"
    md_path = output_dir / "agent_subagent_scorecard_latest.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    aggregate = report.get("aggregate", {})
    lines = [
        "# Agent Subagent Scorecard",
        "",
        f"- generated_at: {report.get('generated_at')}",
        f"- source_fixture: {report.get('source_fixture')}",
        f"- expected_subagents: {aggregate.get('expected_subagents', [])}",
        f"- observed_subagents: {aggregate.get('observed_subagents', [])}",
        f"- expected_eval_modes: {aggregate.get('expected_eval_modes', [])}",
        f"- healthy_subagents: {aggregate.get('healthy_subagents', 0)}",
        f"- partial_subagents: {aggregate.get('partial_subagents', 0)}",
        f"- mismatch_subagents: {aggregate.get('mismatch_subagents', 0)}",
        f"- missing_subagents: {aggregate.get('missing_subagents', 0)}",
        "",
        "## Subagents",
        "",
    ]

    for row in report.get("subagents", []):
        lines.extend(
            [
                f"### {row.get('subagent')}",
                "",
                f"- status: {row.get('status')}",
                f"- coverage_score: {row.get('coverage_score')}",
                f"- modes_seen: {row.get('modes_seen')}",
                f"- expected_skills: {row.get('expected_skills')}",
                f"- observed_skills: {row.get('observed_skills')}",
                f"- expected_tools: {row.get('expected_tools')}",
                f"- observed_tools: {row.get('observed_tools')}",
                f"- start_count: {row.get('start_count')}",
                f"- end_count: {row.get('end_count')}",
                f"- artifact_patch_count: {row.get('artifact_patch_count')}",
                f"- tool_event_count: {row.get('tool_event_count')}",
                f"- issues: {row.get('issues')}",
                "",
            ]
        )

    lines.extend(["## Modes", ""])
    for row in report.get("modes", []):
        lines.append(
            f"- {row.get('mode')}: subagents={row.get('observed_subagents')}, "
            f"starts={row.get('subagent_start_count')}, ends={row.get('subagent_end_count')}, "
            f"artifact_patches={row.get('artifact_patch_count')}, tool_events={row.get('tool_event_count')}"
        )

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def generate_scorecard_report(
    source_path: Path = DEFAULT_FIXTURE,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[Path, Path]:
    """Load the source replay fixture, compute the scorecard, and persist reports."""
    source_fixture = json.loads(source_path.read_text(encoding="utf-8"))
    report = build_subagent_scorecard(source_fixture)
    report["source_fixture"] = _repo_relative_text(source_path)
    return write_report(report, output_dir)


def build_parser() -> argparse.ArgumentParser:
    """Construct the CLI parser for subagent scorecard export."""
    parser = argparse.ArgumentParser(description="Generate replay-backed subagent scorecard reports.")
    parser.add_argument("--source", default=str(DEFAULT_FIXTURE), help="Input chat stream golden fixture path.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for generated reports.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the scorecard CLI and print generated artifact paths."""
    parser = build_parser()
    args = parser.parse_args(argv)
    json_path, md_path = generate_scorecard_report(Path(args.source), Path(args.output_dir))
    print(f"Subagent scorecard JSON report: {json_path}")
    print(f"Subagent scorecard Markdown report: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
