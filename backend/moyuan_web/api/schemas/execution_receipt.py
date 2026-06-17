"""Execution receipt schemas shared by stream and persisted diagnostics payloads."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class _ExecutionReceiptModel(BaseModel):
    """Permissive base model for execution receipt payload validation."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class ExecutionReceiptStage(_ExecutionReceiptModel):
    """One routed stage observation captured within a subagent segment."""

    stage: Optional[str] = None
    label: Optional[str] = None


class SubagentExecutionReceipt(_ExecutionReceiptModel):
    """Summarize one subagent segment within a supervisor run."""

    subagent: str
    sequence: int
    trigger: Optional[str] = None
    description: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    tool_names: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("tool_names", "toolNames"),
        serialization_alias="toolNames",
    )
    tools_used: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("tools_used", "toolsUsed"),
        serialization_alias="toolsUsed",
    )
    stages: list[ExecutionReceiptStage] = Field(default_factory=list)
    artifact_patch_sections: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("artifact_patch_sections", "artifactPatchSections"),
        serialization_alias="artifactPatchSections",
    )
    status: str = "running"
    summary: Optional[str] = None


class ExecutionReceipt(_ExecutionReceiptModel):
    """Top-level execution receipt shared with the public stream contract."""

    session_id: str = Field(
        validation_alias=AliasChoices("session_id", "sessionId"),
        serialization_alias="sessionId",
    )
    run_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("run_id", "runId"),
        serialization_alias="runId",
    )
    chat_mode: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("chat_mode", "chatMode"),
        serialization_alias="chatMode",
    )
    subagent_order: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("subagent_order", "subagentOrder"),
        serialization_alias="subagentOrder",
    )
    tools_used: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("tools_used", "toolsUsed"),
        serialization_alias="toolsUsed",
    )
    artifact_patch_subagents: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("artifact_patch_subagents", "artifactPatchSubagents"),
        serialization_alias="artifactPatchSubagents",
    )
    segments: list[SubagentExecutionReceipt] = Field(default_factory=list)


def normalize_execution_receipt(payload: Any) -> dict[str, Any]:
    """Normalize one execution receipt payload into the public camelCase contract shape."""

    if not isinstance(payload, dict) or not payload:
        return {}
    return ExecutionReceipt.model_validate(payload).model_dump(by_alias=True)
