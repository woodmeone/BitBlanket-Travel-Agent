"""流式终结器，负责成功/失败流式运行的持久化和终端事件生成。

终结器（Finalizer）模式说明：
    终结器负责在流式传输结束后执行收尾工作，包括：
    1. 补全派生状态（如去重工具列表、计算降级步骤数）
    2. 持久化助手消息和记忆
    3. 发送遥测和结构化日志
    4. 构建终端事件（metadata + done / error + done）

    将终结逻辑从流式传输主流程中分离，降低复杂度，便于独立测试。
"""

from __future__ import annotations

import logging
from typing import Any

from .stream_diagnostics import ChatStreamDiagnostics


class ChatStreamFinalizer:
    """持久化诊断数据并构建流式聊天的终端事件。"""

    def __init__(
        self,
        *,
        service: Any,
        logger: logging.Logger,
        diagnostics: ChatStreamDiagnostics,
    ) -> None:
        """存储服务钩子、日志器和诊断构建器。

        Args:
            service: ChatService 实例，用于调用持久化和记忆方法
            logger: 日志器实例
            diagnostics: 诊断信息构建器
        """
        self._service = service
        self._logger = logger
        self._diagnostics = diagnostics

    async def finalize_success(
        self,
        state: Any,
        *,
        message: str,
        mode: str,
    ) -> list[dict[str, Any]]:
        """【核心】持久化成功运行结果并构建终端元数据事件。

        执行顺序：
        1. 补全派生状态（去重工具列表、计算降级步骤等）
        2. 构建成功诊断信息
        3. 持久化助手消息和记忆
        4. 发送成功遥测和结构化日志
        5. 返回终端事件列表（metadata + done）
        """
        self._finalize_stream_state(state, mode)
        assistant_diagnostics = self._diagnostics.build_success_diagnostics(state)
        await self._persist_successful_stream(state, message=message, diagnostics=assistant_diagnostics)
        self._emit_success_stream_telemetry(state, mode=mode)
        return self._build_success_terminal_payloads(state)

    async def finalize_failure(
        self,
        state: Any,
        *,
        mode: str,
        error: Exception,
    ) -> list[dict[str, Any]]:
        """持久化失败状态并构建终端错误事件。

        执行顺序：
        1. 记录异常日志
        2. 记录失败运行指标
        3. 持久化中断消息
        4. 发送失败遥测
        5. 返回终端事件列表（error + done）
        """
        self._logger.exception("Chat stream failed: %s", error)

        self._service._record_run_metrics(
            intent=state.detected_intent or ("direct" if mode == "direct" else "unknown"),
            execution_stats=state.execution_stats,
            hard_error=True,
        )
        await self._persist_failed_stream(state)
        self._emit_failed_stream_telemetry(state, mode=mode, error=error)
        return self._build_failure_terminal_payloads(state, error=error)

    def _finalize_stream_state(self, state: Any, mode: str) -> None:
        """在终端元数据生成前补全派生字段。

        - 去重工具列表（同一工具可能被多次调用）
        - 从执行步骤中统计降级回退数和过期结果数
        - 推断验证是否通过（direct 模式默认通过，其他模式看是否有过期结果）
        """
        state.tools_used = list(dict.fromkeys(state.tools_used))
        stats_steps = list((state.execution_stats or {}).get("steps", []) or [])
        if state.fallback_steps <= 0:
            state.fallback_steps = sum(1 for item in stats_steps if bool(item.get("fallback_used", False)))
        if state.stale_result_count <= 0:
            state.stale_result_count = sum(1 for item in stats_steps if bool(item.get("is_stale", False)))
        if state.verification_passed is None:
            state.verification_passed = True if mode == "direct" else state.stale_result_count == 0

    async def _persist_successful_stream(
        self,
        state: Any,
        *,
        message: str,
        diagnostics: dict[str, Any],
    ) -> None:
        """持久化成功运行的助手输出和记忆副作用。

        1. 保存助手消息（含推理过程和诊断信息）
        2. 写入助手记忆
        3. 如果用户消息尚未写入记忆（如流式过程中失败），补写
        """
        resolved_sid = state.resolved_session_id()
        await self._service.save_message(
            resolved_sid,
            "assistant",
            state.answer_content,
            state.reasoning_content or None,
            diagnostics=diagnostics,
        )
        if not await self._service._write_memory_assistant(resolved_sid, state.answer_content):
            self._logger.warning("Failed to write assistant memory for session=%s", resolved_sid)
        if not state.memory_user_written:
            await self._service._write_memory_user(resolved_sid, message)

    def _emit_success_stream_telemetry(self, state: Any, *, mode: str) -> None:
        """持久化成功后发送成功指标和结构化日志。"""
        from ...observability import emit_structured_log, record_chat_stream

        resolved_sid = state.resolved_session_id()
        self._service._record_run_metrics(
            intent=state.detected_intent or ("direct" if mode == "direct" else "unknown"),
            execution_stats=state.execution_stats,
            hard_error=False,
        )
        self._service._emit_failure_telemetry(
            session_id=resolved_sid,
            run_id=state.run_id,
            mode=mode,
            execution_stats=state.execution_stats,
            answer=state.answer_content,
        )
        record_chat_stream(mode, "success")
        emit_structured_log(
            self._logger,
            "chat_stream_completed",
            session_id=resolved_sid,
            mode=mode,
            run_id=state.run_id,
            tools_used=state.tools_used,
            verification_passed=state.verification_passed,
            stale_result_count=state.stale_result_count,
            fallback_steps=state.fallback_steps,
        )

    def _build_success_terminal_payloads(self, state: Any) -> list[dict[str, Any]]:
        """构建成功流式运行的终端元数据和 done 事件。

        返回两个事件：
        1. metadata: 包含运行统计、工具使用、验证结果、产物等完整元数据
        2. done: 标记流式传输结束，携带产物和执行回执
        """
        return [
            {
                "type": "metadata",
                "run_id": state.run_id,
                "total_steps": len(state.tools_used),
                "tools_used": state.tools_used,
                "has_reasoning": bool(state.reasoning_content),
                "reasoning_length": len(state.reasoning_content),
                "answer_length": len(state.answer_content),
                "plan_id": state.plan_id,
                "execution_stats": state.execution_stats,
                "verification_passed": state.verification_passed,
                "stale_result_count": state.stale_result_count,
                "fallback_steps": state.fallback_steps,
                "failure_clusters": self._service._extract_failure_clusters(state.execution_stats),
                "artifact": state.final_artifact,
                "execution_receipt": state.execution_receipt,
            },
            {
                "type": "done",
                "run_id": state.run_id,
                "artifact": state.final_artifact,
                "execution_receipt": state.execution_receipt,
            },
        ]

    async def _persist_failed_stream(self, state: Any) -> None:
        """持久化中断输出并写入失败记忆痕迹。

        中断的助手消息内容标记为 [INTERRUPTED]，记忆中也添加
        [INTERRUPTED] 前缀，便于后续排查中断原因。
        """
        resolved_sid = state.resolved_session_id()
        interrupted_answer = state.answer_content or "[INTERRUPTED]"

        try:
            await self._service.save_message(
                resolved_sid,
                "assistant",
                interrupted_answer,
                state.reasoning_content or "stream interrupted",
                diagnostics=self._diagnostics.build_failure_diagnostics(state),
            )
        except Exception:
            pass

        await self._service._write_memory_assistant(resolved_sid, f"[INTERRUPTED]{state.answer_content}")

    def _emit_failed_stream_telemetry(
        self,
        state: Any,
        *,
        mode: str,
        error: Exception,
    ) -> None:
        """发送中断流式运行的错误指标和结构化日志。"""
        from ...observability import emit_structured_log, record_chat_stream

        resolved_sid = state.resolved_session_id()
        self._service._emit_failure_telemetry(
            session_id=resolved_sid,
            run_id=state.run_id,
            mode=mode,
            execution_stats=state.execution_stats,
            answer=state.answer_content,
            hard_error=str(error),
        )
        record_chat_stream(mode, "error")
        emit_structured_log(
            self._logger,
            "chat_stream_failed",
            level=logging.ERROR,
            session_id=resolved_sid,
            mode=mode,
            run_id=state.run_id,
            error=str(error),
        )

    @staticmethod
    def _build_failure_terminal_payloads(
        state: Any,
        *,
        error: Exception,
    ) -> list[dict[str, Any]]:
        """构建中断运行的终端错误和 done 事件。

        返回两个事件：
        1. error: 包含错误信息和运行 ID
        2. done: 标记流式传输结束
        """
        return [
            {"type": "error", "content": str(error), "run_id": state.run_id},
            {"type": "done", "run_id": state.run_id},
        ]
