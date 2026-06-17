"""Execution receipt contracts summarizing one multi-subagent runtime run.

【模块说明】
本模块定义了"执行回执"契约，用于在 Agent 一次完整运行结束后，
生成一份结构化的执行报告，记录每个子代理的执行情况。

【核心概念 - 什么是"执行回执"(Execution Receipt)?】
类似于快递的签收回执，记录了"谁做了什么、用了什么工具、结果如何"。
这份回执可以用于：调试排查问题、统计执行效率、展示执行洞察给用户。

【应用场景举例】
Agent 完成"成都3日游"规划后，生成执行回执：
- ExecutionReceipt:
  - session_id: "session_abc"
  - subagent_order: ["research", "planning", "budget", "verification"]
  - tools_used: ["search_attractions", "search_hotels", "calculate_budget"]
  - segments:
    - SubagentExecutionReceipt(research子代理): 调用了search_attractions，状态completed
    - SubagentExecutionReceipt(planning子代理): 调用了search_hotels，状态completed
    - SubagentExecutionReceipt(budget子代理): 调用了calculate_budget，状态completed
    - SubagentExecutionReceipt(verification子代理): 未调用工具，状态completed
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


# 执行阶段快照 - 记录子代理执行过程中的一个阶段
@dataclass(slots=True)
class ExecutionReceiptStage:
    """Describe one observed stage routed through a subagent segment.

    【说明】记录子代理执行过程中的一个阶段信息，如"正在搜索"、"正在分析"等。
    """

    stage: Optional[str] = None  # 阶段标识，如 "searching"、"analyzing"
    label: Optional[str] = None  # 阶段显示文本，如 "正在搜索成都景点"

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable stage snapshot."""
        return {
            "stage": self.stage,
            "label": self.label,
        }


# 子代理执行回执 - 记录单个子代理的执行情况
@dataclass(slots=True)
class SubagentExecutionReceipt:
    """Summarize one subagent segment within a supervisor run.

    【说明】记录一个子代理（如 research、planning）在一次运行中的完整执行情况，
    包括调用了哪些工具、经历了哪些阶段、最终状态等。

    【应用场景】research 子代理执行完毕后的回执：
    - subagent="research", sequence=1
    - tool_names=["search_attractions"], tools_used=["search_attractions"]
    - stages=[Stage(searching, "正在搜索景点"), Stage(analyzing, "正在分析结果")]
    - status="completed", summary="找到20个成都热门景点"
    """

    subagent: str  # 子代理名称，如 "research"、"planning"
    sequence: int  # 执行顺序编号（第几个执行的子代理）
    trigger: Optional[str] = None  # 触发原因，如 "user_request"
    description: Optional[str] = None  # 子代理功能描述
    skills: list[str] = field(default_factory=list)  # 使用的技能列表
    tool_names: list[str] = field(default_factory=list)  # 可用工具名称列表
    tools_used: list[str] = field(default_factory=list)  # 实际使用的工具名称列表
    stages: list[ExecutionReceiptStage] = field(default_factory=list)  # 经历的阶段列表
    artifact_patch_sections: list[str] = field(default_factory=list)  # 修改的产物（artifact）部分
    status: str = "running"  # 执行状态："running"=运行中, "completed"=完成, "failed"=失败
    summary: Optional[str] = None  # 执行结果摘要

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable receipt segment."""
        return {
            "subagent": self.subagent,
            "sequence": self.sequence,
            "trigger": self.trigger,
            "description": self.description,
            "skills": list(self.skills),
            "toolNames": list(self.tool_names),
            "toolsUsed": list(self.tools_used),
            "stages": [stage.to_dict() for stage in self.stages],
            "artifactPatchSections": list(self.artifact_patch_sections),
            "status": self.status,
            "summary": self.summary,
        }


# 【核心】顶层执行回执 - 一次完整 Agent 运行的总结报告
@dataclass(slots=True)
class ExecutionReceipt:
    """Top-level execution summary returned at the end of one runtime run.

    【说明】一次 Agent 运行的完整执行回执，汇总所有子代理的执行情况。
    这是整个执行报告的"封面"，包含全局信息和各子代理的详细回执。

    【应用场景】Agent 完成一次"成都3日游"规划：
    - session_id: "session_abc"
    - run_id: "run_001"
    - chat_mode: "travel_planning"
    - subagent_order: ["research", "planning", "budget", "verification"]
    - tools_used: ["search_attractions", "search_hotels", "calculate_budget"]
    - segments: [4个子代理的详细回执]
    """

    session_id: str  # 会话ID
    run_id: Optional[str] = None  # 运行ID
    chat_mode: Optional[str] = None  # 聊天模式
    subagent_order: list[str] = field(default_factory=list)  # 子代理执行顺序
    tools_used: list[str] = field(default_factory=list)  # 所有使用的工具列表
    artifact_patch_subagents: list[str] = field(default_factory=list)  # 修改了产物的子代理列表
    segments: list[SubagentExecutionReceipt] = field(default_factory=list)  # 各子代理的详细回执

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable execution receipt."""
        return {
            "sessionId": self.session_id,
            "runId": self.run_id,
            "chatMode": self.chat_mode,
            "subagentOrder": list(self.subagent_order),
            "toolsUsed": list(self.tools_used),
            "artifactPatchSubagents": list(self.artifact_patch_subagents),
            "segments": [segment.to_dict() for segment in self.segments],
        }
