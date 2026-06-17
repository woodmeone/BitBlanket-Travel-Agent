"""Contracts that describe supervisor runtime requests, preview results, health diagnostics, and shared execution context.

【模块说明】
本模块定义了 Supervisor 编排层相关的契约，包括：
1. 运行时上下文（SupervisorRuntimeContext）- 运行时共享依赖
2. 运行请求（SupervisorRunRequest）- 一次 Agent 执行的请求参数
3. 计划预览请求与结果（SupervisorPlanPreviewRequest/Preview）- 预览 Agent 的执行计划
4. 工具健康诊断（SupervisorToolHealthEntry/Diagnostics）- 监控工具的熔断状态

【核心概念 - 什么是"编排"(Orchestration)?】
编排就像乐队指挥，负责协调各个乐器（子代理、工具）的演奏顺序和配合方式。
这里的契约定义了"指挥"需要的信息：有哪些乐手（工具）、要演奏什么曲目（请求）、
乐手状态如何（健康诊断）。

【应用场景举例】
1. 用户发送消息 → 创建 SupervisorRunRequest → 启动 Agent 执行
2. Agent 执行前 → 生成 SupervisorPlanPreview → 前端展示"我将这样处理您的请求"
3. 工具频繁失败 → SupervisorToolHealthDiagnostics 记录熔断状态 → 自动降级
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

# Runnable: LangChain 中的可运行对象接口，LLM 模型就是一种 Runnable
# Tool: LangChain 中的工具基类，Agent 可调用的外部能力（如搜索、查询）都继承自 Tool
from langchain_core.runnables import Runnable
from langchain_core.tools import Tool


# 【核心】运行时上下文 - 携带 Supervisor 运行所需的共享依赖
@dataclass(slots=True)
class SupervisorRuntimeContext:
    """Carry shared runtime dependencies used by the supervisor compatibility bridge.

    【说明】将 Supervisor 运行时需要的核心依赖打包在一起，避免到处传参。
    类似于"工具箱"，里面装着 LLM（大脑）、Tools（手）、Memory（记忆）。

    【应用场景】启动 Agent 时，将 LLM 模型、可用工具列表、记忆管理器
    打包成 SupervisorRuntimeContext，传递给 Supervisor 使用。
    """

    llm: Runnable  # 大语言模型实例，Agent 的"大脑"，用于理解和生成文本
    tools: list[Tool]  # 可用工具列表，Agent 的"手"，如搜索酒店、查询航班等
    memory_manager: Any = None  # 记忆管理器，管理对话历史和用户偏好
    routing_llm: Optional[Runnable] = None  # 路由用 LLM，专门用于判断将请求分发给哪个子代理


# 运行请求 - 描述一次 Agent 执行的输入参数
@dataclass(slots=True)
class SupervisorRunRequest:
    """Describe one streaming supervisor run requested by the application layer.

    【说明】当用户发送一条消息时，后端会创建此请求对象，包含用户消息和运行参数。
    这是启动 Agent 执行的"入场券"。

    【应用场景】用户输入"帮我规划成都3日游"：
    - user_message="帮我规划成都3日游"
    - session_id="session_abc123"
    - chat_mode="travel_planning"
    → 后端据此创建请求，启动 Agent 流式执行
    """

    user_message: str  # 用户发送的消息内容
    session_id: str = "default"  # 会话ID，默认"default"
    system_prompt: Optional[str] = None  # 可选的自定义系统提示词，覆盖默认提示词
    persist_memory: bool = True  # 是否将本次对话持久化到记忆中，默认True
    run_id: Optional[str] = None  # 可选的运行ID，用于追踪和日志
    chat_mode: Optional[str] = None  # 可选的聊天模式，如 "travel_planning"、"casual_chat"

    def resolved_system_prompt(self, default: str) -> str:
        """Return the effective system prompt for this runtime request.

        【说明】返回实际使用的系统提示词。如果请求中指定了自定义提示词则用自定义的，
        否则使用传入的默认提示词。类似于"有特别指示就用特别的，没有就用默认的"。
        """
        return self.system_prompt or default


# 计划预览请求 - 在正式执行前预览 Agent 的执行计划
@dataclass(slots=True)
class SupervisorPlanPreviewRequest:
    """Describe one supervisor plan-preview request issued through the runtime seam.

    【说明】在 Agent 正式执行之前，可以先请求一个"计划预览"，
    让用户看到 Agent 打算如何处理他的请求，类似于"执行方案确认"。

    【应用场景】用户输入"帮我规划成都3日游"：
    → 先发送 PlanPreviewRequest → Agent 返回预览：
      "我打算：1.研究成都景点 2.搜索酒店 3.规划行程 4.验证方案"
    → 用户确认后 → 再正式执行
    """

    user_message: str  # 用户发送的消息内容
    session_id: str = "default"  # 会话ID
    system_prompt: Optional[str] = None  # 可选的自定义系统提示词
    chat_mode: Optional[str] = None  # 可选的聊天模式

    def resolved_system_prompt(self, default: str) -> str:
        """Return the effective system prompt for this preview request.

        【说明】与 SupervisorRunRequest 的同名方法逻辑相同，返回实际使用的系统提示词。
        """
        return self.system_prompt or default


# 计划预览结果 - Agent 执行计划的预览内容
@dataclass(slots=True)
class SupervisorPlanPreview:
    """Describe the normalized legacy plan-preview payload used by the runtime seam.

    【说明】Agent 对用户请求的执行计划预览，包含意图识别、计划步骤和验证结果。
    类似于旅行顾问在正式做方案前，先告诉用户"我理解您想要X，打算分这几步做"。

    【应用场景】用户输入"帮我规划成都3日游"：
    - plan_id: "plan_001"
    - intent: "travel_planning"（识别为旅行规划意图）
    - intent_detail: {"destination": "成都", "duration": 3}
    - plan_explanation: "我将为您规划成都3日游，包括景点推荐、酒店预订和行程安排"
    - validation_status: "pass"（计划验证通过）
    - plan: [步骤1: 研究景点, 步骤2: 搜索酒店, 步骤3: 规划行程]
    """

    plan_id: Optional[str] = None  # 计划唯一标识
    intent: Optional[str] = None  # 识别到的用户意图，如 "travel_planning"
    intent_detail: dict[str, Any] = field(default_factory=dict)  # 意图详细信息，如目的地、天数等
    plan_explanation: str = ""  # 计划说明文字，给用户看的解释
    validation_status: str = "pass"  # 验证状态，"pass"=通过, "fail"=失败
    validation_errors: list[Any] = field(default_factory=list)  # 验证错误列表（如果有）
    plan: list[Any] = field(default_factory=list)  # 计划步骤列表

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SupervisorPlanPreview":
        """Build one preview contract from a legacy dictionary payload.

        【说明】类方法（@classmethod），从字典创建预览对象。
        类方法的特点：不需要先创建实例就能调用，用 cls 代表类本身。
        类似于从快递单信息还原出一个完整的快递对象。
        """
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
        """Return a JSON-serializable preview payload for downstream runtime consumers.

        【说明】将预览对象转换为可序列化为 JSON 的字典，用于网络传输。
        JSON-serializable 意思是能被转成 JSON 字符串的格式（字符串、数字、列表、字典等）。
        """
        return {
            "plan_id": self.plan_id,
            "intent": self.intent,
            "intent_detail": _copy_dict(self.intent_detail),
            "plan_explanation": self.plan_explanation,
            "validation_status": self.validation_status,
            "validation_errors": _copy_list(self.validation_errors),
            "plan": _copy_list(self.plan),
        }


# 工具健康条目 - 记录单个工具的熔断器状态
@dataclass(slots=True)
class SupervisorToolHealthEntry:
    """Describe one normalized tool-health snapshot inside the legacy runtime seam.

    【说明】记录单个工具的健康状态，实现"熔断器"（Circuit Breaker）模式。
    熔断器就像电路保险丝：当工具连续失败太多次，就"跳闸"停止调用该工具，
    避免浪费时间和资源，等冷却期过后再尝试恢复。

    【应用场景】酒店搜索工具连续失败3次：
    - consecutive_failures=3 → 连续失败3次
    - is_circuit_open=True → 熔断器打开，暂停调用该工具
    - cooldown_remaining_seconds=60 → 60秒后冷却结束，可以重试
    - open_until=1715000000.0 → 熔断器打开的截止时间戳
    """

    consecutive_failures: int = 0  # 连续失败次数
    open_until: float = 0.0  # 熔断器打开的截止时间（Unix时间戳），0表示未打开
    is_circuit_open: bool = False  # 熔断器是否打开（True=暂停调用该工具）
    cooldown_remaining_seconds: int = 0  # 冷却剩余秒数

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


# 工具健康诊断汇总 - 所有工具的健康状态总览
@dataclass(slots=True)
class SupervisorToolHealthDiagnostics:
    """Describe the normalized tool-health diagnostics returned by the legacy runtime seam.

    【说明】汇总所有工具的健康状态，用于运维监控和降级决策。
    就像医院的"体检报告汇总"，列出所有科室的检查结果。

    【应用场景】运维人员查看 Agent 工具状态：
    - tool_count=5 → 共5个工具
    - open_circuit_count=1 → 1个工具熔断中
    - tools={"search_hotels": 熔断中, "search_flights": 正常, ...}
    → 据此决定是否需要人工介入或调整策略
    """

    runtime_config: dict[str, Any] = field(default_factory=dict)  # 运行时配置信息
    tool_count: int = 0  # 工具总数
    open_circuit_count: int = 0  # 熔断中的工具数量
    tools: dict[str, SupervisorToolHealthEntry] = field(default_factory=dict)  # 各工具的健康状态字典

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


# ========== 以下为内部辅助函数，用于安全地转换数据类型 ==========
# 这些函数的作用是：将"不确定类型"的值安全地转换为目标类型，
# 如果转换失败则返回默认值，避免程序因类型错误而崩溃。

def _coerce_text(value: Any, default: str = "") -> str:
    """Normalize an optional runtime value into text.

    【说明】将任意值转为字符串，None 则返回默认值。
    例如: _coerce_text(None) → ""; _coerce_text(123) → "123"
    """
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _coerce_optional_text(value: Any) -> str | None:
    """Normalize an optional runtime value into text or ``None``.

    【说明】与 _coerce_text 类似，但空字符串返回 None 而非默认值。
    例如: _coerce_optional_text("") → None; _coerce_optional_text("hello") → "hello"
    """
    text = _coerce_text(value)
    return text or None


def _coerce_int(value: Any, default: int = 0) -> int:
    """Normalize a loose numeric value into an integer.

    【说明】安全地将任意值转为整数，失败则返回默认值。
    例如: _coerce_int("3") → 3; _coerce_int("abc") → 0
    """
    try:
        return int(value)
    except Exception:
        return default


def _coerce_float(value: Any, default: float = 0.0) -> float:
    """Normalize a loose numeric value into a float.

    【说明】安全地将任意值转为浮点数，失败则返回默认值。
    例如: _coerce_float("3.14") → 3.14; _coerce_float(None) → 0.0
    """
    try:
        return float(value)
    except Exception:
        return default


def _copy_dict(value: Any) -> dict[str, Any]:
    """Return a shallow builtin-dict copy for loose preview payloads.

    【说明】浅拷贝字典。如果值是字典则复制一份，否则返回空字典。
    "浅拷贝"指只复制第一层，嵌套的字典仍然是引用。
    """
    return dict(value) if isinstance(value, dict) else {}


def _copy_list(value: Any) -> list[Any]:
    """Return a shallow builtin-list copy for loose preview payloads.

    【说明】浅拷贝列表。如果值是列表则复制一份，否则返回空列表。
    """
    return list(value) if isinstance(value, list) else []
