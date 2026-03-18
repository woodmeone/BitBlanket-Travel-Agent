"""Base classes for minimal supervisor subagents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from ..contracts import SkillContract


@dataclass(slots=True)
class BaseSubagent:
    """Base object representing one domain-focused subagent."""

    name: str
    description: str
    skills: list[SkillContract] = field(default_factory=list)

    def skill_names(self) -> list[str]:
        """Return skill names owned by this subagent."""
        return [skill.name for skill in self.skills]

    def tool_names(self) -> list[str]:
        """Return tool names reachable through owned skills."""
        seen: list[str] = []
        for skill in self.skills:
            for tool_name in skill.tool_names:
                if tool_name not in seen:
                    seen.append(tool_name)
        return seen

    def start_event(
        self,
        *,
        session_id: str,
        run_id: Optional[str],
        sequence: int,
        trigger: str,
        chat_mode: Optional[str],
    ) -> dict[str, Any]:
        """Return a normalized subagent start event payload."""
        return {
            "type": "subagent_start",
            "subagent": self.name,
            "description": self.description,
            "skills": self.skill_names(),
            "tool_names": self.tool_names(),
            "session_id": session_id,
            "run_id": run_id,
            "sequence": sequence,
            "trigger": trigger,
            "chat_mode": chat_mode,
        }

    def end_event(
        self,
        *,
        session_id: str,
        run_id: Optional[str],
        sequence: int,
        status: str = "completed",
        summary: str = "",
    ) -> dict[str, Any]:
        """Return a normalized subagent end event payload."""
        return {
            "type": "subagent_end",
            "subagent": self.name,
            "session_id": session_id,
            "run_id": run_id,
            "sequence": sequence,
            "status": status,
            "summary": summary,
        }

    def artifact_patch_from_preview(self, preview: dict[str, Any]) -> dict[str, Any]:
        """Build a partial artifact patch from a plan preview payload."""
        _ = preview
        return {}

    def artifact_patch_from_done(
        self,
        done_event: dict[str, Any],
        *,
        user_message: str,
        session_id: str,
        chat_mode: Optional[str],
    ) -> dict[str, Any]:
        """Build a partial artifact patch from the final done event."""
        _ = (done_event, user_message, session_id, chat_mode)
        return {}
