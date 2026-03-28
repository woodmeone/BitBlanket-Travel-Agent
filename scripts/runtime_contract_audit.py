"""Audit the typed runtime seam that decouples AgentRuntime from the legacy graph."""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent

CONTRACT_PATH = ROOT / "agent" / "travel_agent" / "contracts" / "supervisor_orchestration.py"
LEGACY_BRIDGE_PATH = ROOT / "agent" / "travel_agent" / "runtime" / "legacy_bridge.py"
LEGACY_RUNTIME_PATH = ROOT / "agent" / "travel_agent" / "graph" / "legacy_runtime.py"
AGENT_RUNTIME_PATH = ROOT / "agent" / "travel_agent" / "runtime" / "agent_runtime.py"

REQUIRED_CONTRACTS = (
    "SupervisorRuntimeContext",
    "SupervisorRunRequest",
    "SupervisorPlanPreviewRequest",
    "SupervisorPlanPreview",
    "SupervisorToolHealthEntry",
    "SupervisorToolHealthDiagnostics",
)


@dataclass(frozen=True)
class RuntimeContractAuditFinding:
    """Describe one runtime-seam governance finding."""

    path: str
    symbol: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        """Return one JSON-serializable finding payload."""

        return {
            "path": self.path,
            "symbol": self.symbol,
            "detail": self.detail,
        }


def _repo_relative(path: Path) -> str:
    """Return one repository-relative path for reporting."""

    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _load_module_ast(path: Path) -> ast.Module:
    """Parse one Python source file into an AST module."""

    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _annotation_text(node: ast.AST | None) -> str:
    """Return a normalized string representation for one annotation node."""

    if node is None:
        return ""
    return ast.unparse(node).replace(" ", "")


def _find_class(module: ast.Module, name: str) -> ast.ClassDef | None:
    """Return the class definition with the requested name, when present."""

    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    return None


def _find_function(
    module: ast.Module,
    name: str,
    *,
    class_name: str | None = None,
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """Return one module-level function or class method definition."""

    if class_name:
        class_def = _find_class(module, class_name)
        if class_def is None:
            return None
        nodes = class_def.body
    else:
        nodes = module.body
    for node in nodes:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def _find_kwonly_annotation(
    function_node: ast.FunctionDef | ast.AsyncFunctionDef | None,
    arg_name: str,
) -> str:
    """Return the annotation text for one keyword-only function argument."""

    if function_node is None:
        return ""
    for argument in function_node.args.kwonlyargs:
        if argument.arg == arg_name:
            return _annotation_text(argument.annotation)
    return ""


def _add_missing_function_finding(
    findings: list[RuntimeContractAuditFinding],
    path: Path,
    *,
    symbol: str,
    detail: str,
) -> None:
    """Record one missing-function finding with consistent formatting."""

    findings.append(
        RuntimeContractAuditFinding(
            path=_repo_relative(path),
            symbol=symbol,
            detail=detail,
        )
    )


def audit_contract_module(path: Path) -> list[RuntimeContractAuditFinding]:
    """Audit whether the supervisor orchestration contract exports the typed seam."""

    module = _load_module_ast(path)
    findings: list[RuntimeContractAuditFinding] = []
    present_classes = {
        node.name for node in module.body if isinstance(node, ast.ClassDef)
    }

    for contract_name in REQUIRED_CONTRACTS:
        if contract_name not in present_classes:
            findings.append(
                RuntimeContractAuditFinding(
                    path=_repo_relative(path),
                    symbol=contract_name,
                    detail="missing required runtime contract",
                )
            )

    return findings


def audit_legacy_bridge_module(path: Path) -> list[RuntimeContractAuditFinding]:
    """Audit the runtime bridge annotations and shim entrypoint usage."""

    module = _load_module_ast(path)
    source = path.read_text(encoding="utf-8")
    findings: list[RuntimeContractAuditFinding] = []

    for class_name in ("LegacyRuntimeBridge", "DefaultLegacyRuntimeBridge"):
        stream_with_memory = _find_function(module, "stream_with_memory", class_name=class_name)
        if stream_with_memory is None:
            _add_missing_function_finding(
                findings,
                path,
                symbol=f"{class_name}.stream_with_memory",
                detail="missing bridge streaming entrypoint",
            )
        else:
            request_annotation = _find_kwonly_annotation(stream_with_memory, "request")
            context_annotation = _find_kwonly_annotation(stream_with_memory, "context")
            if request_annotation != "SupervisorRunRequest":
                findings.append(
                    RuntimeContractAuditFinding(
                        path=_repo_relative(path),
                        symbol=f"{class_name}.stream_with_memory.request",
                        detail="expected SupervisorRunRequest annotation",
                    )
                )
            if context_annotation != "SupervisorRuntimeContext":
                findings.append(
                    RuntimeContractAuditFinding(
                        path=_repo_relative(path),
                        symbol=f"{class_name}.stream_with_memory.context",
                        detail="expected SupervisorRuntimeContext annotation",
                    )
                )

        preview_function = _find_function(
            module,
            "generate_plan_preview_with_memory",
            class_name=class_name,
        )
        if preview_function is None:
            _add_missing_function_finding(
                findings,
                path,
                symbol=f"{class_name}.generate_plan_preview_with_memory",
                detail="missing bridge preview entrypoint",
            )
        else:
            request_annotation = _find_kwonly_annotation(preview_function, "request")
            context_annotation = _find_kwonly_annotation(preview_function, "context")
            return_annotation = _annotation_text(preview_function.returns)
            if request_annotation != "SupervisorPlanPreviewRequest":
                findings.append(
                    RuntimeContractAuditFinding(
                        path=_repo_relative(path),
                        symbol=f"{class_name}.generate_plan_preview_with_memory.request",
                        detail="expected SupervisorPlanPreviewRequest annotation",
                    )
                )
            if context_annotation != "SupervisorRuntimeContext":
                findings.append(
                    RuntimeContractAuditFinding(
                        path=_repo_relative(path),
                        symbol=f"{class_name}.generate_plan_preview_with_memory.context",
                        detail="expected SupervisorRuntimeContext annotation",
                    )
                )
            if return_annotation != "SupervisorPlanPreview":
                findings.append(
                    RuntimeContractAuditFinding(
                        path=_repo_relative(path),
                        symbol=f"{class_name}.generate_plan_preview_with_memory",
                        detail="expected SupervisorPlanPreview return annotation",
                    )
                )

        diagnostics_function = _find_function(
            module,
            "get_tool_health_diagnostics",
            class_name=class_name,
        )
        if diagnostics_function is None:
            _add_missing_function_finding(
                findings,
                path,
                symbol=f"{class_name}.get_tool_health_diagnostics",
                detail="missing bridge diagnostics entrypoint",
            )
        else:
            return_annotation = _annotation_text(diagnostics_function.returns)
            if return_annotation != "SupervisorToolHealthDiagnostics":
                findings.append(
                    RuntimeContractAuditFinding(
                        path=_repo_relative(path),
                        symbol=f"{class_name}.get_tool_health_diagnostics",
                        detail="expected SupervisorToolHealthDiagnostics return annotation",
                    )
                )

    if "from ..graph.builder import" in source or "..graph.builder" in source:
        findings.append(
            RuntimeContractAuditFinding(
                path=_repo_relative(path),
                symbol="DefaultLegacyRuntimeBridge",
                detail="legacy bridge must not import graph.builder directly",
            )
        )

    required_shims = (
        "stream_supervisor_run",
        "generate_supervisor_plan_preview",
        "collect_supervisor_tool_health_diagnostics",
    )
    for shim_name in required_shims:
        if shim_name not in source:
            findings.append(
                RuntimeContractAuditFinding(
                    path=_repo_relative(path),
                    symbol=shim_name,
                    detail="missing typed legacy runtime shim reference",
                )
            )

    return findings


def audit_legacy_runtime_module(path: Path) -> list[RuntimeContractAuditFinding]:
    """Audit the legacy runtime shim annotations and exported entrypoints."""

    module = _load_module_ast(path)
    findings: list[RuntimeContractAuditFinding] = []

    stream_function = _find_function(module, "stream_supervisor_run")
    if stream_function is None:
        _add_missing_function_finding(
            findings,
            path,
            symbol="stream_supervisor_run",
            detail="missing supervisor streaming shim",
        )
    else:
        if _find_kwonly_annotation(stream_function, "request") != "SupervisorRunRequest":
            findings.append(
                RuntimeContractAuditFinding(
                    path=_repo_relative(path),
                    symbol="stream_supervisor_run.request",
                    detail="expected SupervisorRunRequest annotation",
                )
            )
        if _find_kwonly_annotation(stream_function, "context") != "SupervisorRuntimeContext":
            findings.append(
                RuntimeContractAuditFinding(
                    path=_repo_relative(path),
                    symbol="stream_supervisor_run.context",
                    detail="expected SupervisorRuntimeContext annotation",
                )
            )

    preview_function = _find_function(module, "generate_supervisor_plan_preview")
    if preview_function is None:
        _add_missing_function_finding(
            findings,
            path,
            symbol="generate_supervisor_plan_preview",
            detail="missing supervisor preview shim",
        )
    else:
        if _find_kwonly_annotation(preview_function, "request") != "SupervisorPlanPreviewRequest":
            findings.append(
                RuntimeContractAuditFinding(
                    path=_repo_relative(path),
                    symbol="generate_supervisor_plan_preview.request",
                    detail="expected SupervisorPlanPreviewRequest annotation",
                )
            )
        if _find_kwonly_annotation(preview_function, "context") != "SupervisorRuntimeContext":
            findings.append(
                RuntimeContractAuditFinding(
                    path=_repo_relative(path),
                    symbol="generate_supervisor_plan_preview.context",
                    detail="expected SupervisorRuntimeContext annotation",
                )
            )
        if _annotation_text(preview_function.returns) != "SupervisorPlanPreview":
            findings.append(
                RuntimeContractAuditFinding(
                    path=_repo_relative(path),
                    symbol="generate_supervisor_plan_preview",
                    detail="expected SupervisorPlanPreview return annotation",
                )
            )

    diagnostics_function = _find_function(module, "collect_supervisor_tool_health_diagnostics")
    if diagnostics_function is None:
        _add_missing_function_finding(
            findings,
            path,
            symbol="collect_supervisor_tool_health_diagnostics",
            detail="missing supervisor diagnostics shim",
        )
    else:
        if _annotation_text(diagnostics_function.returns) != "SupervisorToolHealthDiagnostics":
            findings.append(
                RuntimeContractAuditFinding(
                    path=_repo_relative(path),
                    symbol="collect_supervisor_tool_health_diagnostics",
                    detail="expected SupervisorToolHealthDiagnostics return annotation",
                )
            )

    return findings


def audit_agent_runtime_module(path: Path) -> list[RuntimeContractAuditFinding]:
    """Audit that AgentRuntime consumes the typed bridge seam instead of legacy entrypoints."""

    source = path.read_text(encoding="utf-8")
    findings: list[RuntimeContractAuditFinding] = []

    required_contracts = (
        "SupervisorRunRequest",
        "SupervisorPlanPreviewRequest",
        "SupervisorRuntimeContext",
        "SupervisorPlanPreview",
        "SupervisorToolHealthDiagnostics",
    )
    for contract_name in required_contracts:
        if contract_name not in source:
            findings.append(
                RuntimeContractAuditFinding(
                    path=_repo_relative(path),
                    symbol=contract_name,
                    detail="agent runtime is missing a required typed seam reference",
                )
            )

    forbidden_legacy_references = (
        "run_travel_agent_streaming_with_memory",
        "from ..graph.builder import",
        "from ..graph.legacy_runtime import",
    )
    for token in forbidden_legacy_references:
        if token in source:
            findings.append(
                RuntimeContractAuditFinding(
                    path=_repo_relative(path),
                    symbol="AgentRuntime",
                    detail=f"must not reference legacy runtime token `{token}` directly",
                )
            )

    if "DefaultLegacyRuntimeBridge" not in source or "LegacyRuntimeBridge" not in source:
        findings.append(
            RuntimeContractAuditFinding(
                path=_repo_relative(path),
                symbol="AgentRuntime",
                detail="agent runtime must depend on the explicit legacy bridge seam",
            )
        )

    return findings


def build_runtime_contract_audit_report(root: Path = ROOT) -> dict[str, Any]:
    """Audit the typed runtime seam and return a structured report."""

    files = {
        _repo_relative(CONTRACT_PATH): audit_contract_module(CONTRACT_PATH),
        _repo_relative(LEGACY_BRIDGE_PATH): audit_legacy_bridge_module(LEGACY_BRIDGE_PATH),
        _repo_relative(LEGACY_RUNTIME_PATH): audit_legacy_runtime_module(LEGACY_RUNTIME_PATH),
        _repo_relative(AGENT_RUNTIME_PATH): audit_agent_runtime_module(AGENT_RUNTIME_PATH),
    }
    findings = [
        finding.to_dict()
        for file_findings in files.values()
        for finding in file_findings
    ]
    return {
        "audited_files": list(files.keys()),
        "finding_count": len(findings),
        "findings": findings,
    }


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for the runtime contract audit."""

    parser = argparse.ArgumentParser(
        description=(
            "Audit the typed runtime seam that isolates AgentRuntime from the legacy graph."
        )
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when any runtime seam finding is discovered.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the runtime contract audit CLI."""

    parser = build_parser()
    args = parser.parse_args(argv)
    report = build_runtime_contract_audit_report()
    print(f"audited_files={len(report['audited_files'])}")
    print(f"findings={report['finding_count']}")
    if report["findings"]:
        print("sample_findings:")
        for finding in report["findings"][:20]:
            print(f"{finding['path']}|{finding['symbol']}|{finding['detail']}")
    if args.strict and report["findings"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
