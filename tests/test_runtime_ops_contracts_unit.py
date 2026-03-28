"""Unit tests for runtime ops contracts and manifest sections."""

from __future__ import annotations

from scripts.runtime_ops_contracts import (
    RuntimeDoctorReport,
    SupportBundleManifest,
    SupportBundleRuntimeHealthSection,
)


def test_runtime_doctor_report_round_trip_preserves_check_inventory() -> None:
    """Round-trip a loose runtime-doctor payload through the typed report contract."""

    payload = {
        "status": "ok",
        "checked_at": "2026-03-28T00:00:00+00:00",
        "project_root": "D:/demo",
        "summary": {
            "checks_total": 2,
            "checks_ok": 2,
            "checks_degraded": 0,
            "checks_not_ready": 0,
        },
        "checks": {
            "llm_config": {
                "name": "llm_config",
                "status": "ok",
                "message": "LLM config parsed successfully.",
                "details": {"default_model": "demo"},
            },
            "runtime_files": {
                "name": "runtime_files",
                "status": "ok",
                "message": "Discovered 1 runtime file(s).",
                "details": {"files": [{"key": "sessions"}]},
            },
        },
    }

    report = RuntimeDoctorReport.from_dict(payload)

    assert report.status == "ok"
    assert report.summary.checks_total == 2
    assert report.checks["llm_config"].details["default_model"] == "demo"
    assert report.to_dict() == payload


def test_support_bundle_manifest_round_trip_preserves_nested_sections() -> None:
    """Round-trip a support-bundle manifest through the typed nested-section contract."""

    payload = {
        "created_at": "2026-03-28T00:00:00+00:00",
        "project_root": "D:/demo",
        "base_url": "http://localhost:38000",
        "runtime_health": {
            "doctor_status": "ok",
            "runtime_files_count": 3,
            "checks_total": 7,
            "checks_degraded": 0,
            "checks_not_ready": 0,
        },
        "release_evidence": {
            "release_manifest_exists": True,
            "release_manifest_path": "artifacts/release/release-manifest.json",
        },
        "delivery_evidence": {
            "contract_snapshots": ["openapi.snapshot.json", "sse-contract.snapshot.json"],
            "includes_http_snapshot": False,
        },
    }

    manifest = SupportBundleManifest.from_dict(payload)

    assert manifest.runtime_health.runtime_files_count == 3
    assert manifest.release_evidence.release_manifest_exists is True
    assert manifest.delivery_evidence.contract_snapshots == [
        "openapi.snapshot.json",
        "sse-contract.snapshot.json",
    ]
    assert manifest.to_dict() == payload


def test_runtime_health_section_uses_runtime_files_from_doctor_report() -> None:
    """Derive runtime-health manifest counters from the typed doctor report."""

    report = RuntimeDoctorReport.from_dict(
        {
            "status": "degraded",
            "checked_at": "2026-03-28T00:00:00+00:00",
            "project_root": "D:/demo",
            "summary": {
                "checks_total": 4,
                "checks_ok": 2,
                "checks_degraded": 1,
                "checks_not_ready": 1,
            },
            "checks": {
                "runtime_files": {
                    "name": "runtime_files",
                    "status": "ok",
                    "message": "Discovered 2 runtime file(s).",
                    "details": {
                        "files": [
                            {"key": "sessions"},
                            {"key": "share_links"},
                        ]
                    },
                }
            },
        }
    )

    section = SupportBundleRuntimeHealthSection.from_doctor_report(report)

    assert section.doctor_status == "degraded"
    assert section.runtime_files_count == 2
    assert section.checks_degraded == 1
    assert section.checks_not_ready == 1
