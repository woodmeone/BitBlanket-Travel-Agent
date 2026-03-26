"""Budget subagent for cost estimation and tradeoff reporting."""

from __future__ import annotations

from typing import Any, Optional

from .base import BaseSubagent


class BudgetSubagent(BaseSubagent):
    """Minimal budget subagent backed by current budgeting tools and runtime metadata."""

    def artifact_patch_from_done(
        self,
        done_event: dict[str, Any],
        *,
        user_message: str,
        session_id: str,
        chat_mode: Optional[str],
    ) -> dict[str, object]:
        """Build a budget artifact patch from the completed stream event."""
        _ = (user_message, session_id)
        tool_names = [name for name in done_event.get("tools_used", []) if name in self.tool_names()]
        execution_budget = done_event.get("execution_budget")
        if not isinstance(execution_budget, dict):
            execution_budget = {}

        fallback_steps = int(done_event.get("fallback_steps", 0) or 0)
        stale_result_count = int(done_event.get("stale_result_count", 0) or 0)
        if not tool_names and not execution_budget and fallback_steps <= 0 and stale_result_count <= 0:
            return {}

        summary = {
            "source_tools": tool_names,
            "sourceTools": tool_names,
            "tool_count": len(tool_names),
            "toolCount": len(tool_names),
            "mode": chat_mode or "react",
        }
        if execution_budget:
            summary["has_execution_budget"] = True
            summary["hasExecutionBudget"] = True

        return {
            "budget": {
                "summary": summary,
                "execution_budget": execution_budget,
                "executionBudget": execution_budget,
                "stale_result_count": stale_result_count,
                "staleResultCount": stale_result_count,
                "fallback_steps": fallback_steps,
                "fallbackSteps": fallback_steps,
            },
            "metadata": {
                "budget_subagent_completed": True,
            },
        }
