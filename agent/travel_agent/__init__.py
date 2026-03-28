"""Core agent runtime package with graph, supervisor, skills, and app-facing runtime."""

from __future__ import annotations

from typing import Any

__all__ = ["AgentRuntime"]


def __getattr__(name: str) -> Any:
    """Lazily expose runtime entrypoints without importing LangChain on package import."""

    if name == "AgentRuntime":
        from .runtime import AgentRuntime

        return AgentRuntime
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
