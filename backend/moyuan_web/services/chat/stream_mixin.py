"""流式传输编排 Mixin，协调流式协作组件完成 SSE 事件生成。

SSE（Server-Sent Events）流式传输说明：
    SSE 是一种基于 HTTP 的单向推送协议，服务端通过 "data: ...\\n\\n" 格式
    持续向客户端推送事件。与 WebSocket 不同，SSE 是纯文本、单向的，更适合
    LLM 逐 token 输出的场景。前端通过 EventSource API 监听并实时渲染。

异步生成器（AsyncGenerator）说明：
    Python 的 async for ... yield 语法实现异步生成器，每次 yield 产出一个
    SSE 事件字符串，调用方（FastAPI 的 StreamingResponse）逐条发送给客户端。
    好处是无需等待完整响应生成，用户可实时看到推理过程。

典型应用场景：
    用户输入"帮我查三亚的酒店"，stream_chat 方法会：
    1. 先推送 session_id 事件，让前端建立会话绑定
    2. 推送 reasoning_start → reasoning_chunk → reasoning_end（推理过程）
    3. 推送 tool_start → tool_end（工具调用过程）
    4. 推送 answer_start → chunk → done（最终回答）
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Iterable, Optional

from ...bootstrap import ensure_project_paths
from .plan_preview_coordinator import ChatPlanPreviewCoordinator
from .shared import merge_artifact_payload
from .sse_serializer import ChatStreamSSESerializer
from .stream_diagnostics import ChatStreamDiagnostics
from .stream_finalizer import ChatStreamFinalizer

ensure_project_paths()

logger = logging.getLogger(__name__)

@dataclass(slots=True)
class _StreamRunState:
    """单次流式聊天运行期间累积的可变状态。

    每次聊天请求创建一个实例，在流式处理过程中逐步填充，
    最终用于持久化和构建终端事件。slots=True 可减少内存占用。

    应用场景：用户发送"规划三亚5日游"，整个流式过程中：
    - reasoning_content 逐步累积推理文本
    - tools_used 记录调用了哪些工具（如 search_hotel, get_weather）
    - final_artifact 合并各子 Agent 产出的旅行计划片段
    """

    requested_session_id: Optional[str]  # 前端传入的会话 ID（可能不存在）
    session_id: Optional[str] = None     # 实际解析后的会话 ID
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))  # 本次运行唯一标识
    answer_content: str = ""             # 累积的最终回答文本
    reasoning_content: str = ""          # 累积的推理过程文本
    tools_used: list[str] = field(default_factory=list)  # 本次运行使用的工具名称列表
    plan_id: Optional[str] = None       # 生成的旅行计划 ID（plan 模式下）
    detected_intent: Optional[str] = None  # 检测到的用户意图（如 "hotel_search"）
    execution_stats: dict[str, Any] = field(default_factory=dict)  # 执行统计信息
    verification_passed: Optional[bool] = None  # 结果验证是否通过
    stale_result_count: int = 0         # 过期结果计数（如缓存命中的旧数据）
    fallback_steps: int = 0             # 降级回退步骤数
    final_artifact: dict[str, Any] = field(default_factory=dict)  # 最终合并的旅行计划产物
    subagent_events: list[dict[str, Any]] = field(default_factory=list)  # 子 Agent 生命周期事件
    execution_receipt: dict[str, Any] = field(default_factory=dict)  # 执行回执（含各步骤详情）
    answer_started: bool = False        # 是否已推送 answer_start 事件
    reasoning_ended: bool = False       # 是否已推送 reasoning_end 事件
    memory_user_written: bool = False   # 用户消息是否已写入记忆

    def resolved_session_id(self) -> str:
        """返回最佳可用会话标识符，用于持久化和日志记录。

        优先级：实际 session_id > 请求传入的 session_id > "unknown"
        """
        return self.session_id or self.requested_session_id or "unknown"

class ChatStreamMixin:
    """聊天流式传输和 SSE 序列化方法 Mixin。

    提供流式聊天的完整生命周期管理：从接收用户消息到推送 SSE 事件流，
    再到最终持久化和终端事件生成。被 ChatService 通过多继承混入。
    """

    async def stream_chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        mode: str = "react",
        display_message: Optional[str] = None,
        request_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """【核心】执行一次聊天请求并以 SSE 事件流的形式返回结果。

        这是聊天服务的入口方法，被 FastAPI 的 StreamingResponse 调用。

        Args:
            message: 用户输入的原始消息文本
            session_id: 可选的会话 ID，不存在则自动创建
            mode: 聊天模式 - "direct"(直接LLM) / "react"(工具编排) / "plan"(规划预览)
            display_message: 前端展示用的消息文本（可能与原始消息不同，如脱敏处理）
            request_id: 请求追踪 ID
            trace_id: 分布式追踪 ID

        Yields:
            str: SSE 格式的事件字符串，如 "data: {...}\\n\\n"

        应用场景：用户输入"帮我查三亚酒店"，此方法会持续 yield SSE 事件，
        前端 EventSource 逐条接收并渲染推理过程和最终回答。
        """
        from ...observability import bind_request_context, emit_structured_log, reset_request_context

        context_tokens = bind_request_context(request_id or str(uuid.uuid4()), trace_id)  # 绑定请求上下文用于日志追踪
        mode = self._normalize_mode(mode)
        state = _StreamRunState(requested_session_id=session_id)

        try:
            await self.initialize()
            state.session_id = await self._ensure_session(session_id)  # 确保会话存在
            emit_structured_log(  # 记录结构化日志，便于后续排查问题
                logger,
                "chat_stream_started",
                session_id=state.session_id,
                mode=mode,
                run_id=state.run_id,
            )

            yield self._serialize_sse_payload(  # 推送 session_id 事件，前端据此绑定会话
                {"type": "session_id", "session_id": state.session_id, "run_id": state.run_id}
            )
            await self._save_user_message(  # 持久化用户消息到会话历史
                state.session_id,
                display_message or message,
                model_content=message,
            )
            state.memory_user_written = await self._write_memory_user(state.session_id, message)  # 写入记忆管理器

            async for envelope in self._stream_normalized_sse_events(state, message=message, mode=mode):  # 【核心】流式推送规范化事件
                yield envelope

            for envelope in self._serialize_sse_payloads(  # 推送终端事件（metadata + done）
                await self._finalize_stream_run(state, message=message, mode=mode)
            ):
                yield envelope

        except Exception as exc:
            for envelope in self._serialize_sse_payloads(  # 异常时推送 error + done 事件
                await self._finalize_stream_failure(state, mode=mode, error=exc)
            ):
                yield envelope
        finally:
            reset_request_context(context_tokens)  # 清理请求上下文，防止上下文泄漏

    async def _stream_normalized_sse_events(
        self,
        state: _StreamRunState,
        *,
        message: str,
        mode: str,
    ) -> AsyncGenerator[str, None]:
        """将规范化的运行时事件序列化为 SSE 信封并逐条产出。"""
        async for payload in self._normalize_stream_events(state, message=message, mode=mode):
            yield self._serialize_sse_payload(payload)

    async def _normalize_stream_events(
        self,
        state: _StreamRunState,
        *,
        message: str,
        mode: str,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """【核心】将内部运行时输出规范化为公共流式事件。

        根据模式分支处理：
        - direct: 直接流式输出 LLM token，无工具调用
        - react: 先推送推理过程，再流式输出 Agent 事件（含工具调用）
        - plan: 先生成规划预览，再执行 react 流程

        应用场景：用户选择"规划模式"时，先展示计划预览（哪些步骤、什么意图），
        再逐步执行各步骤并推送结果。
        """
        if mode == "direct":
            async for payload in self._normalize_direct_stream_events(state, message=message):
                yield payload
            return

        yield {"type": "reasoning_start"}  # 推理阶段开始标记

        if mode == "plan":
            for payload in await self._normalize_plan_preview_events(state, message=message):  # plan 模式下先生成预览
                yield payload

        async for event in self._stream_agent_events(  # 流式获取 Agent 运行时事件
            state.resolved_session_id(),
            message,
            mode=mode,
            run_id=state.run_id,
        ):
            for payload in self._normalize_runtime_event(state, event):  # 规范化每个运行时事件
                yield payload

        for payload in self._ensure_answer_section_started(state):  # 确保推理→回答的边界事件已推送
            yield payload

    async def _normalize_direct_stream_events(
        self,
        state: _StreamRunState,
        *,
        message: str,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """规范化 direct 模式的 LLM 流式输出为标准事件。

        direct 模式跳过工具编排，直接流式输出 LLM token，
        适用于简单问答场景（如"今天天气怎么样"）。
        """
        yield {"type": "reasoning_start"}
        yield {"type": "reasoning_end"}
        state.reasoning_ended = True
        yield {"type": "answer_start"}
        state.answer_started = True

        async for token in self._stream_direct_response(state.resolved_session_id(), message):
            state.answer_content += token
            yield {"type": "chunk", "content": token}

    async def _normalize_plan_preview_events(
        self,
        state: _StreamRunState,
        *,
        message: str,
    ) -> list[dict[str, Any]]:
        """规范化 plan 模式的规划预览输出。

        应用场景：用户输入"规划三亚5日游"，先展示计划预览：
        "识别意图：trip_planning，将执行 4 步"
        """
        return await self._build_plan_preview_coordinator().normalize(
            state,
            session_id=state.resolved_session_id(),
            message=message,
        )

    def _build_plan_preview_coordinator(self) -> ChatPlanPreviewCoordinator:
        """构建规划预览协调器，用于 plan 模式下的预览生成。"""
        return ChatPlanPreviewCoordinator(
            generate_plan_preview=self._generate_plan_preview,
            get_timestamp=self._get_timestamp,
            logger=logger,
        )

    def _build_stream_sse_serializer(self) -> ChatStreamSSESerializer:
        """构建 SSE 序列化器，将规范化事件转为 SSE 信封格式。"""
        return ChatStreamSSESerializer()

    def _build_stream_diagnostics(self) -> ChatStreamDiagnostics:
        """构建诊断信息生成器，用于流式运行结束后的诊断数据构建。"""
        return ChatStreamDiagnostics()

    def _build_stream_finalizer(self) -> ChatStreamFinalizer:
        """构建流式终结器，负责成功/失败时的持久化和终端事件生成。"""
        return ChatStreamFinalizer(
            service=self,
            logger=logger,
            diagnostics=self._build_stream_diagnostics(),
        )
    def _normalize_runtime_event(
        self,
        state: _StreamRunState,
        event: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """【核心】规范化单个运行时事件并更新累积的流式状态。

        按优先级依次尝试四类事件处理器，首个匹配的处理器返回结果：
        1. 推理事件（reasoning/stage）
        2. 子 Agent 事件（subagent_start/subagent_end/artifact_patch）
        3. 工具事件（tool_start/tool_end）
        4. 回答事件（chunk/done）
        """
        for handler in (
            self._normalize_reasoning_runtime_event,
            self._normalize_subagent_runtime_event,
            self._normalize_tool_runtime_event,
            self._normalize_answer_runtime_event,
        ):
            payloads = handler(state, event)
            if payloads is not None:
                return payloads

        return []

    def _normalize_reasoning_runtime_event(
        self,
        state: _StreamRunState,
        event: dict[str, Any],
    ) -> Optional[list[dict[str, Any]]]:
        """规范化推理和阶段事件。

        应用场景：Agent 思考过程中推送 "正在搜索酒店..." 等推理片段，
        前端在推理区域实时展示。
        """
        event_type = event.get("type")
        if event_type == "reasoning":
            content = event.get("content", "")
            state.reasoning_content += content
            return [{"type": "reasoning_chunk", "content": content}]
        if event_type == "stage":
            return [
                {
                    "type": "stage",
                    "stage": event.get("stage"),
                    "label": event.get("label"),
                    "progress": event.get("progress"),
                    "subagent": event.get("subagent"),
                }
            ]
        return None

    def _normalize_subagent_runtime_event(
        self,
        state: _StreamRunState,
        event: dict[str, Any],
    ) -> Optional[list[dict[str, Any]]]:
        """规范化子 Agent 生命周期和产物补丁事件。

        子 Agent 说明：主 Agent 可将复杂任务拆分给子 Agent 执行，
        如"酒店搜索子 Agent"、"景点推荐子 Agent"。
        subagent_start/end 标记子 Agent 的执行边界，
        artifact_patch 用于逐步合并子 Agent 产出的旅行计划片段。
        """
        event_type = event.get("type")
        if event_type == "subagent_start":
            state.subagent_events.append(
                {
                    "subagent": event.get("subagent"),
                    "description": event.get("description"),
                    "skills": event.get("skills", []),
                    "toolNames": event.get("tool_names", []),
                    "sequence": event.get("sequence"),
                    "trigger": event.get("trigger"),
                    "timestamp": self._get_timestamp(),
                }
            )
            return [
                {
                    "type": "subagent_start",
                    "subagent": event.get("subagent"),
                    "description": event.get("description"),
                    "skills": event.get("skills", []),
                    "tool_names": event.get("tool_names", []),
                    "sequence": event.get("sequence"),
                    "trigger": event.get("trigger"),
                }
            ]
        if event_type == "subagent_end":
            state.subagent_events.append(
                {
                    "subagent": event.get("subagent"),
                    "sequence": event.get("sequence"),
                    "status": event.get("status"),
                    "summary": event.get("summary"),
                    "timestamp": self._get_timestamp(),
                }
            )
            return [
                {
                    "type": "subagent_end",
                    "subagent": event.get("subagent"),
                    "sequence": event.get("sequence"),
                    "status": event.get("status"),
                    "summary": event.get("summary"),
                }
            ]
        if event_type == "artifact_patch":
            state.final_artifact = merge_artifact_payload(
                state.final_artifact,
                event.get("artifact_patch") if isinstance(event.get("artifact_patch"), dict) else {},
            )
            return [
                {
                    "type": "artifact_patch",
                    "subagent": event.get("subagent"),
                    "artifact_patch": event.get("artifact_patch", {}),
                }
            ]
        return None

    def _normalize_tool_runtime_event(
        self,
        state: _StreamRunState,
        event: dict[str, Any],
    ) -> Optional[list[dict[str, Any]]]:
        """规范化工具生命周期事件，并更新已使用工具追踪。

        应用场景：Agent 调用 search_hotel 工具时，前端展示"正在搜索酒店..."，
        工具返回结果后展示"找到3家酒店"。
        """
        event_type = event.get("type")
        if event_type == "tool_start":
            tool_name = event.get("tool", "")
            if tool_name:
                state.tools_used.append(tool_name)
            return [
                {
                    "type": "tool_start",
                    "tool": tool_name,
                    "subagent": event.get("subagent"),
                }
            ]
        if event_type == "tool_end":
            return [
                {
                    "type": "tool_end",
                    "tool": event.get("tool", ""),
                    "result": event.get("result", ""),
                    "subagent": event.get("subagent"),
                }
            ]
        return None

    def _normalize_answer_runtime_event(
        self,
        state: _StreamRunState,
        event: dict[str, Any],
    ) -> Optional[list[dict[str, Any]]]:
        """规范化回答 token 流和终端运行时更新。

        chunk 事件携带 LLM 输出的文本片段，done 事件携带运行终态数据。
        """
        event_type = event.get("type")
        if event_type == "chunk":
            payloads = self._ensure_answer_section_started(state)
            content = event.get("content", "")
            if content:
                state.answer_content += content
                payloads.append({"type": "chunk", "content": content})
            return payloads
        if event_type == "done":
            self._apply_done_event(state, event)
            return []
        return None

    def _apply_done_event(self, state: _StreamRunState, event: dict[str, Any]) -> None:
        """将终端运行时事件数据合并到累积的流式状态中。

        done 事件由 Agent 运行时在执行完成时推送，包含最终回答、
        意图、执行统计、产物等终态数据。
        """
        state.answer_content = event.get("answer", state.answer_content)
        state.plan_id = event.get("plan_id") or state.plan_id
        state.detected_intent = event.get("intent") or state.detected_intent
        state.execution_stats = event.get("execution_stats") or state.execution_stats

        if event.get("verification_passed") is not None:
            state.verification_passed = bool(event.get("verification_passed"))

        if event.get("stale_result_count") is not None:
            try:
                state.stale_result_count = int(event.get("stale_result_count") or 0)
            except Exception:
                state.stale_result_count = 0

        if event.get("fallback_steps") is not None:
            try:
                state.fallback_steps = int(event.get("fallback_steps") or 0)
            except Exception:
                state.fallback_steps = 0

        if isinstance(event.get("artifact"), dict):
            state.final_artifact = merge_artifact_payload(state.final_artifact, event.get("artifact"))
        if isinstance(event.get("execution_receipt"), dict):
            state.execution_receipt = dict(event.get("execution_receipt"))

        stream_tools = event.get("tools_used", [])
        if stream_tools:
            state.tools_used.extend([tool for tool in stream_tools if tool])

    def _ensure_answer_section_started(self, state: _StreamRunState) -> list[dict[str, Any]]:
        """确保在回答 token 流出前推送缺失的推理/回答边界事件。

        如果推理阶段尚未结束（如 Agent 直接产出回答而未推送 reasoning_end），
        则自动补充边界事件，保证前端状态机正确转换。
        """
        payloads: list[dict[str, Any]] = []
        if not state.reasoning_ended:
            payloads.append({"type": "reasoning_end"})
            state.reasoning_ended = True
        if not state.answer_started:
            payloads.append({"type": "answer_start"})
            state.answer_started = True
        return payloads

    async def _finalize_stream_run(
        self,
        state: _StreamRunState,
        *,
        message: str,
        mode: str,
    ) -> list[dict[str, Any]]:
        """持久化成功运行结果并构建终端元数据事件。"""
        return await self._build_stream_finalizer().finalize_success(
            state,
            message=message,
            mode=mode,
        )

    async def _finalize_stream_failure(
        self,
        state: _StreamRunState,
        *,
        mode: str,
        error: Exception,
    ) -> list[dict[str, Any]]:
        """持久化失败状态并构建终端错误事件。"""
        return await self._build_stream_finalizer().finalize_failure(
            state,
            mode=mode,
            error=error,
        )

    def _finalize_stream_state(self, state: _StreamRunState, mode: str) -> None:
        """兼容性包装：委托给终结器完成派生状态补全。"""
        self._build_stream_finalizer()._finalize_stream_state(state, mode)

    def _build_success_terminal_payloads(self, state: _StreamRunState) -> list[dict[str, Any]]:
        """兼容性包装：委托给终结器构建成功终端事件。"""
        return self._build_stream_finalizer()._build_success_terminal_payloads(state)

    def _build_failure_terminal_payloads(
        self,
        state: _StreamRunState,
        *,
        error: Exception,
    ) -> list[dict[str, Any]]:
        """兼容性包装：委托给终结器构建失败终端事件。"""
        return self._build_stream_finalizer()._build_failure_terminal_payloads(state, error=error)

    def _serialize_sse_payload(self, payload: dict[str, Any]) -> str:
        """将单个规范化事件序列化为 SSE 信封。"""
        return self._build_stream_sse_serializer().serialize_payload(payload)

    def _serialize_sse_payloads(self, payloads: Iterable[dict[str, Any]]) -> list[str]:
        """将批量规范化事件序列化为 SSE 信封列表。"""
        return self._build_stream_sse_serializer().serialize_payloads(payloads)

    def _build_success_diagnostics(self, state: _StreamRunState) -> dict[str, Any]:
        """构建成功流式运行的助手诊断信息。"""
        return self._build_stream_diagnostics().build_success_diagnostics(state)

    def _build_failure_diagnostics(self, state: _StreamRunState) -> dict[str, Any]:
        """构建中断流式运行的诊断信息。"""
        return self._build_stream_diagnostics().build_failure_diagnostics(state)

    @staticmethod
    def _public_artifact_contract(payload: Any) -> dict[str, Any] | None:
        """将存储的产物载荷规范化为公共合约格式。"""
        return ChatStreamDiagnostics.public_artifact_contract(payload)

    async def _stream_direct_response(self, session_id: str, message: str) -> AsyncGenerator[str, None]:
        """direct 模式下流式输出 LLM token，跳过工具编排。

        构建包含系统提示、历史上下文和用户消息的完整 prompt，
        然后通过 LLM 的 astream 方法逐 token 产出。
        """
        from langchain_core.messages import HumanMessage, SystemMessage
        from agent.travel_agent.graph import TRAVEL_AGENT_SYSTEM_PROMPT

        history = self._build_relevant_memory_context_messages(session_id, message)  # 优先使用查询相关的记忆上下文
        if not history:
            history = await self._build_history_messages(session_id, exclude_last_user_message=message)  # 回退到完整历史
        payload: list[Any] = [SystemMessage(content=TRAVEL_AGENT_SYSTEM_PROMPT)]  # 系统提示词
        payload.extend(history)  # 历史对话上下文
        payload.append(HumanMessage(content=message))  # 当前用户消息

        async for chunk in self._llm.astream(payload):
            token = self._extract_stream_text(chunk)
            if token:
                yield token

    @staticmethod
    def _extract_stream_text(chunk: Any) -> str:
        """从异构流式 chunk 中提取文本 token。

        LLM 返回的 chunk 格式不统一（可能是字符串、列表、字典），
        此方法统一处理各种格式，确保正确提取文本内容。
        """
        content = getattr(chunk, "content", chunk)
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                    continue
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            return "".join(parts)
        if isinstance(content, dict):
            text = content.get("text")
            if isinstance(text, str):
                return text
        return str(content)

    async def _stream_agent_events(
        self,
        session_id: str,
        message: str,
        mode: str = "react",
        run_id: Optional[str] = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """【核心】将图（Graph）流式事件桥接为服务层规范化事件字典。

        通过 AgentRuntime 的 stream_with_memory 方法获取流式事件，
        并对 tool_end 事件的结果文本进行截断，防止过长的工具输出占用带宽。
        """
        from agent.travel_agent.runtime import TOOL_RESULT_PREVIEW_LIMIT

        if self._agent_runtime is None:
            raise RuntimeError("Agent runtime is not initialized")

        async for event in self._agent_runtime.stream_with_memory(
            user_message=message,
            session_id=session_id,
            persist_memory=False,
            run_id=run_id,
            chat_mode=mode,
        ):
            if event.get("type") == "tool_end":
                event["result"] = str(event.get("result", ""))[:TOOL_RESULT_PREVIEW_LIMIT]  # 截断工具结果，防止过长
            yield event

    def _generate_plan_preview(self, session_id: str, message: str) -> dict[str, Any]:
        """生成 plan 模式下在完整执行前展示的计划预览载荷。

        应用场景：用户输入"规划三亚5日游"，先展示计划预览：
        意图=trip_planning，步骤=[搜索酒店, 查询天气, 推荐景点, 生成行程]
        """
        if self._agent_runtime is None:
            raise RuntimeError("Agent runtime is not initialized")

        return self._agent_runtime.generate_plan_preview_with_memory(
            user_message=message,
            session_id=session_id,
            chat_mode="plan",
        )

    @staticmethod
    def _normalize_mode(mode: Optional[str]) -> str:
        """规范化请求的模式，无效值回退到安全的默认值 "react"。"""
        if not mode:
            return "react"
        mode = mode.strip().lower()
        valid_modes = {"direct", "react", "plan"}
        return mode if mode in valid_modes else "react"

    @staticmethod
    def _sse(payload: dict[str, Any]) -> str:
        """将结构化载荷对象序列化为单行 SSE 信封。"""
        return ChatStreamSSESerializer.sse(payload)
