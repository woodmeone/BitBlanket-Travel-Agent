"""Contracts describing normalized legacy supervisor runtime events.

【模块说明】
本模块定义了 Supervisor（监督者）在运行过程中发出的各类"事件契约"。
这些事件通过 SSE（Server-Sent Events，服务端推送事件）流式传输到前端，
让用户能实时看到 Agent 的执行进度、推理过程和最终结果。

【核心概念 - 什么是"契约"(Contract)?】
在软件工程中，"契约"是一种约定好的数据格式规范。
就像快递单上的字段（收件人、地址、电话）是固定格式一样，
这里的事件契约规定了每个事件必须包含哪些字段、字段类型是什么，
确保 Agent 后端和前端之间的数据传递不会出错。

【应用场景举例】
用户在聊天框输入"帮我规划一个成都3日游"，Agent 开始执行：
1. 前端收到 SupervisorStageEvent → 显示"正在研究目的地..."进度条
2. 前端收到 SupervisorReasoningEvent → 显示"根据用户偏好，推荐美食路线..."
3. 前端收到 SupervisorToolStartEvent → 显示"正在调用酒店搜索工具..."
4. 前端收到 SupervisorToolEndEvent → 显示"找到15家酒店"
5. 前端收到 SupervisorChunkEvent → 流式显示最终回答的文字片段
6. 前端收到 SupervisorDoneEvent → 显示完成，包含完整答案和统计信息
"""

# from __future__ import annotations: Python 特殊导入，允许在类型注解中使用尚未定义的类名
# 例如在方法返回值类型中写 "SupervisorStageEvent" 时，不会报"未定义"错误
from __future__ import annotations

# dataclass: Python 内置装饰器，自动生成 __init__、__repr__ 等方法，省去手写样板代码
# field: 用于为 dataclass 字段设置默认值等属性
from dataclasses import dataclass, field
from typing import Any, Optional  # Any: 任意类型; Optional[X] 等价于 X | None，表示可以为空


# 【核心】阶段进度事件 - 告知前端 Agent 当前执行到哪个阶段了
# slots=True: Python 3.10+ 特性，用 __slots__ 替代 __dict__，节省内存并提高属性访问速度
@dataclass(slots=True)
class SupervisorStageEvent:
    """Describe one normalized stage update emitted by the legacy supervisor path.

    【说明】表示 Agent 执行过程中的一个"阶段"更新。
    例如："正在研究目的地"、"正在规划行程"、"正在验证方案"等。

    【应用场景】用户问"成都3日游"，Agent 执行流程：
    - stage="research", progress=20, label="正在研究成都景点..." → 前端显示20%进度
    - stage="planning", progress=60, label="正在规划3日行程..." → 前端显示60%进度
    - stage="verification", progress=90, label="正在验证方案可行性..." → 前端显示90%进度
    """

    stage: str  # 阶段标识，如 "research"、"planning"、"verification"
    progress: int  # 进度百分比，0-100
    label: str  # 给用户看的阶段描述文字，如 "正在研究成都景点..."
    subagent: Optional[str] = None  # 可选：当前执行该阶段的子代理名称，如 "research_subagent"

    def to_dict(self) -> dict[str, Any]:
        """Return the SSE-ready stage payload while omitting empty optional fields.

        【说明】将事件转换为字典格式，用于 SSE 推送给前端。
        如果 subagent 为空则不包含该字段，避免前端收到多余的 null 值。
        """
        payload = {
            "type": "stage",
            "stage": self.stage,
            "progress": self.progress,
            "label": self.label,
        }
        if self.subagent:
            payload["subagent"] = self.subagent
        return payload


# 推理过程事件 - 让用户看到 Agent 的"思考过程"
@dataclass(slots=True)
class SupervisorReasoningEvent:
    """Describe one reasoning breadcrumb emitted by the legacy supervisor path.

    【说明】记录 Agent 的推理"面包屑"（breadcrumb，即思路线索）。
    用于展示 Agent 的思考过程，增加透明度和用户信任感。

    【应用场景】Agent 推理过程：
    - content="用户预算有限，优先推荐性价比高的民宿" → 前端显示推理气泡
    - content="成都3月多雨，建议室内外行程搭配" → 前端显示推理气泡
    """

    content: str  # 推理内容文本，如 "用户预算有限，优先推荐性价比高的民宿"

    def to_dict(self) -> dict[str, str]:
        """Return the normalized reasoning payload.

        【说明】转换为 {"type": "reasoning", "content": "..."} 格式推送给前端。
        """
        return {
            "type": "reasoning",
            "content": self.content,
        }


# 回答片段事件 - 流式输出 Agent 的最终回答文字
@dataclass(slots=True)
class SupervisorChunkEvent:
    """Describe one answer chunk emitted by the legacy supervisor path.

    【说明】Agent 最终回答的一个文字片段。类似于 ChatGPT 的"逐字输出"效果，
    每生成一小段文字就推送一个 chunk 事件，前端拼接后呈现流式打字效果。

    【应用场景】Agent 生成回答 "推荐您第一天去宽窄巷子..."：
    - chunk1: content="推荐您" → 前端显示"推荐您"
    - chunk2: content="第一天去" → 前端追加显示"推荐您第一天去"
    - chunk3: content="宽窄巷子..." → 前端追加显示完整句子
    """

    content: str  # 回答文字片段，如 "推荐您"

    def to_dict(self) -> dict[str, str]:
        """Return the normalized answer chunk payload.

        【说明】转换为 {"type": "chunk", "content": "..."} 格式推送给前端。
        """
        return {
            "type": "chunk",
            "content": self.content,
        }


# 工具调用开始事件 - 告知前端 Agent 正在调用某个工具
@dataclass(slots=True)
class SupervisorToolStartEvent:
    """Describe one normalized tool-start update emitted by the legacy supervisor path.

    【说明】当 Agent 开始调用某个工具（如酒店搜索、航班查询）时发出此事件。
    前端据此显示"正在搜索酒店..."等加载状态。

    【应用场景】Agent 执行过程中调用工具：
    - tool="search_hotels", progress=40 → 前端显示"正在搜索酒店..."（40%进度）
    - tool="search_flights", progress=55 → 前端显示"正在查询航班..."（55%进度）
    """

    tool: str  # 工具名称，如 "search_hotels"、"search_flights"
    progress: int  # 调用此工具时的整体进度百分比

    def to_dict(self) -> dict[str, Any]:
        """Return the normalized tool-start payload.

        【说明】转换为 {"type": "tool_start", "tool": "...", "progress": N} 格式。
        """
        return {
            "type": "tool_start",
            "tool": self.tool,
            "progress": self.progress,
        }


# 工具调用结束事件 - 告知前端工具调用完成及其结果
@dataclass(slots=True)
class SupervisorToolEndEvent:
    """Describe one normalized tool-end update emitted by the legacy supervisor path.

    【说明】当 Agent 调用的工具执行完毕后发出此事件，携带工具返回的结果摘要。
    前端据此更新状态，如从"正在搜索酒店..."变为"找到15家酒店"。

    【应用场景】工具调用完成：
    - tool="search_hotels", result="找到15家酒店", progress=50 → 前端显示搜索结果摘要
    - tool="search_flights", result="找到8个航班", progress=65 → 前端显示查询结果摘要
    """

    tool: str  # 工具名称，如 "search_hotels"
    result: str  # 工具返回的结果摘要，如 "找到15家酒店"
    progress: int  # 工具完成后的整体进度百分比

    def to_dict(self) -> dict[str, Any]:
        """Return the normalized tool-end payload.

        【说明】转换为 {"type": "tool_end", "tool": "...", "result": "...", "progress": N} 格式。
        """
        return {
            "type": "tool_end",
            "tool": self.tool,
            "result": self.result,
            "progress": self.progress,
        }


# 【核心】执行完成事件 - Agent 一次完整运行的最终总结
@dataclass(slots=True)
class SupervisorDoneEvent:
    """Describe the terminal normalized payload emitted by the legacy supervisor path.

    【说明】这是 Agent 一次完整运行结束后的最终事件，包含完整答案和执行统计信息。
    前端收到此事件后，标记本次对话完成，停止显示加载状态。

    【应用场景】Agent 完成一次"成都3日游"规划：
    - answer: "为您规划了成都3日游方案：第一天..."（完整回答）
    - tools_used: ["search_hotels", "search_attractions", "search_restaurants"]
    - session_id: "user_123_session_456"
    - verification_passed: True（方案验证通过）
    - execution_stats: {"total_time": 12.5, "tool_calls": 3}
    """

    answer: str  # Agent 的完整回答文本
    tools_used: list[str] = field(default_factory=list)  # 本次运行使用的工具名称列表
    session_id: str = "default"  # 会话ID，标识一次用户对话
    run_id: Optional[str] = None  # 运行ID，标识一次具体的 Agent 执行
    plan_id: Optional[str] = None  # 计划ID，关联生成的旅行计划
    intent: Optional[str] = None  # 识别到的用户意图，如 "travel_planning"
    execution_stats: dict[str, Any] = field(default_factory=dict)  # 执行统计（耗时、工具调用次数等）
    verification_passed: Optional[bool] = None  # 方案验证是否通过
    stale_result_count: int = 0  # 过期结果数量（如酒店信息已过时）
    fallback_steps: int = 0  # 降级回退步数（工具调用失败后走备用方案的次数）

    def to_dict(self) -> dict[str, Any]:
        """Return the normalized terminal payload consumed by the runtime seam.

        【说明】转换为完整的终端事件字典，包含所有执行结果和统计信息。
        """
        return {
            "type": "done",
            "answer": self.answer,
            "tools_used": list(self.tools_used),
            "session_id": self.session_id,
            "run_id": self.run_id,
            "plan_id": self.plan_id,
            "intent": self.intent,
            "execution_stats": dict(self.execution_stats),
            "verification_passed": self.verification_passed,
            "stale_result_count": self.stale_result_count,
            "fallback_steps": self.fallback_steps,
        }
