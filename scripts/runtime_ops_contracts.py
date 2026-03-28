"""Shared contracts for runtime diagnostics, support bundles, and ops snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _coerce_text(value: Any, default: str = "") -> str:
    """Return one normalized text value."""

    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _copy_dict(value: Any) -> dict[str, Any]:
    """Return one shallow builtin dict copy."""

    return dict(value) if isinstance(value, dict) else {}


def _copy_str_list(value: Any) -> list[str]:
    """Return one normalized list of strings."""

    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


@dataclass(slots=True)
class RuntimeDoctorCheck:
    """Describe one normalized runtime-doctor check."""

    name: str
    status: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RuntimeDoctorCheck":
        """Build one check contract from a loose dictionary payload."""

        item = dict(payload) if isinstance(payload, dict) else {}
        return cls(
            name=_coerce_text(item.get("name")),
            status=_coerce_text(item.get("status")),
            message=_coerce_text(item.get("message")),
            details=_copy_dict(item.get("details")),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return one JSON-serializable check payload."""

        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "details": _copy_dict(self.details),
        }


@dataclass(slots=True)
class RuntimeDoctorSummary:
    """Describe aggregate runtime-doctor status counters."""

    checks_total: int = 0
    checks_ok: int = 0
    checks_degraded: int = 0
    checks_not_ready: int = 0

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RuntimeDoctorSummary":
        """Build one summary contract from a loose dictionary payload."""

        item = dict(payload) if isinstance(payload, dict) else {}
        return cls(
            checks_total=int(item.get("checks_total", 0) or 0),
            checks_ok=int(item.get("checks_ok", 0) or 0),
            checks_degraded=int(item.get("checks_degraded", 0) or 0),
            checks_not_ready=int(item.get("checks_not_ready", 0) or 0),
        )

    def to_dict(self) -> dict[str, int]:
        """Return one JSON-serializable summary payload."""

        return {
            "checks_total": self.checks_total,
            "checks_ok": self.checks_ok,
            "checks_degraded": self.checks_degraded,
            "checks_not_ready": self.checks_not_ready,
        }


@dataclass(slots=True)
class RuntimeDoctorReport:
    """Describe the full runtime-doctor report contract."""

    status: str
    checked_at: str
    project_root: str
    summary: RuntimeDoctorSummary
    checks: dict[str, RuntimeDoctorCheck] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RuntimeDoctorReport":
        """Build one report contract from a loose runtime-doctor payload."""

        item = dict(payload) if isinstance(payload, dict) else {}
        raw_checks = item.get("checks")
        checks = (
            {
                str(name): RuntimeDoctorCheck.from_dict(check_payload)
                for name, check_payload in dict(raw_checks).items()
            }
            if isinstance(raw_checks, dict)
            else {}
        )
        return cls(
            status=_coerce_text(item.get("status")),
            checked_at=_coerce_text(item.get("checked_at")),
            project_root=_coerce_text(item.get("project_root")),
            summary=RuntimeDoctorSummary.from_dict(_copy_dict(item.get("summary"))),
            checks=checks,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return one JSON-serializable runtime-doctor report payload."""

        return {
            "status": self.status,
            "checked_at": self.checked_at,
            "project_root": self.project_root,
            "summary": self.summary.to_dict(),
            "checks": {
                name: check.to_dict() for name, check in self.checks.items()
            },
        }


@dataclass(slots=True)
class SupportBundleRuntimeHealthSection:
    """Describe runtime-health evidence embedded in the support-bundle manifest."""

    doctor_status: str
    runtime_files_count: int
    checks_total: int
    checks_degraded: int
    checks_not_ready: int

    @classmethod
    def from_doctor_report(cls, report: RuntimeDoctorReport) -> "SupportBundleRuntimeHealthSection":
        """Build runtime-health evidence from one runtime-doctor report."""

        runtime_files = report.checks.get("runtime_files")
        details = runtime_files.details if runtime_files else {}
        files = details.get("files")
        runtime_files_count = len(files) if isinstance(files, list) else 0
        return cls(
            doctor_status=report.status,
            runtime_files_count=runtime_files_count,
            checks_total=report.summary.checks_total,
            checks_degraded=report.summary.checks_degraded,
            checks_not_ready=report.summary.checks_not_ready,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return one JSON-serializable runtime-health manifest section."""

        return {
            "doctor_status": self.doctor_status,
            "runtime_files_count": self.runtime_files_count,
            "checks_total": self.checks_total,
            "checks_degraded": self.checks_degraded,
            "checks_not_ready": self.checks_not_ready,
        }


@dataclass(slots=True)
class SupportBundleReleaseEvidenceSection:
    """Describe release-evidence entries embedded in the support-bundle manifest."""

    release_manifest_exists: bool
    release_manifest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return one JSON-serializable release-evidence manifest section."""

        return {
            "release_manifest_exists": self.release_manifest_exists,
            "release_manifest_path": self.release_manifest_path,
        }


@dataclass(slots=True)
class SupportBundleDeliveryEvidenceSection:
    """Describe delivery-evidence entries embedded in the support-bundle manifest."""

    contract_snapshots: list[str] = field(default_factory=list)
    includes_http_snapshot: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Return one JSON-serializable delivery-evidence manifest section."""

        return {
            "contract_snapshots": list(self.contract_snapshots),
            "includes_http_snapshot": self.includes_http_snapshot,
        }


@dataclass(slots=True)
class SupportBundleManifest:
    """Describe the support-bundle manifest contract."""

    created_at: str
    project_root: str
    base_url: str | None
    runtime_health: SupportBundleRuntimeHealthSection
    release_evidence: SupportBundleReleaseEvidenceSection
    delivery_evidence: SupportBundleDeliveryEvidenceSection

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SupportBundleManifest":
        """Build one support-bundle manifest contract from a loose payload."""

        item = dict(payload) if isinstance(payload, dict) else {}
        runtime_health = _copy_dict(item.get("runtime_health"))
        release_evidence = _copy_dict(item.get("release_evidence"))
        delivery_evidence = _copy_dict(item.get("delivery_evidence"))
        return cls(
            created_at=_coerce_text(item.get("created_at")),
            project_root=_coerce_text(item.get("project_root")),
            base_url=_coerce_text(item.get("base_url")) or None,
            runtime_health=SupportBundleRuntimeHealthSection(
                doctor_status=_coerce_text(runtime_health.get("doctor_status")),
                runtime_files_count=int(runtime_health.get("runtime_files_count", 0) or 0),
                checks_total=int(runtime_health.get("checks_total", 0) or 0),
                checks_degraded=int(runtime_health.get("checks_degraded", 0) or 0),
                checks_not_ready=int(runtime_health.get("checks_not_ready", 0) or 0),
            ),
            release_evidence=SupportBundleReleaseEvidenceSection(
                release_manifest_exists=bool(release_evidence.get("release_manifest_exists")),
                release_manifest_path=_coerce_text(release_evidence.get("release_manifest_path")) or None,
            ),
            delivery_evidence=SupportBundleDeliveryEvidenceSection(
                contract_snapshots=_copy_str_list(delivery_evidence.get("contract_snapshots")),
                includes_http_snapshot=bool(delivery_evidence.get("includes_http_snapshot")),
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return one JSON-serializable support-bundle manifest payload."""

        return {
            "created_at": self.created_at,
            "project_root": self.project_root,
            "base_url": self.base_url,
            "runtime_health": self.runtime_health.to_dict(),
            "release_evidence": self.release_evidence.to_dict(),
            "delivery_evidence": self.delivery_evidence.to_dict(),
        }


def build_runtime_doctor_contract_snapshot() -> dict[str, Any]:
    """Return a stable snapshot payload that documents the runtime-doctor contract shape."""

    report = RuntimeDoctorReport(
        status="ok",
        checked_at="<iso8601-utc>",
        project_root="<project_root>",
        summary=RuntimeDoctorSummary(
            checks_total=7,
            checks_ok=7,
            checks_degraded=0,
            checks_not_ready=0,
        ),
        checks={
            "server_config": RuntimeDoctorCheck(
                name="server_config",
                status="ok",
                message="Server config parsed successfully.",
                details={
                    "path": "<project_root>/config/server_config.yaml",
                    "exists": True,
                    "web_host": "0.0.0.0",
                    "web_port": 38000,
                    "frontend_port": 33001,
                    "metrics_enabled": True,
                    "metrics_path": "/api/metrics",
                },
            ),
            "llm_config": RuntimeDoctorCheck(
                name="llm_config",
                status="ok",
                message="LLM config parsed successfully.",
                details={
                    "path": "<project_root>/config/llm_config.yaml",
                    "exists": True,
                    "default_model": "<default_model>",
                    "active_models": ["<default_model>"],
                    "models_count": 1,
                },
            ),
            "data_dir": RuntimeDoctorCheck(
                name="data_dir",
                status="ok",
                message="Runtime data directory is writable.",
                details={"path": "<project_root>/data"},
            ),
            "runtime_files": RuntimeDoctorCheck(
                name="runtime_files",
                status="ok",
                message="Discovered 2 runtime file(s).",
                details={
                    "files": [
                        {"key": "sessions", "relative_path": "data/sessions/sessions.json", "size_bytes": 1024},
                        {"key": "share_links", "relative_path": "data/share_links.json", "size_bytes": 256},
                    ]
                },
            ),
            "backups": RuntimeDoctorCheck(
                name="backups",
                status="ok",
                message="Runtime backup inventory loaded.",
                details={
                    "path": "<project_root>/artifacts/runtime_backups",
                    "archive_count": 1,
                    "latest_archive": "<project_root>/artifacts/runtime_backups/runtime_backup_example.zip",
                },
            ),
            "contract_snapshots": RuntimeDoctorCheck(
                name="contract_snapshots",
                status="ok",
                message="Contract snapshots validated.",
                details={
                    "snapshots": {
                        "openapi": {
                            "name": "openapi_snapshot",
                            "status": "ok",
                            "message": "Snapshot file loaded.",
                            "details": {
                                "exists": True,
                                "path": "<project_root>/docs/reference/openapi.snapshot.json",
                                "root_type": "dict",
                                "top_level_keys": ["components", "info", "openapi", "paths", "servers"],
                            },
                        },
                        "sse": {
                            "name": "sse_snapshot",
                            "status": "ok",
                            "message": "Snapshot file loaded.",
                            "details": {
                                "exists": True,
                                "path": "<project_root>/docs/reference/sse-contract.snapshot.json",
                                "root_type": "dict",
                                "top_level_keys": ["endpoint", "modes", "registered_event_types", "schema_version"],
                            },
                        },
                    }
                },
            ),
            "http_probe": RuntimeDoctorCheck(
                name="http_probe",
                status="ok",
                message="Live HTTP probes passed.",
                details={
                    "base_url": "http://localhost:38000",
                    "endpoints": {
                        "health": {
                            "name": "health",
                            "status": "ok",
                            "message": "HTTP 200",
                            "details": {
                                "url": "http://localhost:38000/api/health",
                                "status_code": 200,
                                "content_type": "application/json",
                            },
                        },
                        "ready": {
                            "name": "ready",
                            "status": "ok",
                            "message": "HTTP 200",
                            "details": {
                                "url": "http://localhost:38000/api/ready",
                                "status_code": 200,
                                "content_type": "application/json",
                            },
                        },
                        "metrics": {
                            "name": "metrics",
                            "status": "ok",
                            "message": "HTTP 200",
                            "details": {
                                "url": "http://localhost:38000/api/metrics",
                                "status_code": 200,
                                "content_type": "text/plain; version=0.0.4",
                            },
                        },
                    },
                },
            ),
        },
    )
    return report.to_dict()
