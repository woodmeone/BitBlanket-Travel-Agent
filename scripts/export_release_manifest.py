"""Export release manifest describing app versions, build context, and image coordinates."""
# ruff: noqa: E402

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

if __package__:
    _bootstrap_paths = importlib.import_module(f"{__package__}.bootstrap_paths")
else:
    _bootstrap_paths_path = Path(__file__).with_name("bootstrap_paths.py")
    _bootstrap_paths_spec = importlib.util.spec_from_file_location("bootstrap_paths", _bootstrap_paths_path)
    if _bootstrap_paths_spec is None or _bootstrap_paths_spec.loader is None:
        raise ImportError(f"Unable to load bootstrap_paths from {_bootstrap_paths_path}")
    _bootstrap_paths = importlib.util.module_from_spec(_bootstrap_paths_spec)
    _bootstrap_paths_spec.loader.exec_module(_bootstrap_paths)

ROOT = _bootstrap_paths.PROJECT_ROOT
ensure_project_paths = _bootstrap_paths.ensure_project_paths
ensure_project_paths()

from moyuan_web.app_meta import APP_NAME, APP_VERSION
from scripts.runtime_ops_contracts import (
    ReleaseApplicationEntry,
    ReleaseManifest,
    ReleaseManifestQuality,
    ReleaseManifestSource,
    ReleaseQualityArtifacts,
)


DEFAULT_OUTPUT = ROOT / "artifacts" / "release" / "release-manifest.json"

QUALITY_ARTIFACTS = {
    "benchmark_report": "docs/benchmarks/agent_benchmark_latest.json",
    "golden_eval_report": "docs/benchmarks/agent_golden_eval_latest.json",
    "subagent_scorecard_report": "docs/benchmarks/agent_subagent_scorecard_latest.json",
    "release_harness_scorecard_report": "docs/benchmarks/release_harness_scorecard_latest.json",
    "delivery_snapshot": "frontend/tests/features/trip-plan/__snapshots__/travelPlanDeliverySnapshot.test.ts.snap",
    "skills_catalog": "docs/reference/skills-market-catalog.md",
}


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


def _load_frontend_version(project_root: Path) -> str:
    """Load frontend package version from package.json."""
    package_json = project_root / "frontend" / "package.json"
    payload = json.loads(package_json.read_text(encoding="utf-8"))
    return str(payload.get("version") or "unknown")


def _derive_release_tag(*, git_sha: str, git_ref: str, release_tag: str | None) -> str:
    """Resolve one explicit release tag used by image publication and manifests."""
    normalized = str(release_tag or "").strip()
    if normalized:
        return normalized

    ref_name = str(git_ref or "").strip()
    if ref_name.startswith("refs/tags/"):
        return ref_name.split("/", 2)[-1]
    if ref_name and "/" not in ref_name:
        return ref_name

    short_sha = str(git_sha or "").strip()[:7] or "local"
    return f"sha-{short_sha}"


def export_release_manifest(
    output_path: Path = DEFAULT_OUTPUT,
    *,
    git_sha: str,
    git_ref: str,
    registry: str,
    owner: str,
    release_tag: str | None = None,
) -> Path:
    """Write one release manifest that release workflows can upload and publish."""
    owner = owner.strip().lower()
    registry = registry.rstrip("/")
    resolved_release_tag = _derive_release_tag(git_sha=git_sha, git_ref=git_ref, release_tag=release_tag)
    backend_image = f"{registry}/{owner}/moyuan-travel-agent-backend"
    frontend_image = f"{registry}/{owner}/moyuan-travel-agent-frontend"
    manifest = ReleaseManifest(
        created_at=utc_now_iso(),
        source=ReleaseManifestSource(
            git_sha=git_sha,
            git_ref=git_ref,
        ),
        applications={
            "backend": ReleaseApplicationEntry(
                name=APP_NAME,
                version=APP_VERSION,
                image=backend_image,
                image_tag=resolved_release_tag,
                image_ref=f"{backend_image}:{resolved_release_tag}",
            ),
            "frontend": ReleaseApplicationEntry(
                name="moyuan-travel-agent-frontend",
                version=_load_frontend_version(ROOT),
                image=frontend_image,
                image_tag=resolved_release_tag,
                image_ref=f"{frontend_image}:{resolved_release_tag}",
            ),
        },
        quality=ReleaseManifestQuality(
            release_check_command="python scripts/release_harness_scorecard.py --strict",
            artifacts=ReleaseQualityArtifacts.from_dict(QUALITY_ARTIFACTS),
        ),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def build_parser() -> argparse.ArgumentParser:
    """Construct CLI parser for release manifest export utility."""
    parser = argparse.ArgumentParser(description="Export release manifest for moyuan-travel-agent.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output path for the release manifest.")
    parser.add_argument("--git-sha", required=True, help="Git SHA recorded in the release manifest.")
    parser.add_argument("--git-ref", required=True, help="Git ref or tag recorded in the release manifest.")
    parser.add_argument("--release-tag", default="", help="Explicit image tag recorded in the release manifest.")
    parser.add_argument("--registry", default="ghcr.io", help="Container registry host.")
    parser.add_argument("--owner", required=True, help="Container/image owner or namespace.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for release manifest export."""
    parser = build_parser()
    args = parser.parse_args(argv)
    target = export_release_manifest(
        Path(args.output),
        git_sha=str(args.git_sha),
        git_ref=str(args.git_ref),
        registry=str(args.registry),
        owner=str(args.owner),
        release_tag=str(args.release_tag),
    )
    print(f"Release manifest exported to: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
