"""
Supervisor（监督者）图构建器 —— 兼容当前 LangGraph 运行时的实现。

Supervisor 层的概念与作用：
==========================
在旅行 Agent 架构中，Supervisor 是位于"单图执行"之上的协调层。
可以把它理解为一个旅行团的"领队"——领队不亲自订酒店、查路线，
而是把任务分配给擅长不同领域的子 Agent（研究、规划、预算、核验），
并确保它们按正确顺序协作。

与 LangGraph 图的关系：
- LangGraph 的核心抽象是 StateGraph（状态图），由"节点（Node）"和"边（Edge）"组成。
- 本模块的 SupervisorTravelAgentGraph 继承自 TravelAgentGraph，
  保留了原有的图拓扑结构（节点和边的连接方式不变），
  但将普通节点替换为"Supervisor 感知"的节点（SupervisorNodes），
  从而在无需重写整张图的前提下引入技能注册表（SkillRegistry）等 Supervisor 能力。
- 简单类比：LangGraph 图 = 一条旅行流水线，Supervisor = 流水线上的调度员。

典型场景举例（成都3日游）：
  用户说"帮我规划成都3日游" → Supervisor 接收请求 →
  调度 research 子Agent 查景点 → 调度 planning 子Agent 排行程 →
  调度 budget 子Agent 估算费用 → 调度 verification 子Agent 核验可行性 →
  最终输出完整旅行方案。
"""

from __future__ import annotations  # 允许在类型标注中使用尚未定义的类型（Python 3.7+ 延迟求值）

from typing import Any, Callable, Optional  # Any: 任意类型; Callable: 可调用对象; Optional: 可选类型

from langchain_core.runnables import Runnable  # Runnable: LangChain 的统一可运行接口，LLM、Chain、Tool 等均实现此接口
from langchain_core.tools import Tool  # Tool: LangChain 工具抽象，封装外部能力（如搜索、订票）供 LLM 调用

from ..graph.builder import TravelAgentGraph  # 基础旅行 Agent 图构建器，定义了图的拓扑结构
from ..graph.state import TRAVEL_AGENT_SYSTEM_PROMPT  # 系统提示词常量，定义 Agent 的角色和行为边界
from ..skills import SkillRegistry, build_default_skill_registry  # SkillRegistry: 技能注册表; build_default_skill_registry: 根据工具列表构建默认注册表
from .nodes import SupervisorNodes  # Supervisor 感知的节点集合，替代普通 AgentNodes


class SupervisorTravelAgentGraph(TravelAgentGraph):
    """
    兼容性图类：在保留现有图拓扑的前提下，替换为 Supervisor 感知的节点和技能注册表。

    继承关系：SupervisorTravelAgentGraph → TravelAgentGraph
    - TravelAgentGraph 定义了"节点如何连接"（图的拓扑）
    - 本类仅替换节点实现（AgentNodes → SupervisorNodes），不改变连接方式
    - 这样新增 Supervisor 能力时，无需重新设计整张图
    """

    def __init__(
        self,
        llm: Runnable,  # 大语言模型实例，如 ChatOpenAI，用于生成回复和做路由决策
        tools: list[Tool],  # 可用工具列表，如搜索工具、订票工具等
        system_prompt: str = TRAVEL_AGENT_SYSTEM_PROMPT,  # 系统提示词，定义 Agent 角色边界
        planner_hooks: Optional[dict[str, Callable[[dict], list[dict]]]] = None,  # 规划钩子，允许在规划阶段插入自定义逻辑
        checkpointer: Any = None,  # 检查点存储，用于 LangGraph 的状态持久化（如断点续跑）
        routing_llm: Optional[Runnable] = None,  # 路由用 LLM，专门用于判断将请求分发给哪个子 Agent；若为 None 则复用 llm
        skill_registry: Optional[SkillRegistry] = None,  # 技能注册表，管理子 Agent 可调用的技能；若为 None 则自动构建
    ):
        """初始化 Supervisor 图，保持现有图拓扑不变。"""
        self.llm = llm  # 【核心】主 LLM，驱动所有节点的推理
        self.tools = tools  # 【核心】工具集，供 Agent 调用以完成实际操作
        self.system_prompt = system_prompt  # 系统提示词，约束 Agent 行为
        self.skill_registry = skill_registry or build_default_skill_registry(tools)  # 【核心】技能注册表：若未提供则根据工具自动构建
        # 【核心】创建 Supervisor 感知的节点实例——这是 Supervisor 层的关键，
        # 它替代了普通的 AgentNodes，增加了技能路由和子 Agent 调度能力
        self.nodes = SupervisorNodes(
            llm=llm,
            tools=tools,
            system_prompt=system_prompt,
            planner_hooks=planner_hooks,
            routing_llm=routing_llm,  # 路由 LLM：决定"成都3日游"该交给哪个子 Agent 处理
            skill_registry=self.skill_registry,  # 技能注册表：子 Agent 可用的技能清单
        )
        self.checkpointer = checkpointer  # LangGraph 检查点，支持多轮对话的状态保存与恢复
        self._graph = None  # 编译后的 LangGraph StateGraph 实例，初始为 None，调用 build() 后生成


def build_supervisor_agent(
    llm: Runnable,  # 大语言模型实例
    tools: list[Tool],  # 可用工具列表
    system_prompt: str = TRAVEL_AGENT_SYSTEM_PROMPT,  # 系统提示词
    planner_hooks: Optional[dict[str, Callable[[dict], list[dict]]]] = None,  # 规划钩子
    checkpointer: Any = None,  # 检查点存储
    routing_llm: Optional[Runnable] = None,  # 路由 LLM
    skill_registry: Optional[SkillRegistry] = None,  # 技能注册表
) -> SupervisorTravelAgentGraph:
    """
    【核心】工厂函数：创建并编译 Phase-1 Supervisor 图。

    使用方式：
        agent = build_supervisor_agent(llm=my_llm, tools=my_tools)
        result = agent.invoke({"messages": [{"role": "user", "content": "帮我规划成都3日游"}]})

    Phase-1 含义：当前为第一阶段实现，仅引入 Supervisor 元数据和技能注册表，
    后续阶段将逐步增加子 Agent 独立图、并行执行等高级能力。
    """
    agent = SupervisorTravelAgentGraph(  # 创建 Supervisor 图实例
        llm=llm,
        tools=tools,
        system_prompt=system_prompt,
        planner_hooks=planner_hooks,
        checkpointer=checkpointer,
        routing_llm=routing_llm,
        skill_registry=skill_registry,
    )
    agent.build()  # 【核心】编译图：将节点和边组装为可执行的 LangGraph StateGraph
    return agent
