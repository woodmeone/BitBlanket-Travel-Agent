"""Shared script bootstrap helpers for stable repo-root imports."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = PROJECT_ROOT / "web"


def ensure_project_paths() -> None:
    """Expose repo-root and web package imports to script entrypoints."""

    for path in (str(PROJECT_ROOT), str(WEB_ROOT)):
        if path not in sys.path:
            sys.path.insert(0, path)
