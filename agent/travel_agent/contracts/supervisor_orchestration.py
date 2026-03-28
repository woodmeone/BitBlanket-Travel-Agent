"""Contracts that describe supervisor runtime requests, preview results, health diagnostics, and shared execution context."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from langchain_core.runnables import Runnable
from langchain_core.tools import Tool


@dataclass(slots=True)
class SupervisorRuntimeContext:
    """Carry shared runtime dependencies used by the supervisor compatibility bridge."""

    llm: Runnable
    tools: list[Tool]
    memory_manager: Any = None
    routing_llm: Optional[Runnable] = None


@dataclass(slots=True)
class SupervisorRunRequest:
    """Describe one streaming supervisor run requested by the application layer."""

    user_message: str
    session_id: str = "default"
    system_prompt: Optional[str] = None
    persist_memory: bool = True
    run_id: Optional[str] = None
    chat_mode: Optional[str] = None

    def resolved_system_prompt(self, default: str) -> str:
        """Return the effective system prompt for this runtime request."""
        return self.system_prompt or default


@dataclass(slots=True)
class SupervisorPlanPreviewRequest:
    """Describe one supervisor plan-preview request issued through the runtime seam."""

    user_message: str
    session_id: str = "default"
    system_prompt: Optional[str] = None
    chat_mode: Optional[str] = None

    def resolved_system_prompt(self, default: str) -> str:
        """Return the effective system prompt for this preview request."""
        return self.system_prompt or default


@dataclass(slots=True)
class SupervisorPlanPreview:
    """Describe the normalized legacy plan-preview payload used by the runtime seam."""

    plan_id: Optional[str] = None
    intent: Optional[str] = None
    intent_detail: dict[str, Any] = field(default_factory=dict)
    plan_explanation: str = ""
    validation_status: str = "pass"
    validation_errors: list[Any] = field(default_factory=list)
    plan: list[Any] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SupervisorPlanPreview":
        """Build one preview contract from a legacy dictionary payload."""
        preview = dict(payload) if isinstance(payload, dict) else {}
        return cls(
            plan_id=_coerce_optional_text(preview.get("plan_id")),
            intent=_coerce_optional_text(preview.get("intent")),
            intent_detail=_copy_dict(preview.get("intent_detail")),
            plan_explanation=_coerce_text(preview.get("plan_explanation")),
            validation_status=_coerce_text(preview.get("validation_status"), "pass"),
            validation_errors=_copy_list(preview.get("validation_errors")),
            plan=_copy_list(preview.get("plan")),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable preview payload for downstream runtime consumers."""
        return {
            "plan_id": self.plan_id,
            "intent": self.intent,
            "intent_detail": _copy_dict(self.intent_detail),
            "plan_explanation": self.plan_explanation,
            "validation_status": self.validation_status,
            "validation_errors": _copy_list(self.validation_errors),
            "plan": _copy_list(self.plan),
        }


@dataclass(slots=True)
class SupervisorToolHealthEntry:
    """Describe one normalized tool-health snapshot inside the legacy runtime seam."""

    consecutive_failures: int = 0
    open_until: float = 0.0
    is_circuit_open: bool = False
    cooldown_remaining_seconds: int = 0

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SupervisorToolHealthEntry":
        """Build one tool-health entry from a loose monitoring dictionary."""
        item = dict(payload) if isinstance(payload, dict) else {}
        return cls(
            consecutive_failures=_coerce_int(item.get("consecutive_failures")),
            open_until=_coerce_float(item.get("open_until")),
            is_circuit_open=bool(item.get("is_circuit_open")),
            cooldown_remaining_seconds=_coerce_int(item.get("cooldown_remaining_seconds")),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-serializable tool-health snapshot."""
        return {
            "consecutive_failures": self.consecutive_failures,
            "open_until": self.open_until,
            "is_circuit_open": self.is_circuit_open,
            "cooldown_remaining_seconds": self.cooldown_remaining_seconds,
        }


@dataclass(slots=True)
class SupervisorToolHealthDiagnostics:
    """Describe the normalized tool-health diagnostics returned by the legacy runtime seam."""

    runtime_config: dict[str, Any] = field(default_factory=dict)
    tool_count: int = 0
    open_circuit_count: int = 0
    tools: dict[str, SupervisorToolHealthEntry] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SupervisorToolHealthDiagnostics":
        """Build one diagnostics contract from a legacy monitoring dictionary."""
        diagnostics = dict(payload) if isinstance(payload, dict) else {}
        raw_tools = diagnostics.get("tools")
        tools = {
            str(name): SupervisorToolHealthEntry.from_dict(item)
            for name, item in dict(raw_tools).items()
        } if isinstance(raw_tools, dict) else {}
        return cls(
            runtime_config=_copy_dict(diagnostics.get("runtime_config")),
            tool_count=_coerce_int(diagnostics.get("tool_count")),
            open_circuit_count=_coerce_int(diagnostics.get("open_circuit_count")),
            tools=tools,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-serializable diagnostics payload for higher-level runtime layers."""
        return {
            "runtime_config": _copy_dict(self.runtime_config),
            "tool_count": self.tool_count,
            "open_circuit_count": self.open_circuit_count,
            "tools": {
                name: item.to_dict() for name, item in self.tools.items()
            },
        }


def _coerce_text(value: Any, default: str = "") -> str:
    """Normalize an optional runtime value into text."""
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _coerce_optional_text(value: Any) -> str | None:
    """Normalize an optional runtime value into text or ``None``."""
    text = _coerce_text(value)
    return text or None


def _coerce_int(value: Any, default: int = 0) -> int:
    """Normalize a loose numeric value into an integer."""
    try:
        return int(value)
    except Exception:
        return default


def _coerce_float(value: Any, default: float = 0.0) -> float:
    """Normalize a loose numeric value into a float."""
    try:
        return float(value)
    except Exception:
        return default


def _copy_dict(value: Any) -> dict[str, Any]:
    """Return a shallow builtin-dict copy for loose preview payloads."""
    return dict(value) if isinstance(value, dict) else {}


def _copy_list(value: Any) -> list[Any]:
    """Return a shallow builtin-list copy for loose preview payloads."""
    return list(value) if isinstance(value, list) else []
