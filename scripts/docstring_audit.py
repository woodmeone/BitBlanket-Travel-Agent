"""Audit Python docstrings for both coverage and information quality.

Usage:
    python scripts/docstring_audit.py
    python scripts/docstring_audit.py --roots agent web scripts --max-output 200
    python scripts/docstring_audit.py --write-baseline
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

DEFAULT_ROOTS = ("agent", "web", "scripts")
DEFAULT_EXCLUDE_DIRS = {".git", ".cache", ".venv", "__pycache__", ".pytest_cache", ".mypy_cache"}
DocumentedNode = ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
DEFAULT_BASELINE_PATH = Path("docs/reference/docstring-audit.low-info-baseline.json")
GENERIC_PURPOSE_SENTENCE = "Explain how this routine updates graph state, tool execution flow, and downstream decision logic."
GENERIC_ARG_RE = re.compile(
    r"^\s*[A-Za-z_][A-Za-z0-9_]*:\s+"
    r"(Input field|Numeric control parameter|Time-related setting|Filesystem/resource path).*$",
    re.MULTILINE,
)
GENERIC_RETURN_RE = re.compile(
    r"^\s*"
    r"(None: No explicit return value; side effects happen in-place\."
    r"|Computed value returned to the caller\."
    r"|Normalized text string used by downstream logic\."
    r"|Runtime-dependent object returned to the calling layer\."
    r"|Boolean outcome flag used by guards or success checks\.)\s*$",
    re.MULTILINE,
)


@dataclass(slots=True)
class MissingDocstring:
    """One missing-docstring finding."""

    kind: str
    file_path: str
    line: int
    symbol: str


@dataclass(slots=True)
class LowInfoDocstring:
    """One low-information docstring finding."""

    kind: str
    file_path: str
    line: int
    symbol: str
    reasons: tuple[str, ...]

    @property
    def issue_key(self) -> str:
        """Build a stable baseline key independent from line-number churn."""

        return f"{self.kind}|{self.file_path}|{self.symbol}|{','.join(self.reasons)}"

    @property
    def reason_label(self) -> str:
        """Return a compact human-readable reason label."""

        return ",".join(self.reasons)


def iter_python_files(roots: Iterable[Path]) -> Iterable[Path]:
    """Yield Python source files under roots while skipping cache/venv folders."""

    for root in roots:
        if not root.exists():
            continue
        for file_path in root.rglob("*.py"):
            if any(part in DEFAULT_EXCLUDE_DIRS for part in file_path.parts):
                continue
            yield file_path


def normalize_path(file_path: Path) -> str:
    """Normalize path separators so findings stay stable across local shells."""

    return file_path.as_posix()


def iter_symbol_nodes(node: ast.AST, parent_qualname: str = "") -> Iterable[tuple[str, DocumentedNode, str]]:
    """Yield class/function nodes with a qualified symbol name."""

    for child in getattr(node, "body", []):
        if isinstance(child, ast.ClassDef):
            qualname = f"{parent_qualname}.{child.name}" if parent_qualname else child.name
            yield ("class", child, qualname)
            yield from iter_symbol_nodes(child, qualname)
        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            qualname = f"{parent_qualname}.{child.name}" if parent_qualname else child.name
            yield ("function", child, qualname)
            yield from iter_symbol_nodes(child, qualname)


def detect_low_info_reasons(docstring: str) -> tuple[str, ...]:
    """Return low-information reasons for one docstring, if any."""

    reasons: list[str] = []
    if GENERIC_PURPOSE_SENTENCE in docstring:
        reasons.append("template_purpose")

    generic_arg_count = len(GENERIC_ARG_RE.findall(docstring))
    generic_return_count = len(GENERIC_RETURN_RE.findall(docstring))

    if generic_arg_count >= 2:
        reasons.append("placeholder_args")
    if generic_return_count >= 1:
        reasons.append("placeholder_return")

    if "Purpose:" in docstring and "template_purpose" in reasons:
        reasons.append("boilerplate_sections")

    if "template_purpose" not in reasons and generic_arg_count == 1 and generic_return_count == 0:
        return ()

    unique = sorted(set(reasons))
    if not unique:
        return ()
    if "template_purpose" in unique:
        return tuple(unique)
    if "placeholder_args" in unique and "placeholder_return" in unique:
        return tuple(unique)
    return ()


def collect_missing_docstrings(file_path: Path) -> list[MissingDocstring]:
    """Collect missing module/class/function docstrings from a single file."""

    source = file_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    normalized_path = normalize_path(file_path)
    missing: list[MissingDocstring] = []

    if ast.get_docstring(tree) is None:
        missing.append(MissingDocstring("module", normalized_path, 1, "<module>"))

    for kind, node, qualname in iter_symbol_nodes(tree):
        if ast.get_docstring(node) is None:
            missing.append(MissingDocstring(kind, normalized_path, int(node.lineno), qualname))

    return missing


def collect_low_info_docstrings(file_path: Path) -> list[LowInfoDocstring]:
    """Collect low-information module/class/function docstrings from a single file."""

    source = file_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    normalized_path = normalize_path(file_path)
    low_info: list[LowInfoDocstring] = []

    module_docstring = ast.get_docstring(tree)
    if module_docstring is not None:
        reasons = detect_low_info_reasons(module_docstring)
        if reasons:
            low_info.append(LowInfoDocstring("module", normalized_path, 1, "<module>", reasons))

    for kind, node, qualname in iter_symbol_nodes(tree):
        docstring = ast.get_docstring(node)
        if docstring is None:
            continue
        reasons = detect_low_info_reasons(docstring)
        if not reasons:
            continue
        low_info.append(LowInfoDocstring(kind, normalized_path, int(node.lineno), qualname, reasons))

    return low_info


def load_low_info_baseline(baseline_path: Path | None) -> set[str]:
    """Load a low-info baseline file if one exists."""

    if baseline_path is None or not baseline_path.exists():
        return set()
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    findings = payload.get("findings", [])
    if not isinstance(findings, list):
        return set()
    return {str(item) for item in findings}


def write_low_info_baseline(baseline_path: Path, findings: Sequence[LowInfoDocstring]) -> Path:
    """Write low-information findings into a baseline snapshot file."""

    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "finding_count": len(findings),
        "findings": sorted(item.issue_key for item in findings),
    }
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return baseline_path


def build_parser() -> argparse.ArgumentParser:
    """Create command-line parser for docstring audit options."""

    parser = argparse.ArgumentParser(description="Audit Python docstring coverage and information quality.")
    parser.add_argument("--roots", nargs="*", default=list(DEFAULT_ROOTS), help="Root directories to scan.")
    parser.add_argument(
        "--max-output",
        type=int,
        default=120,
        help="Maximum number of findings to print.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 when any missing or active low-information docstring is found.",
    )
    parser.add_argument(
        "--baseline",
        default=str(DEFAULT_BASELINE_PATH),
        help="Baseline file used to suppress known low-information findings.",
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Write the current low-information findings into the baseline file and exit.",
    )
    return parser


def main() -> int:
    """Run docstring audit and print a concise report."""

    args = build_parser().parse_args()
    roots = [Path(root) for root in args.roots]
    baseline_path = Path(args.baseline) if args.baseline else None

    missing: list[MissingDocstring] = []
    low_info: list[LowInfoDocstring] = []
    scanned_files = 0

    for file_path in iter_python_files(roots):
        scanned_files += 1
        try:
            missing.extend(collect_missing_docstrings(file_path))
            low_info.extend(collect_low_info_docstrings(file_path))
        except SyntaxError as exc:
            missing.append(MissingDocstring("syntax_error", normalize_path(file_path), int(exc.lineno or 1), exc.msg))
        except UnicodeDecodeError as exc:
            missing.append(MissingDocstring("decode_error", normalize_path(file_path), 1, str(exc)))

    if args.write_baseline and baseline_path is not None:
        written_path = write_low_info_baseline(baseline_path, low_info)
        print(f"baseline_written={written_path.as_posix()}")

    low_info_baseline = load_low_info_baseline(baseline_path)
    active_low_info = [item for item in low_info if item.issue_key not in low_info_baseline]
    baselined_low_info = len(low_info) - len(active_low_info)

    module_missing = sum(1 for item in missing if item.kind == "module")
    class_missing = sum(1 for item in missing if item.kind == "class")
    function_missing = sum(1 for item in missing if item.kind == "function")
    other_missing = len(missing) - module_missing - class_missing - function_missing

    print(f"scanned_files={scanned_files}")
    print(
        "missing_counts "
        f"module={module_missing} class={class_missing} function={function_missing} other={other_missing} total={len(missing)}"
    )
    print(
        "low_info_counts "
        f"total={len(low_info)} baselined={baselined_low_info} active={len(active_low_info)}"
    )

    findings_output: list[str] = []
    findings_output.extend(
        f"{item.kind}|{item.file_path}:{item.line}|{item.symbol}"
        for item in missing
    )
    findings_output.extend(
        f"low_info({item.reason_label})|{item.file_path}:{item.line}|{item.symbol}"
        for item in active_low_info
    )

    if findings_output:
        print("sample_findings:")
        for item in findings_output[: max(0, args.max_output)]:
            print(item)

    if args.strict and (missing or active_low_info):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
