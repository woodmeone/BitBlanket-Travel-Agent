"""预算子代理（Budget Subagent）模块。

职责：估算费用范围和权衡方案。
    budget 子代理是旅行规划的"财务顾问"，负责：
    - 估算机票、酒店、餐饮等各项费用
    - 管理执行预算（execution_budget）约束
    - 跟踪数据过期（stale_result）和降级回退（fallback）情况

    类比旅行社：budget 子代理就是"预算分析师"，
    根据客户预算范围，评估各项花费是否合理，给出费用权衡建议。
"""

from __future__ import annotations

from typing import Any, Optional

from .base import BaseSubagent


class BudgetSubagent(BaseSubagent):
    """预算子代理，基于现有预算工具和运行时元数据实现。

    覆写基类的 artifact_patch_from_done 方法，
    从完成事件中提取预算信息和执行统计数据。
    """

    def artifact_patch_from_done(
        self,
        done_event: dict[str, Any],  # 完成事件，包含 execution_budget、fallback_steps 等数据
        *,
        user_message: str,  # 用户原始消息
        session_id: str,  # 会话ID
        chat_mode: Optional[str],  # 对话模式，如 "react" 或 "plan"
    ) -> dict[str, object]:
        """【核心】从完成事件构建预算产物补丁。

        只在存在预算相关数据时才生成产物（使用了预算工具、
        有执行预算约束、或存在降级/过期情况），
        否则返回空字典。

        旅行场景举例：
            用户说"东京5天预算1万够吗"，budget 子代理估算后
            产物包含 execution_budget={total: 10000, currency: "CNY"}、
            tool_count=2（调用了机票和酒店比价工具）
        """
        _ = (user_message, session_id)
        # 筛选出本次执行中属于本子代理的工具
        tool_names = [name for name in done_event.get("tools_used", []) if name in self.tool_names()]
        # 执行预算约束，如 {"total": 10000, "currency": "CNY"}
        execution_budget = done_event.get("execution_budget")
        if not isinstance(execution_budget, dict):
            execution_budget = {}

        # 降级回退步数：当工具调用失败时使用备选方案的次数
        fallback_steps = int(done_event.get("fallback_steps", 0) or 0)
        # 过期结果数量：使用了缓存中过期数据的次数
        stale_result_count = int(done_event.get("stale_result_count", 0) or 0)

        # 无任何预算相关数据时不生成产物
        if not tool_names and not execution_budget and fallback_steps <= 0 and stale_result_count <= 0:
            return {}

        summary = {
            "source_tools": tool_names,  # 使用的预算工具列表（snake_case）
            "sourceTools": tool_names,  # camelCase 版本
            "tool_count": len(tool_names),  # 工具使用数量
            "toolCount": len(tool_names),  # camelCase 版本
            "mode": chat_mode or "react",  # 执行模式，默认 "react"（推理+行动模式）
        }
        if execution_budget:
            summary["has_execution_budget"] = True  # 标记存在执行预算约束
            summary["hasExecutionBudget"] = True  # camelCase 版本

        return {
            "budget": {
                "summary": summary,  # 预算执行摘要
                "execution_budget": execution_budget,  # 执行预算详情（snake_case）
                "executionBudget": execution_budget,  # camelCase 版本
                "stale_result_count": stale_result_count,  # 过期结果数量（snake_case）
                "staleResultCount": stale_result_count,  # camelCase 版本
                "fallback_steps": fallback_steps,  # 降级回退步数（snake_case）
                "fallbackSteps": fallback_steps,  # camelCase 版本
            },
            "metadata": {
                "budget_subagent_completed": True,  # 标记预算子代理已完成
            },
        }
