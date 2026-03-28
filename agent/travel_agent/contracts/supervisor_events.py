"""Contracts describing normalized legacy supervisor runtime events."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(slots=True)
class SupervisorStageEvent:
    """Describe one normalized stage update emitted by the legacy supervisor path."""

    stage: str
    progress: int
    label: str
    subagent: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Return the SSE-ready stage payload while omitting empty optional fields."""
        payload = {
            "type": "stage",
            "stage": self.stage,
            "progress": self.progress,
            "label": self.label,
        }
        if self.subagent:
            payload["subagent"] = self.subagent
        return payload


@dataclass(slots=True)
class SupervisorReasoningEvent:
    """Describe one reasoning breadcrumb emitted by the legacy supervisor path."""

    content: str

    def to_dict(self) -> dict[str, str]:
        """Return the normalized reasoning payload."""
        return {
            "type": "reasoning",
            "content": self.content,
        }


@dataclass(slots=True)
class SupervisorChunkEvent:
    """Describe one answer chunk emitted by the legacy supervisor path."""

    content: str

    def to_dict(self) -> dict[str, str]:
        """Return the normalized answer chunk payload."""
        return {
            "type": "chunk",
            "content": self.content,
        }


@dataclass(slots=True)
class SupervisorToolStartEvent:
    """Describe one normalized tool-start update emitted by the legacy supervisor path."""

    tool: str
    progress: int

    def to_dict(self) -> dict[str, Any]:
        """Return the normalized tool-start payload."""
        return {
            "type": "tool_start",
            "tool": self.tool,
            "progress": self.progress,
        }


@dataclass(slots=True)
class SupervisorToolEndEvent:
    """Describe one normalized tool-end update emitted by the legacy supervisor path."""

    tool: str
    result: str
    progress: int

    def to_dict(self) -> dict[str, Any]:
        """Return the normalized tool-end payload."""
        return {
            "type": "tool_end",
            "tool": self.tool,
            "result": self.result,
            "progress": self.progress,
        }


@dataclass(slots=True)
class SupervisorDoneEvent:
    """Describe the terminal normalized payload emitted by the legacy supervisor path."""

    answer: str
    tools_used: list[str] = field(default_factory=list)
    session_id: str = "default"
    run_id: Optional[str] = None
    plan_id: Optional[str] = None
    intent: Optional[str] = None
    execution_stats: dict[str, Any] = field(default_factory=dict)
    verification_passed: Optional[bool] = None
    stale_result_count: int = 0
    fallback_steps: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Return the normalized terminal payload consumed by the runtime seam."""
        return {
            "type": "done",
            "answer": self.answer,
            "tools_used": list(self.tools_used),
            "session_id": self.session_id,
            "run_id": self.run_id,
            "plan_id": self.plan_id,
            "intent": self.intent,
            "execution_stats": dict(self.execution_stats),
            "verification_passed": self.verification_passed,
            "stale_result_count": self.stale_result_count,
            "fallback_steps": self.fallback_steps,
        }
