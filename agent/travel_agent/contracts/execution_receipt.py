"""Execution receipt contracts summarizing one multi-subagent runtime run."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(slots=True)
class ExecutionReceiptStage:
    """Describe one observed stage routed through a subagent segment."""

    stage: Optional[str] = None
    label: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable stage snapshot."""
        return {
            "stage": self.stage,
            "label": self.label,
        }


@dataclass(slots=True)
class SubagentExecutionReceipt:
    """Summarize one subagent segment within a supervisor run."""

    subagent: str
    sequence: int
    trigger: Optional[str] = None
    description: Optional[str] = None
    skills: list[str] = field(default_factory=list)
    tool_names: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    stages: list[ExecutionReceiptStage] = field(default_factory=list)
    artifact_patch_sections: list[str] = field(default_factory=list)
    status: str = "running"
    summary: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable receipt segment."""
        return {
            "subagent": self.subagent,
            "sequence": self.sequence,
            "trigger": self.trigger,
            "description": self.description,
            "skills": list(self.skills),
            "toolNames": list(self.tool_names),
            "toolsUsed": list(self.tools_used),
            "stages": [stage.to_dict() for stage in self.stages],
            "artifactPatchSections": list(self.artifact_patch_sections),
            "status": self.status,
            "summary": self.summary,
        }


@dataclass(slots=True)
class ExecutionReceipt:
    """Top-level execution summary returned at the end of one runtime run."""

    session_id: str
    run_id: Optional[str] = None
    chat_mode: Optional[str] = None
    subagent_order: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    artifact_patch_subagents: list[str] = field(default_factory=list)
    segments: list[SubagentExecutionReceipt] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable execution receipt."""
        return {
            "sessionId": self.session_id,
            "runId": self.run_id,
            "chatMode": self.chat_mode,
            "subagentOrder": list(self.subagent_order),
            "toolsUsed": list(self.tools_used),
            "artifactPatchSubagents": list(self.artifact_patch_subagents),
            "segments": [segment.to_dict() for segment in self.segments],
        }
