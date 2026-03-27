"""Shared bootstrap helpers for project-root and web-package import setup."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = PROJECT_ROOT / "web"


def ensure_project_paths() -> None:
    """Ensure project root and web package paths are importable.

    Keep the repository root importable so package imports like
    `agent.travel_agent...` and `config...` remain stable across entrypoints,
    and keep `web/` importable so direct `moyuan_web...` imports resolve in
    tests and local scripts without per-file `sys.path` patches.
    """
    for path in (str(PROJECT_ROOT), str(WEB_ROOT)):
        if path not in sys.path:
            sys.path.insert(0, path)
