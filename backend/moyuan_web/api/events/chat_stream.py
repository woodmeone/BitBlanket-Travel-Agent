"""
聊天流 SSE 事件注册表与载荷校验器

【基础知识】
- SSE（Server-Sent Events）：服务端向客户端单向推送事件的 HTTP 长连接协议。
  与 WebSocket 双向通信不同，SSE 是单向的（服务端→客户端），更适合聊天流式输出场景。
  前端通过 EventSource API 监听事件，每个事件有 type 和 data 字段。

- 事件类型体系：聊天流的生命周期由多种事件类型组成，按时间顺序大致为：
  session_id → reasoning_start → reasoning_chunk* → reasoning_end →
  answer_start → stage* → plan_preview* → subagent_start → tool_start →
  tool_end → artifact_patch* → subagent_end → chunk* → metadata → done/error

- Pydantic 判别联合（Discriminated Union）：通过 type 字段自动选择对应的事件模型，
  实现类型安全的序列化/反序列化，避免手动 if-else 判断事件类型。
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator

from ..schemas import normalize_artifact_patch, normalize_execution_receipt, normalize_trip_plan_artifact


class _ChatStreamEventBase(BaseModel):
    """所有 SSE 事件的公共基类，携带请求追踪元数据。"""

    model_config = ConfigDict(extra="forbid")  # 禁止额外字段，防止未知字段静默透传

    request_id: Optional[str] = None
    trace_id: Optional[str] = None


class SessionIdEvent(_ChatStreamEventBase):
    """会话标识事件 —— 通知前端当前流对应的 session_id 和 run_id。"""

    type: Literal["session_id"]
    session_id: str
    run_id: str


class ReasoningStartEvent(_ChatStreamEventBase):
    """推理开始事件 —— 标记 LLM 推理阶段的开始。"""

    type: Literal["reasoning_start"]


class ReasoningChunkEvent(_ChatStreamEventBase):
    """推理增量事件 —— 携带一段推理文本片段，前端逐步拼接展示。"""

    type: Literal["reasoning_chunk"]
    content: str


class ReasoningEndEvent(_ChatStreamEventBase):
    """推理结束事件 —— 标记 LLM 推理阶段的结束。"""

    type: Literal["reasoning_end"]


class AnswerStartEvent(_ChatStreamEventBase):
    """回答开始事件 —— 标记正式回答内容的开始。"""

    type: Literal["answer_start"]


class StageEvent(_ChatStreamEventBase):
    """阶段转换事件 —— 通知前端当前运行阶段（如"规划中"、"搜索中"）。

    应用场景：前端根据 stage 和 progress 展示进度条或步骤指示器。
    例：stage="planning", progress=0.6, label="正在规划行程"
    """

    type: Literal["stage"]
    stage: Optional[str] = None
    label: Optional[str] = None
    progress: Optional[float] = None
    subagent: Optional[str] = None


class PlanPreviewEvent(_ChatStreamEventBase):
    """计划预览事件 —— 在最终回答前展示预览计划和产物片段。

    应用场景：Agent 生成行程计划时，先通过 plan_preview 展示中间结果，
    前端可实时展示"正在为您规划北京3日游..."的预览卡片。
    """

    type: Literal["plan_preview"]
    plan_id: Optional[str] = None
    intent: Optional[str] = None
    explanation: Optional[str] = None
    validation_status: Optional[str] = None
    validation_errors: list[Any] = Field(default_factory=list)
    steps: list[dict[str, Any]] = Field(default_factory=list)
    artifact: Optional[dict[str, Any]] = None
    artifact_patch: Optional[dict[str, Any]] = None
    subagent: Optional[str] = None
    skills: list[str] = Field(default_factory=list)

    @field_validator("artifact", mode="before")
    @classmethod
    def _normalize_artifact(cls, value: Any) -> dict[str, Any] | None:
        """将内嵌产物载荷标准化为公共契约格式。"""
        if value is None:
            return None
        return normalize_trip_plan_artifact(value)

    @field_validator("artifact_patch", mode="before")
    @classmethod
    def _normalize_artifact_patch(cls, value: Any) -> dict[str, Any] | None:
        """将预览产物补丁标准化为公共契约格式。"""
        if value is None:
            return None
        return normalize_artifact_patch(value)


class SubagentStartEvent(_ChatStreamEventBase):
    """子代理开始事件 —— 通知前端一个委派子代理步骤开始执行。

    应用场景：旅行规划中，主 Agent 可能委派"酒店搜索"子代理，
    前端收到此事件后展示"正在搜索酒店..."的提示。
    """

    type: Literal["subagent_start"]
    subagent: str
    description: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    tool_names: list[str] = Field(default_factory=list)
    sequence: Optional[int] = None
    trigger: Optional[str] = None


class SubagentEndEvent(_ChatStreamEventBase):
    """子代理结束事件 —— 通知前端一个委派子代理步骤执行完毕。"""

    type: Literal["subagent_end"]
    subagent: str
    sequence: Optional[int] = None
    status: Optional[str] = None
    summary: Optional[str] = None


class ArtifactPatchEvent(_ChatStreamEventBase):
    """产物增量补丁事件 —— 携带子代理输出的增量产物补丁。

    应用场景：子代理逐步生成行程计划时，每次更新通过 artifact_patch 推送，
    前端可实时合并展示，无需等待最终结果。
    """

    type: Literal["artifact_patch"]
    subagent: str
    artifact_patch: dict[str, Any] = Field(default_factory=dict)

    @field_validator("artifact_patch", mode="before")
    @classmethod
    def _normalize_artifact_patch(cls, value: Any) -> dict[str, Any]:
        """将流式产物补丁标准化为公共契约格式。"""
        return normalize_artifact_patch(value)


class ToolStartEvent(_ChatStreamEventBase):
    """工具执行开始事件 —— 通知前端某个工具（如搜索、地图）开始执行。"""

    type: Literal["tool_start"]
    tool: str
    subagent: Optional[str] = None


class ToolEndEvent(_ChatStreamEventBase):
    """工具执行结束事件 —— 通知前端某个工具执行完毕，携带结果摘要。"""

    type: Literal["tool_end"]
    tool: str
    result: str = ""
    subagent: Optional[str] = None


class ChunkEvent(_ChatStreamEventBase):
    """回答增量事件 —— 携带一段回答文本片段，前端逐步拼接展示。"""

    type: Literal["chunk"]
    content: str


class MetadataEvent(_ChatStreamEventBase):
    """元数据事件 —— 流结束时发布执行统计信息。

    包含运行步骤数、使用的工具列表、推理长度、产物等，
    前端可用于展示"本次对话使用了3个工具"等统计信息。
    """

    type: Literal["metadata"]
    run_id: str
    total_steps: int
    tools_used: list[str] = Field(default_factory=list)
    has_reasoning: bool
    reasoning_length: int
    answer_length: int
    plan_id: Optional[str] = None
    execution_stats: dict[str, Any] = Field(default_factory=dict)
    verification_passed: Optional[bool] = None
    stale_result_count: int = 0
    fallback_steps: int = 0
    failure_clusters: Any = None
    artifact: dict[str, Any] = Field(default_factory=dict)
    execution_receipt: dict[str, Any] = Field(default_factory=dict)

    @field_validator("artifact", mode="before")
    @classmethod
    def _normalize_artifact(cls, value: Any) -> dict[str, Any]:
        """将元数据中的产物标准化为公共契约格式。"""
        return normalize_trip_plan_artifact(value)

    @field_validator("execution_receipt", mode="before")
    @classmethod
    def _normalize_execution_receipt(cls, value: Any) -> dict[str, Any]:
        """将元数据中的执行回执标准化为公共契约格式。"""
        return normalize_execution_receipt(value)


class ErrorEvent(_ChatStreamEventBase):
    """错误事件 —— 流中断时携带错误信息。"""

    type: Literal["error"]
    content: str
    run_id: Optional[str] = None


class DoneEvent(_ChatStreamEventBase):
    """完成事件 —— 标记流的正常终止，携带最终产物和执行回执。"""

    type: Literal["done"]
    run_id: str
    artifact: dict[str, Any] = Field(default_factory=dict)
    execution_receipt: dict[str, Any] = Field(default_factory=dict)

    @field_validator("artifact", mode="before")
    @classmethod
    def _normalize_artifact(cls, value: Any) -> dict[str, Any]:
        """将完成事件中的最终产物标准化为公共契约格式。"""
        return normalize_trip_plan_artifact(value)

    @field_validator("execution_receipt", mode="before")
    @classmethod
    def _normalize_execution_receipt(cls, value: Any) -> dict[str, Any]:
        """将完成事件中的执行回执标准化为公共契约格式。"""
        return normalize_execution_receipt(value)


ChatStreamEvent = Annotated[
    Union[
        SessionIdEvent,
        ReasoningStartEvent,
        ReasoningChunkEvent,
        ReasoningEndEvent,
        AnswerStartEvent,
        StageEvent,
        PlanPreviewEvent,
        SubagentStartEvent,
        SubagentEndEvent,
        ArtifactPatchEvent,
        ToolStartEvent,
        ToolEndEvent,
        ChunkEvent,
        MetadataEvent,
        ErrorEvent,
        DoneEvent,
    ],
    Field(discriminator="type"),  # 【核心】通过 type 字段自动判别事件类型，实现类型安全的联合类型
]

CHAT_STREAM_EVENT_TYPES = (
    "session_id",
    "reasoning_start",
    "reasoning_chunk",
    "reasoning_end",
    "answer_start",
    "stage",
    "plan_preview",
    "subagent_start",
    "subagent_end",
    "artifact_patch",
    "tool_start",
    "tool_end",
    "chunk",
    "metadata",
    "error",
    "done",
)

_CHAT_STREAM_EVENT_ADAPTER = TypeAdapter(ChatStreamEvent)  # Pydantic 类型适配器，用于运行时校验和序列化


def validate_chat_stream_payload(
    payload: dict[str, Any],
    *,
    request_id: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> dict[str, Any]:
    """【核心】校验并标准化一条聊天流 SSE 载荷。

    流程：
    1. 补充 request_id / trace_id（如果载荷中未携带）
    2. 通过 TypeAdapter 根据 type 字段自动选择对应的事件模型进行校验
    3. 排除 None 值后返回标准化的字典
    """

    normalized_payload = dict(payload)
    if request_id and "request_id" not in normalized_payload:
        normalized_payload["request_id"] = request_id
    if trace_id and "trace_id" not in normalized_payload:
        normalized_payload["trace_id"] = trace_id

    event = _CHAT_STREAM_EVENT_ADAPTER.validate_python(normalized_payload)  # 根据 type 字段自动选择事件模型校验
    return event.model_dump(exclude_none=True)  # 排除 None 值，减小 SSE 载荷体积


__all__ = [
    "CHAT_STREAM_EVENT_TYPES",
    "ArtifactPatchEvent",
    "ChatStreamEvent",
    "DoneEvent",
    "ErrorEvent",
    "MetadataEvent",
    "PlanPreviewEvent",
    "SessionIdEvent",
    "StageEvent",
    "SubagentEndEvent",
    "SubagentStartEvent",
    "ToolEndEvent",
    "ToolStartEvent",
    "validate_chat_stream_payload",
]
