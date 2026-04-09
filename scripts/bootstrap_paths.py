"""Shared script bootstrap helpers for stable repo-root imports."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"


def ensure_project_paths() -> None:
    """Expose repo-root and backend package imports to script entrypoints."""

    for path in (str(PROJECT_ROOT), str(BACKEND_ROOT)):
        if path not in sys.path:
            sys.path.insert(0, path)
