#!/usr/bin/env python3
"""Track line-count budgets for complexity hotspots.

Usage:
    python scripts/complexity_budget.py
    python scripts/complexity_budget.py --strict
    python scripts/complexity_budget.py --write-baseline
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


DEFAULT_BASELINE_PATH = Path("docs/reference/complexity-budget.json")


@dataclass(frozen=True)
class BudgetTarget:
    """Describe a tracked hotspot file and why it is gated."""

    path: str
    note: str


@dataclass(frozen=True)
class BudgetEntry:
    """Persist a maximum line budget for one tracked file."""

    path: str
    max_lines: int
    note: str


@dataclass(frozen=True)
class BudgetViolation:
    """Represent one complexity gate violation."""

    kind: str
    path: str
    details: str


DEFAULT_TARGETS: tuple[BudgetTarget, ...] = (
    BudgetTarget("agent/travel_agent/graph/nodes.py", "legacy graph execution hotspot"),
    BudgetTarget(
        "agent/travel_agent/graph/memory_integration.py",
        "legacy memory orchestration hotspot",
    ),
    BudgetTarget("agent/travel_agent/graph/builder.py", "runtime graph assembly hotspot"),
    BudgetTarget("agent/travel_agent/tools/travel_api.py", "large external travel provider adapter"),
    BudgetTarget("agent/travel_agent/tools/travel_tools.py", "large tool aggregation module"),
    BudgetTarget(
        "agent/travel_agent/memory/conflict_resolution.py",
        "memory conflict clarification helper",
    ),
    BudgetTarget("agent/travel_agent/pipelines/planning.py", "planning pipeline hotspot"),
    BudgetTarget(
        "backend/moyuan_web/services/chat/stream_mixin.py",
        "chat streaming orchestration hotspot",
    ),
    BudgetTarget("backend/moyuan_web/routes/api_docs.py", "API docs presentation route"),
    BudgetTarget("frontend/src/utils/travelPlan.ts", "trip-plan shared transformation helper"),
    BudgetTarget(
        "frontend/src/components/chat-area/useChatRuntime.ts",
        "chat runtime orchestration hotspot",
    ),
    BudgetTarget("frontend/src/components/TravelPlanToolkit.tsx", "trip-plan workspace shell"),
)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for baseline management and strict gating."""

    parser = argparse.ArgumentParser(
        description="Audit hotspot files against line-count complexity budgets."
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=DEFAULT_BASELINE_PATH,
        help="Path to the JSON baseline file.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when tracked files exceed budgets or baseline entries go stale.",
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Write a fresh baseline from the default tracked hotspots.",
    )
    parser.add_argument(
        "--max-output",
        type=int,
        default=20,
        help="Maximum number of sample findings to print.",
    )
    return parser.parse_args()


def repo_root() -> Path:
    """Return the repository root based on the script location."""

    return Path(__file__).resolve().parent.parent


def count_lines(path: Path) -> int:
    """Count logical lines in a UTF-8 source file."""

    return len(path.read_text(encoding="utf-8").splitlines())


def build_default_budget_entries(root: Path) -> list[BudgetEntry]:
    """Build baseline entries from the current tracked hotspot files."""

    entries: list[BudgetEntry] = []
    for target in DEFAULT_TARGETS:
        absolute_path = root / target.path
        if not absolute_path.exists():
            raise FileNotFoundError(f"Tracked hotspot file not found: {target.path}")
        entries.append(
            BudgetEntry(
                path=target.path,
                max_lines=count_lines(absolute_path),
                note=target.note,
            )
        )
    return entries


def write_baseline_file(baseline_path: Path, entries: Iterable[BudgetEntry]) -> None:
    """Write the baseline file with tracked budgets."""

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "description": (
            "Line-count budgets for curated complexity hotspots. "
            "Strict mode fails if tracked files grow beyond these maxima "
            "or if baseline entries go stale."
        ),
        "budgets": [asdict(entry) for entry in entries],
    }
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_budget_entries(baseline_path: Path) -> list[BudgetEntry]:
    """Load tracked budgets from a JSON baseline file."""

    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    budgets = payload.get("budgets", [])
    return [BudgetEntry(**budget) for budget in budgets]


def evaluate_budget_entries(root: Path, entries: Iterable[BudgetEntry]) -> tuple[list[BudgetViolation], list[str]]:
    """Evaluate tracked files and return violations plus summary lines."""

    violations: list[BudgetViolation] = []
    summary_lines: list[str] = []
    for entry in entries:
        absolute_path = root / entry.path
        if not absolute_path.exists():
            violations.append(
                BudgetViolation(
                    kind="missing",
                    path=entry.path,
                    details="tracked file is missing; update the complexity baseline",
                )
            )
            continue

        current_lines = count_lines(absolute_path)
        delta = current_lines - entry.max_lines
        summary_lines.append(
            f"{entry.path}|current={current_lines}|max={entry.max_lines}|delta={delta:+d}"
        )
        if current_lines > entry.max_lines:
            violations.append(
                BudgetViolation(
                    kind="over_budget",
                    path=entry.path,
                    details=(
                        f"current_lines={current_lines} exceeds max_lines={entry.max_lines} "
                        f"by {delta}"
                    ),
                )
            )

    return violations, sorted(
        summary_lines,
        key=lambda line: int(line.split("|current=")[1].split("|", 1)[0]),
        reverse=True,
    )


def main() -> int:
    """Run baseline export or strict complexity gating."""

    args = parse_args()
    root = repo_root()
    baseline_path = args.baseline if args.baseline.is_absolute() else root / args.baseline

    if args.write_baseline:
        entries = build_default_budget_entries(root)
        write_baseline_file(baseline_path, entries)
        print(f"baseline_written={baseline_path.as_posix()}")
        print(f"tracked_files={len(entries)}")
        return 0

    if not baseline_path.exists():
        print(
            f"Missing baseline: {baseline_path.as_posix()}. "
            "Run with --write-baseline to create it.",
            file=sys.stderr,
        )
        return 1

    entries = load_budget_entries(baseline_path)
    violations, summary_lines = evaluate_budget_entries(root, entries)
    print(f"tracked_files={len(entries)}")
    print(f"violations={len(violations)}")
    if summary_lines:
        print("largest_tracked_files:")
        for line in summary_lines[: args.max_output]:
            print(line)

    if violations:
        print("sample_findings:")
        for violation in violations[: args.max_output]:
            print(f"{violation.kind}|{violation.path}|{violation.details}")

    if args.strict and violations:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
