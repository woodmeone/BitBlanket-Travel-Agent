"""流式聊天诊断信息构建器，生成持久化到消息记录中的诊断数据。

诊断信息（Diagnostics）说明：
    每次聊天运行结束后，会将运行元数据作为诊断信息持久化到助手消息中，
    包括：使用的工具、验证结果、执行统计、产物、子 Agent 事件等。
    这些数据用于：
    1. 前端展示运行详情（如工具调用链、验证状态）
    2. 后续请求的历史回溯
    3. 运维排查问题
"""

from __future__ import annotations

from typing import Any


class ChatStreamDiagnostics:
    """构建规范化诊断载荷，在流式聊天运行结束后持久化。"""

    @staticmethod
    def public_artifact_contract(payload: Any) -> dict[str, Any] | None:
        """将存储的旅行计划产物规范化为公共合约格式。

        产物（Artifact）说明：旅行计划的完整数据结构，包含行程、酒店、
        景点等信息。规范化确保前端和 API 消费者获得一致的数据格式。
        """
        from ...api.schemas import normalize_trip_plan_artifact

        normalized = normalize_trip_plan_artifact(payload)
        return normalized or None

    @staticmethod
    def public_execution_receipt_contract(payload: Any) -> dict[str, Any] | None:
        """将存储的执行回执规范化为公共合约格式。

        执行回执（Execution Receipt）说明：记录每个执行步骤的详细信息，
        包括步骤名称、状态、耗时、结果等，用于前端展示执行过程。
        """
        from ...api.schemas import normalize_execution_receipt

        normalized = normalize_execution_receipt(payload)
        return normalized or None

    def build_success_diagnostics(self, state: Any) -> dict[str, Any]:
        """构建成功流式运行的助手诊断信息，包含完整的运行元数据。"""
        from ...observability import get_request_context

        request_context = get_request_context()
        return {
            "sessionId": state.resolved_session_id(),
            "toolsUsed": state.tools_used,
            "verificationPassed": state.verification_passed,
            "staleResultCount": state.stale_result_count,
            "fallbackSteps": state.fallback_steps,
            "planId": state.plan_id,
            "executionStats": state.execution_stats,
            "artifact": self.public_artifact_contract(state.final_artifact),
            "subagentEvents": state.subagent_events,
            "executionReceipt": self.public_execution_receipt_contract(state.execution_receipt),
            "runId": state.run_id,
            "requestId": request_context.get("request_id"),
            "traceId": request_context.get("trace_id"),
        }

    def build_failure_diagnostics(self, state: Any) -> dict[str, Any]:
        """构建中断流式运行的诊断信息，仅包含中断时可用的数据。"""
        from ...observability import get_request_context

        request_context = get_request_context()
        return {
            "sessionId": state.resolved_session_id(),
            "artifact": self.public_artifact_contract(state.final_artifact),
            "subagentEvents": state.subagent_events,
            "executionReceipt": self.public_execution_receipt_contract(state.execution_receipt),
            "runId": state.run_id,
            "requestId": request_context.get("request_id"),
            "traceId": request_context.get("trace_id"),
        }
