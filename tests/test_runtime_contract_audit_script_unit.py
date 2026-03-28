"""Unit tests for the runtime contract audit script."""

from __future__ import annotations

from pathlib import Path

from scripts import runtime_contract_audit


def test_build_runtime_contract_audit_report_passes_for_current_repo() -> None:
    """Accept the current repository runtime seam when all contracts are present."""

    report = runtime_contract_audit.build_runtime_contract_audit_report()

    assert report["finding_count"] == 0
    assert len(report["audited_files"]) == 4


def test_audit_legacy_bridge_module_reports_missing_typed_annotations(tmp_path: Path) -> None:
    """Flag bridge methods that drift away from typed supervisor contracts."""

    bridge_path = tmp_path / "legacy_bridge.py"
    bridge_path.write_text(
        "\n".join(
            [
                "from typing import Any, AsyncGenerator, Protocol",
                "",
                "class LegacyRuntimeBridge(Protocol):",
                "    async def stream_with_memory(self, *, request, context) -> AsyncGenerator[dict[str, Any], None]:",
                "        yield {}",
                "",
                "class DefaultLegacyRuntimeBridge:",
                "    async def stream_with_memory(self, *, request, context) -> AsyncGenerator[dict[str, Any], None]:",
                "        yield {}",
                "",
                "    def generate_plan_preview_with_memory(self, *, request, context):",
                "        return {}",
                "",
                "    def get_tool_health_diagnostics(self):",
                "        return {}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    findings = runtime_contract_audit.audit_legacy_bridge_module(bridge_path)
    finding_details = {f"{finding.symbol}|{finding.detail}" for finding in findings}

    assert any(
        detail.endswith("expected SupervisorRunRequest annotation")
        for detail in finding_details
    )
    assert any(
        detail.endswith("expected SupervisorPlanPreview return annotation")
        for detail in finding_details
    )
    assert any(
        detail.endswith("missing typed legacy runtime shim reference")
        for detail in finding_details
    )
