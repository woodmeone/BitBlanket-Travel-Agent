"""Contract-first event emitters used by the legacy supervisor runtime shim."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .contracts import (
    SupervisorChunkEvent,
    SupervisorDoneEvent,
    SupervisorReasoningEvent,
    SupervisorStageEvent,
    SupervisorToolEndEvent,
    SupervisorToolStartEvent,
)

TOOL_RESULT_PREVIEW_LIMIT = 200
_INCOMPLETE_ANSWER_FALLBACK = (
    "The main steps are complete, but the current response may be truncated. "
    "Tell me whether you want me to fill in the budget, itinerary, or hotel details first."
)
_NODE_STAGE_CONFIG: dict[str, dict[str, Any]] = {
    "intent": {
        "stage": "parse",
        "progress": 10,
        "label": "Analyze request",
        "reasoning": "Analyzing user intent...",
    },
    "strategy": {
        "stage": "parse",
        "progress": 18,
        "label": "Select strategy",
        "reasoning": "Selecting the execution strategy...",
    },
    "plan": {
        "stage": "query",
        "progress": 25,
        "label": "Build plan",
        "subagent": "planning",
        "reasoning": "Preparing the execution plan...",
    },
    "react": {
        "stage": "query",
        "progress": 25,
        "label": "Run reactive planner",
        "subagent": "planning",
        "reasoning": "Preparing the reactive tool loop...",
    },
    "execute": {
        "stage": "query",
        "progress": 45,
        "label": "Query data",
        "subagent": "research",
        "reasoning": "Running tools...",
    },
    "answer": {
        "stage": "generate",
        "progress": 80,
        "label": "Draft answer",
    },
    "direct_answer": {
        "stage": "generate",
        "progress": 80,
        "label": "Draft answer",
    },
    "verify": {
        "stage": "generate",
        "progress": 72,
        "label": "Verify results",
        "subagent": "verification",
        "reasoning": "Checking price, policy, and date consistency...",
    },
    "self_check": {
        "stage": "finalize",
        "progress": 95,
        "label": "Self check answer",
    },
}


def _is_answer_complete(answer: str) -> bool:
    """Heuristically detect whether generated answer text appears complete."""

    text = str(answer or "").strip()
    if len(text) < 8:
        return False
    return text[-1] in {".", "!", "?", "\u3002", "\uff01", "\uff1f"}


@dataclass(slots=True)
class LegacySupervisorEventEmitter:
    """Emit normalized supervisor runtime events while tracking stream state."""

    session_id: str = "default"
    run_id: str | None = None
    answer: str = ""
    tools_used: list[str] = field(default_factory=list)
    final_state: dict[str, Any] = field(default_factory=dict)
    stage: str = "parse"
    progress: int = 5

    def emit_initial(self) -> dict[str, Any]:
        """Emit the first stage event for one runtime stream."""

        return SupervisorStageEvent(
            stage=self.stage,
            progress=self.progress,
            label="Analyze request",
        ).to_dict()

    def emit_node_start(self, node_name: str) -> list[dict[str, Any]]:
        """Emit normalized stage/reasoning events for one node transition."""

        config = _NODE_STAGE_CONFIG.get(node_name)
        if not config:
            return []

        self.stage = str(config["stage"])
        self.progress = int(config["progress"])
        events: list[dict[str, Any]] = [
            SupervisorStageEvent(
                stage=self.stage,
                progress=self.progress,
                label=str(config["label"]),
                subagent=config.get("subagent"),
            ).to_dict()
        ]
        reasoning = config.get("reasoning")
        if reasoning:
            events.append(SupervisorReasoningEvent(content=str(reasoning)).to_dict())
        return events

    def emit_chat_chunk(self, content: str) -> dict[str, Any] | None:
        """Emit one normalized answer chunk and retain it for the final payload."""

        if not content:
            return None
        self.answer += content
        return SupervisorChunkEvent(content=content).to_dict()

    def emit_tool_start(self, tool_name: str) -> list[dict[str, Any]]:
        """Emit normalized stage/tool-start updates for one tool invocation."""

        self.tools_used.append(tool_name)
        self.stage = "query"
        self.progress = min(75, self.progress + 5)
        return [
            SupervisorStageEvent(
                stage="query",
                progress=self.progress,
                label=f"Query data: {tool_name}",
            ).to_dict(),
            SupervisorToolStartEvent(tool=tool_name, progress=self.progress).to_dict(),
        ]

    def emit_tool_end(self, tool_name: str, result: Any) -> dict[str, Any]:
        """Emit one normalized tool-end payload."""

        return SupervisorToolEndEvent(
            tool=tool_name,
            result=str(result)[:TOOL_RESULT_PREVIEW_LIMIT],
            progress=self.progress,
        ).to_dict()

    def record_chain_output(self, output: Any) -> None:
        """Capture the final graph state used to assemble the done payload."""

        if isinstance(output, dict) and ("answer" in output or "execution_stats" in output):
            self.final_state = output

    def interrupted_answer(self) -> str:
        """Return the persisted assistant answer used after an interrupted run."""

        return f"[INTERRUPTED]{self.answer}"

    def persisted_answer(self) -> str:
        """Return the assistant answer that should be written into memory."""

        return str(self.final_state.get("answer") or self.answer or "")

    def emit_completion_events(self) -> list[dict[str, Any]]:
        """Emit the terminal stage event plus the normalized done payload."""

        return [
            SupervisorStageEvent(stage="finalize", progress=100, label="Complete").to_dict(),
            self._build_done_event(),
        ]

    def _build_done_event(self) -> dict[str, Any]:
        """Build the terminal normalized payload for one runtime stream."""

        resolved_answer = str(self.final_state.get("answer") or self.answer or "")
        resolved_tools_used = list(self.final_state.get("tools_used") or self.tools_used or [])
        execution_stats = self.final_state.get("execution_stats", {}) or {}
        execution_summary = self.final_state.get("execution_summary", {}) or {}
        verify_result = self.final_state.get("verify_result", {}) or {}
        strategy_detail = self.final_state.get("strategy_detail", {}) or {}
        tool_results = self.final_state.get("tool_results", {}) or {}
        plan_id = self.final_state.get("plan_id")
        intent = self.final_state.get("intent")

        if isinstance(verify_result, dict) and "passed" in verify_result:
            verification_passed = bool(verify_result.get("passed"))
        elif bool(strategy_detail.get("requires_verification", False)):
            verification_passed = False
        else:
            verification_passed = True

        fallback_steps = int(execution_summary.get("fallback_steps", 0) or 0)
        if fallback_steps <= 0 and isinstance(execution_stats, dict):
            stats_steps = list(execution_stats.get("steps", []) or [])
            fallback_steps = sum(1 for item in stats_steps if bool(item.get("fallback_used", False)))

        stale_result_count = sum(
            1
            for result in (tool_results.values() if isinstance(tool_results, dict) else [])
            if isinstance(result, dict) and bool(result.get("success")) and bool(result.get("is_stale", False))
        )

        if not _is_answer_complete(resolved_answer):
            if resolved_answer:
                resolved_answer = f"{resolved_answer.rstrip()} {_INCOMPLETE_ANSWER_FALLBACK}"
            else:
                resolved_answer = _INCOMPLETE_ANSWER_FALLBACK

        return SupervisorDoneEvent(
            answer=resolved_answer,
            tools_used=resolved_tools_used,
            session_id=self.session_id,
            run_id=self.run_id,
            plan_id=plan_id,
            intent=intent,
            execution_stats=execution_stats if isinstance(execution_stats, dict) else {},
            verification_passed=verification_passed,
            stale_result_count=stale_result_count,
            fallback_steps=fallback_steps,
        ).to_dict()
