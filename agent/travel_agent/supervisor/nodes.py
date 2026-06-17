"""
Supervisor（监督者）节点包装器 —— 在当前单图实现基础上构建。

Supervisor 节点的概念与作用：
============================
在 LangGraph 的架构中，"节点（Node）"是图中的计算单元，每个节点接收状态、
处理逻辑、返回更新后的状态。SupervisorNodes 是对普通 AgentNodes 的增强包装，
它引入了以下 Supervisor 特有能力：

1. 技能注册表（SkillRegistry）：管理子 Agent 可调用的技能，如搜索景点、估算预算等。
2. 子 Agent 执行顺序（subagent_order）：定义子 Agent 的调度顺序。
3. 旅行方案产物构建（build_trip_plan_artifact）：将图状态转换为结构化的旅行方案。

与 LangGraph 图的关系：
- LangGraph 图由节点和边组成，节点是图中的"处理站"，边是"传送带"。
- SupervisorNodes 替代了普通 AgentNodes 成为图中的处理站，
  在不改变图拓扑（传送带布局）的前提下，增强了每个处理站的能力。
- 类比：同样是"成都3日游"的流水线，SupervisorNodes 让每个工位
  不仅会做本职工作，还知道如何与其他工位协作。

典型场景举例（成都3日游）：
  subagent_order = ["research", "planning", "budget", "verification"]
  → 先由 research 子 Agent 搜索宽窄巷子、大熊猫基地等景点信息
  → 再由 planning 子 Agent 将景点编排为3天行程
  → 然后 budget 子 Agent 估算门票、住宿、餐饮费用
  → 最后 verification 子 Agent 核验行程是否合理（如时间冲突、交通可行性）
"""

from __future__ import annotations  # 允许在类型标注中使用尚未定义的类型（Python 3.7+ 延迟求值）

from typing import Any, Callable, Optional  # Any: 任意类型; Callable: 可调用对象; Optional: 可选类型

from langchain_core.runnables import Runnable  # Runnable: LangChain 统一可运行接口
from langchain_core.tools import Tool  # Tool: LangChain 工具抽象，封装外部能力供 LLM 调用

from ..artifacts import build_trip_plan_artifact_from_state  # 从图状态构建旅行方案产物的工具函数
from ..graph.nodes import AgentNodes  # 基础 Agent 节点类，定义了节点的通用行为
from ..skills import SkillRegistry, build_default_skill_registry  # SkillRegistry: 技能注册表; build_default_skill_registry: 根据工具构建默认注册表


class SupervisorNodes(AgentNodes):
    """
    Phase-1 兼容性包装器：在现有节点行为基础上，引入 Supervisor 元数据和技能系统。

    继承关系：SupervisorNodes → AgentNodes
    - AgentNodes 提供了基础的 LLM 调用、工具执行等节点行为
    - SupervisorNodes 在此基础上新增了技能注册表和子 Agent 调度顺序
    - 这是渐进式演进策略：先包装、后替换，确保不破坏现有功能
    """

    def __init__(
        self,
        llm: Runnable,  # 大语言模型实例，驱动节点内的推理
        tools: list[Tool],  # 可用工具列表，如搜索工具、订票工具等
        system_prompt: str,  # 系统提示词，定义 Agent 角色与行为边界
        planner_hooks: Optional[dict[str, Callable[[dict], list[dict]]]] = None,  # 规划钩子，允许在规划阶段插入自定义逻辑
        routing_llm: Optional[Runnable] = None,  # 路由 LLM，用于判断请求应分发给哪个子 Agent
        skill_registry: Optional[SkillRegistry] = None,  # 技能注册表，管理子 Agent 可用技能
    ):
        """初始化 Phase-1 Supervisor 节点，保留现有节点行为。"""
        # 调用父类 AgentNodes 的初始化，保留原有的 LLM 调用、工具执行等基础能力
        super().__init__(
            llm=llm,
            tools=tools,
            system_prompt=system_prompt,
            planner_hooks=planner_hooks,
            routing_llm=routing_llm,
        )
        # 【核心】技能注册表：若未提供则根据工具列表自动构建
        # 技能注册表是 Supervisor 层的关键组件，它让节点知道"我能做什么"
        # 例如：搜索景点、查询天气、估算预算等都是注册在表中的技能
        self.skill_registry = skill_registry or build_default_skill_registry(tools)
        # 【核心】子 Agent 执行顺序：定义 Supervisor 调度子 Agent 的先后次序
        # 以"成都3日游"为例：
        #   1. research  → 搜索宽窄巷子、锦里、大熊猫基地等景点信息
        #   2. planning  → 将景点编排为 Day1/Day2/Day3 行程
        #   3. budget    → 估算门票、住宿、餐饮、交通费用
        #   4. verification → 核验行程合理性（时间冲突、交通可行性等）
        self.subagent_order = ["research", "planning", "budget", "verification"]

    def build_trip_plan_artifact(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        【核心】从当前图状态构建旅行方案产物（artifact）。

        artifact 是一种"产物优先"的设计理念——将图内部的状态转换为
        面向用户的结构化旅行方案，而非直接暴露内部状态细节。

        参数：
            state: LangGraph 图的当前状态字典，包含对话历史、规划结果等
                   例如：{"messages": [...], "itinerary": {...}, "budget": {...}}

        返回：
            结构化的旅行方案字典，包含行程、预算、注意事项等
            例如：{"trip_plan": {"destination": "成都", "days": 3, "itinerary": [...], ...}}

        场景举例（成都3日游）：
            输入 state 中包含 research 阶段找到的景点、planning 阶段编排的行程、
            budget 阶段估算的费用 → 本方法将它们整合为一份完整的旅行方案。
        """
        return build_trip_plan_artifact_from_state(state)
