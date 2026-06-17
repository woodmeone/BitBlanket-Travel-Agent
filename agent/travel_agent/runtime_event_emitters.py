"""
运行时事件发射器（Runtime Event Emitters）

将 Agent 内部事件转换为标准化的 SSE（Server-Sent Events）推送格式，
供前端实时展示 Agent 的运行状态和进度。

SSE 概念说明：
  - SSE（Server-Sent Events）：服务器向浏览器单向推送的实时通信协议，
    前端通过 EventSource API 监听，适合"服务端推送进度"的场景
  - 事件类型：stage（阶段变更）、reasoning（推理过程）、chunk（回答片段）、
    tool_start（工具开始）、tool_end（工具结束）、done（完成）

事件流转：
  Agent 图节点执行 → SupervisorEventEmitter 捕获 → 转换为标准化事件字典 → SSE 推送到前端

旅行场景举例：
  用户问"成都3日游" → 前端看到：
    [stage: parse 10%] 分析请求 → [stage: query 45%] 查询数据
    → [tool_start: query_attractions] → [tool_end] → [chunk: "第一天..."]
    → [stage: finalize 100%] 完成
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .contracts import (
    SupervisorChunkEvent,  # 回答片段事件：流式输出的一段文本
    SupervisorDoneEvent,  # 完成事件：包含最终答案和执行统计
    SupervisorReasoningEvent,  # 推理过程事件：展示 Agent 当前思考内容
    SupervisorStageEvent,  # 阶段变更事件：展示当前执行阶段和进度
    SupervisorToolEndEvent,  # 工具结束事件：工具执行完成
    SupervisorToolStartEvent,  # 工具开始事件：工具开始执行
)

# 工具结果预览的字符数上限，避免 SSE 推送过大的数据
TOOL_RESULT_PREVIEW_LIMIT = 200

# 回答不完整时的兜底提示文本
_INCOMPLETE_ANSWER_FALLBACK = (
    "The main steps are complete, but the current response may be truncated. "
    "Tell me whether you want me to fill in the budget, itinerary, or hotel details first."
)

# 图节点到阶段/进度/标签的映射配置
# 每个节点对应一个执行阶段，用于前端展示进度条和状态文本
_NODE_STAGE_CONFIG: dict[str, dict[str, Any]] = {
    "intent": {
        "stage": "parse",  # 阶段：解析
        "progress": 10,  # 进度：10%
        "label": "Analyze request",  # 前端展示的标签
        "reasoning": "Analyzing user intent...",  # 推理过程文本
    },
    "strategy": {
        "stage": "parse",
        "progress": 18,
        "label": "Select strategy",
        "reasoning": "Selecting the execution strategy...",
    },
    "plan": {
        "stage": "query",  # 阶段：查询
        "progress": 25,
        "label": "Build plan",
        "subagent": "planning",  # 子代理标识
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
        "subagent": "research",  # 子代理：研究
        "reasoning": "Running tools...",
    },
    "answer": {
        "stage": "generate",  # 阶段：生成
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
        "subagent": "verification",  # 子代理：验证
        "reasoning": "Checking price, policy, and date consistency...",
    },
    "self_check": {
        "stage": "finalize",  # 阶段：收尾
        "progress": 95,
        "label": "Self check answer",
    },
}


def _is_answer_complete(answer: str) -> bool:
    """启发式检测生成的回答文本是否完整。

    判断依据：文本长度 ≥ 8 且以句末标点结尾（中英文均可）。
    用于在回答被截断时追加兜底提示。
    """

    text = str(answer or "").strip()
    if len(text) < 8:
        return False
    return text[-1] in {".", "!", "?", "\u3002", "\uff01", "\uff1f"}  # 英文句号/感叹/问号 + 中文句号/感叹/问号


@dataclass(slots=True)
class SupervisorEventEmitter:
    """【核心】运行时事件发射器，发射标准化的 Supervisor 运行事件并追踪流状态。

    在一次完整的 Agent 运行中，此对象持续追踪：
      - 当前阶段和进度
      - 已累积的回答文本
      - 已使用的工具列表
      - 最终的图状态

    旅行场景举例：
      用户问"成都3日游" → 发射器依次发出：
      emit_initial() → emit_node_start("execute") → emit_tool_start("query_attractions")
      → emit_tool_end(...) → emit_chat_chunk("第一天...") → emit_completion_events()
    """

    session_id: str = "default"  # 会话 ID，用于关联 SSE 流
    run_id: str | None = None  # 运行 ID，用于追踪单次执行
    answer: str = ""  # 累积的回答文本（流式拼接）
    tools_used: list[str] = field(default_factory=list)  # 已使用的工具名称列表
    final_state: dict[str, Any] = field(default_factory=dict)  # 最终的图状态
    stage: str = "parse"  # 当前执行阶段：parse / query / generate / finalize
    progress: int = 5  # 当前进度百分比

    def emit_initial(self) -> dict[str, Any]:
        """发射运行流的第一个阶段事件。"""

        return SupervisorStageEvent(
            stage=self.stage,
            progress=self.progress,
            label="Analyze request",
        ).to_dict()

    def emit_node_start(self, node_name: str) -> list[dict[str, Any]]:
        """发射一个图节点转换的阶段/推理事件。

        根据节点名称从 _NODE_STAGE_CONFIG 中查找对应的阶段配置，
        更新当前阶段和进度，并发射阶段事件和可选的推理事件。

        Args:
            node_name: 图节点名称，如 "intent"、"execute"、"answer" 等
        """

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
                subagent=config.get("subagent"),  # 子代理标识，如 "planning"、"research"
            ).to_dict()
        ]
        reasoning = config.get("reasoning")
        if reasoning:
            events.append(SupervisorReasoningEvent(content=str(reasoning)).to_dict())
        return events

    def emit_chat_chunk(self, content: str) -> dict[str, Any] | None:
        """发射一个回答片段事件，并累积到内部回答文本中。

        Args:
            content: 本次回答片段的文本内容
        """

        if not content:
            return None
        self.answer += content  # 累积回答文本
        return SupervisorChunkEvent(content=content).to_dict()

    def emit_tool_start(self, tool_name: str) -> list[dict[str, Any]]:
        """发射工具调用的阶段/开始事件。

        更新阶段为 "query"，递增进度，并记录使用的工具。

        Args:
            tool_name: 工具名称，如 "query_attractions"、"get_weather"
        """

        self.tools_used.append(tool_name)
        self.stage = "query"
        self.progress = min(75, self.progress + 5)  # 每次工具调用进度+5%，上限75%
        return [
            SupervisorStageEvent(
                stage="query",
                progress=self.progress,
                label=f"Query data: {tool_name}",
            ).to_dict(),
            SupervisorToolStartEvent(tool=tool_name, progress=self.progress).to_dict(),
        ]

    def emit_tool_end(self, tool_name: str, result: Any) -> dict[str, Any]:
        """发射一个工具结束事件。

        Args:
            tool_name: 工具名称
            result: 工具执行结果（截断预览）
        """

        return SupervisorToolEndEvent(
            tool=tool_name,
            result=str(result)[:TOOL_RESULT_PREVIEW_LIMIT],  # 截断结果预览，避免 SSE 推送过大
            progress=self.progress,
        ).to_dict()

    def record_chain_output(self, output: Any) -> None:
        """捕获最终的图状态，用于组装完成事件载荷。

        仅当输出包含 "answer" 或 "execution_stats" 字段时才记录。
        """

        if isinstance(output, dict) and ("answer" in output or "execution_stats" in output):
            self.final_state = output

    def interrupted_answer(self) -> str:
        """返回被中断运行时的回答文本（带 [INTERRUPTED] 前缀）。"""

        return f"[INTERRUPTED]{self.answer}"

    def persisted_answer(self) -> str:
        """返回应写入记忆的助手回答文本。

        优先使用最终状态中的 answer，其次使用流式累积的 answer。
        """

        return str(self.final_state.get("answer") or self.answer or "")

    def emit_completion_events(self) -> list[dict[str, Any]]:
        """【核心】发射终止阶段事件和标准化的完成载荷。

        包含两个事件：
          1. 阶段完成事件（stage="finalize", progress=100）
          2. 完成事件（包含最终答案、工具使用、执行统计等）
        """

        return [
            SupervisorStageEvent(stage="finalize", progress=100, label="Complete").to_dict(),
            self._build_done_event(),
        ]

    def _build_done_event(self) -> dict[str, Any]:
        """【核心】构建一次运行流的终止标准化载荷。

        从最终状态和流式累积状态中解析：
          - 最终答案（若不完整则追加兜底提示）
          - 使用的工具列表
          - 执行统计和摘要
          - 验证结果
          - 过期结果计数
          - 降级步骤计数
        """

        resolved_answer = str(self.final_state.get("answer") or self.answer or "")  # 最终答案
        resolved_tools_used = list(self.final_state.get("tools_used") or self.tools_used or [])  # 使用的工具列表
        execution_stats = self.final_state.get("execution_stats", {}) or {}  # 执行统计
        execution_summary = self.final_state.get("execution_summary", {}) or {}  # 执行摘要
        verify_result = self.final_state.get("verify_result", {}) or {}  # 验证结果
        strategy_detail = self.final_state.get("strategy_detail", {}) or {}  # 策略详情
        tool_results = self.final_state.get("tool_results", {}) or {}  # 工具结果
        plan_id = self.final_state.get("plan_id")  # 计划 ID
        intent = self.final_state.get("intent")  # 意图

        # 判断验证是否通过
        if isinstance(verify_result, dict) and "passed" in verify_result:
            verification_passed = bool(verify_result.get("passed"))
        elif bool(strategy_detail.get("requires_verification", False)):
            # 策略要求验证但无验证结果 → 未通过
            verification_passed = False
        else:
            # 无需验证 → 默认通过
            verification_passed = True

        # 统计降级步骤数（使用了 fallback 的步骤）
        fallback_steps = int(execution_summary.get("fallback_steps", 0) or 0)
        if fallback_steps <= 0 and isinstance(execution_stats, dict):
            stats_steps = list(execution_stats.get("steps", []) or [])
            fallback_steps = sum(1 for item in stats_steps if bool(item.get("fallback_used", False)))

        # 统计过期结果数
        stale_result_count = sum(
            1
            for result in (tool_results.values() if isinstance(tool_results, dict) else [])
            if isinstance(result, dict) and bool(result.get("success")) and bool(result.get("is_stale", False))
        )

        # 若回答不完整，追加兜底提示
        if not _is_answer_complete(resolved_answer):
            if resolved_answer:
                resolved_answer = f"{resolved_answer.rstrip()} {_INCOMPLETE_ANSWER_FALLBACK}"
            else:
                resolved_answer = _INCOMPLETE_ANSWER_FALLBACK

        return SupervisorDoneEvent(
            answer=resolved_answer,  # 最终答案
            tools_used=resolved_tools_used,  # 使用的工具列表
            session_id=self.session_id,  # 会话 ID
            run_id=self.run_id,  # 运行 ID
            plan_id=plan_id,  # 计划 ID
            intent=intent,  # 意图
            execution_stats=execution_stats if isinstance(execution_stats, dict) else {},  # 执行统计
            verification_passed=verification_passed,  # 验证是否通过
            stale_result_count=stale_result_count,  # 过期结果数
            fallback_steps=fallback_steps,  # 降级步骤数
        ).to_dict()
