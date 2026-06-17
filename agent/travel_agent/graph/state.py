"""
旅行 Agent 图状态模型与默认值定义。

本模块的作用：
    定义旅行 Agent 在 LangGraph 工作流中流转的共享状态结构（AgentState），
    以及创建初始状态的工厂函数和系统提示词。

AgentState 是什么：
    AgentState 是一个类型化的字典（TypedDict），它承载了旅行 Agent 在整个
    图执行过程中所有节点之间传递和共享的数据。每个节点读取并修改状态中的
    特定字段，节点之间通过状态进行解耦通信。

LangGraph 状态流的概念：
    LangGraph 采用"状态机"模式——图由多个节点（Node）和边（Edge）组成，
    状态对象在节点之间自动传递。当一个节点执行完毕后，其返回的状态更新
    会被合并到全局状态中，下一个节点读取最新状态继续执行。
    这类似于流水线：每个工位（节点）从传送带（状态）上取半成品，
    加工后放回传送带，下一个工位继续处理。

    旅行 Agent 的状态流大致为：
    用户输入 → 意图识别 → 策略选择 → 路由分发 → 计划生成 →
    计划校验 → 执行 → 结果验证 → 自检 → 生成回答
"""

# from __future__ import annotations：启用延迟注解求值（PEP 563），
# 允许在类型注解中使用尚未定义的类型（如 list[BaseMessage]），
# 而不必写成 "list[BaseMessage]" 字符串形式
from __future__ import annotations

# TypedDict：Python typing 模块提供的基类，用于定义"具有固定键和值类型的字典"。
# 与普通 dict 不同，TypedDict 让 IDE 和类型检查器知道字典中每个键的值类型，
# 相当于给字典加了一层"类型契约"。例如：
#   class User(TypedDict):
#       name: str
#       age: int
#   u: User = {"name": "Alice", "age": 30}  # 类型检查通过
#
# Annotated：Python typing 模块提供的类型注解增强工具，格式为
# Annotated[基础类型, 元数据1, 元数据2, ...]。
# 它在保留基础类型信息的同时，附加额外的元数据供框架使用。
# 在 LangGraph 中，Annotated[list[BaseMessage], add_messages] 表示：
#   - 基础类型是 list[BaseMessage]（消息列表）
#   - 元数据 add_messages 是一个"reducer 函数"，定义了状态合并策略
#
# add_messages：LangGraph 提供的 reducer 函数，用于合并消息列表。
# 当节点返回新的 messages 时，add_messages 会将新消息追加到已有消息列表末尾，
# 而不是直接覆盖。这确保了对话历史不会丢失。
# 如果不使用 Annotated + reducer，LangGraph 默认会用新值覆盖旧值。
from typing import Annotated, Any, Dict, List, Optional, TypedDict

# BaseMessage：LangChain 消息基类，HumanMessage（用户消息）和
# SystemMessage（系统提示词消息）都是其子类
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

# add_messages：LangGraph 内置的 reducer 函数，用于智能合并消息列表。
# 它支持追加新消息，也支持通过消息 id 更新/删除已有消息
from langgraph.graph import add_messages


# 【核心】AgentState —— 旅行 Agent 的全局共享状态
# 整个 LangGraph 工作流中的所有节点都通过读写这个状态来协作。
# TypedDict 使其兼具字典的灵活性和类型的可检查性。
class AgentState(TypedDict):
    """旅行 Agent 在 LangGraph 节点间流转的共享可变状态。"""

    # 【核心】对话消息列表
    # Annotated[list[BaseMessage], add_messages] 的含义：
    #   - 类型为 BaseMessage 列表
    #   - 使用 add_messages 作为 reducer，新消息会追加而非覆盖
    # 旅行场景举例：用户说"我想去成都"，这条 HumanMessage 被追加到 messages；
    # Agent 回复"好的，我来帮您规划"，这条 AIMessage 也被追加。
    # 整个对话历史通过 messages 字段完整保留。
    messages: Annotated[list[BaseMessage], add_messages]

    # 对话模式，标识当前对话的业务类型
    # 旅行场景举例：值为 "travel" 表示旅行咨询模式，
    # 可能为 "casual"（闲聊）、"travel"（旅行规划）等
    chat_mode: Optional[str]

    # 用户意图标签，由意图识别节点填写
    # 旅行场景举例："recommend"（推荐目的地）、"itinerary"（行程规划）、
    # "budget"（预算查询）、"attraction"（景点查询）、"transport"（出行建议）
    intent: Optional[str]

    # 意图详细信息，包含意图识别的补充参数
    # 旅行场景举例：intent="itinerary" 时，
    # intent_detail={"destination": "成都", "days": 5, "budget": 5000}
    intent_detail: Optional[Dict[str, Any]]

    # 执行策略，由策略选择节点填写
    # 旅行场景举例："single_tool"（单工具直接查询）、
    # "multi_step"（多步骤规划执行）、"clarify"（需要追问用户）
    strategy: Optional[str]

    # 策略详细信息，包含策略执行的补充参数
    # 旅行场景举例：strategy="multi_step" 时，
    # strategy_detail={"steps": ["查景点", "查酒店", "查交通"], "parallel": True}
    strategy_detail: Optional[Dict[str, Any]]

    # 路由目标，由路由节点填写，决定后续走哪条执行路径
    # 旅行场景举例："plan_and_execute"（规划并执行）、
    # "direct_answer"（直接回答）、"clarify"（追问用户）
    routing: Optional[str]

    # 执行计划 ID，用于标识和追踪一次计划
    # 旅行场景举例："plan_20240607_chengdu_001"
    plan_id: Optional[str]

    # 计划说明，对执行计划的自然语言解释
    # 旅行场景举例："为用户规划成都5日游，包含景点、美食和交通安排"
    plan_explanation: Optional[str]

    # 【核心】执行计划步骤列表，每个步骤是一个字典
    # 旅行场景举例：
    # [
    #   {"step": 1, "action": "search_attractions", "params": {"city": "成都"}, "status": "pending"},
    #   {"step": 2, "action": "search_hotels", "params": {"city": "成都", "budget": 300}, "status": "pending"},
    #   {"step": 3, "action": "search_transport", "params": {"from": "北京", "to": "成都"}, "status": "pending"}
    # ]
    plan: Optional[List[Dict[str, Any]]]

    # 计划校验状态，由校验节点填写
    # 旅行场景举例："valid"（校验通过）、"invalid"（校验失败）、"warning"（有警告）
    validation_status: Optional[str]

    # 校验错误列表，记录计划中的问题
    # 旅行场景举例：[{"step": 2, "error": "预算超出范围", "suggestion": "降低酒店档次"}]
    validation_errors: Optional[List[Dict[str, Any]]]

    # 当前执行到的步骤索引（从 0 开始）
    # 旅行场景举例：current_step=2 表示正在执行第3个步骤（查交通）
    current_step: int

    # 执行轮次计数，用于控制重试和循环次数
    # 旅行场景举例：execution_round=1 表示第1轮执行，若验证不通过可能进入第2轮
    execution_round: int

    # 当前并行度，表示同时执行的步骤数
    # 旅行场景举例：parallelism=3 表示同时查询景点、酒店、交通
    parallelism: Optional[int]

    # 最大允许并行度，限制并发工具调用的数量，防止过载
    # 旅行场景举例：max_parallelism=5 表示最多同时执行5个工具调用
    max_parallelism: Optional[int]

    # 各步骤的执行状态映射，记录每个步骤的运行情况
    # 旅行场景举例：
    # {"step_1": {"status": "completed", "result": {...}},
    #  "step_2": {"status": "running"},
    #  "step_3": {"status": "pending"}}
    execution_state: Optional[Dict[str, Any]]

    # 执行统计信息，汇总工具调用的整体数据
    # 旅行场景举例：{"total_calls": 5, "success": 4, "failed": 1, "total_time_ms": 3200}
    execution_stats: Optional[Dict[str, Any]]

    # 执行结果摘要，对工具返回数据的精炼总结
    # 旅行场景举例：{"attractions": 8, "hotels": 5, "avg_price": 280}
    execution_summary: Optional[Dict[str, Any]]

    # 执行轨迹记录，按时间顺序记录每一步操作
    # 旅行场景举例：
    # [{"step": 1, "tool": "search_attractions", "input": {...}, "output": {...}, "time": "2024-06-07T10:30:00"}]
    execution_trace: Optional[List[Dict[str, Any]]]

    # 执行预算控制，限制单次执行的资源消耗
    # 旅行场景举例：{"max_tokens": 10000, "max_tool_calls": 20, "used_tokens": 3500}
    execution_budget: Optional[Dict[str, Any]]

    # 融合后的工具结果，将多个工具的返回数据合并为统一结构
    # 旅行场景举例：将景点、酒店、交通三个工具的结果融合为一个完整的旅行方案
    fused_tool_results: Optional[Dict[str, Any]]

    # 提前终止原因，当执行未完成但需要停止时记录原因
    # 旅行场景举例："budget_exceeded"（超出预算限制）、
    # "max_rounds_reached"（达到最大轮次）、"user_cancelled"（用户取消）
    early_stop_reason: Optional[str]

    # 验证重试次数，记录结果验证阶段的重试计数
    # 旅行场景举例：verify_retry_count=2 表示已重试验证2次
    verify_retry_count: int

    # 验证结果，由验证节点填写，包含对执行结果的检查结论
    # 旅行场景举例：{"passed": True, "issues": [], "score": 0.95}
    verify_result: Optional[Dict[str, Any]]

    # 自检结果，由自检节点填写，对最终回答的质量评估
    # 旅行场景举例：{"hallucination_risk": "low", "completeness": "high", "suggestions": []}
    self_check_result: Optional[Dict[str, Any]]

    # 本次执行使用过的工具名称列表
    # 旅行场景举例：["search_attractions", "search_hotels", "search_transport"]
    tools_used: List[str]

    # 工具返回结果的字典，key 为工具名，value 为该工具的返回数据
    # 旅行场景举例：{"search_attractions": {"items": [...]}, "search_hotels": {"items": [...]}}
    tool_results: Dict[str, Any]

    # 【核心】最终回答，Agent 生成给用户的旅行建议文本
    # 旅行场景举例："为您推荐成都5日游方案：第一天游览武侯祠和锦里..."
    answer: Optional[str]

    # 推理过程，记录 Agent 的思考链路
    # 旅行场景举例："用户想去成都5天，预算5000元，先查景点再查酒店..."
    reasoning: Optional[str]

    # 会话 ID，标识一次完整的用户会话
    # 旅行场景举例："session_abc123"，同一会话的多轮对话共享此 ID
    session_id: str

    # 运行 ID，标识一次图执行的唯一运行实例
    # 旅行场景举例："run_xyz789"，每次图执行生成新的 run_id
    run_id: Optional[str]

    # 错误信息，当执行过程中出现异常时记录
    # 旅行场景举例："Tool search_attractions failed: API timeout"
    error: Optional[str]


# 【核心】创建初始状态的工厂函数
# 作用：为一次用户交互构建完整的初始状态字典，所有字段设为合理的默认值。
# 这是 LangGraph 图执行的入口——图启动时需要一份"干净"的状态，
# 本函数就是生成这份初始状态的模板。
#
# 参数说明：
#   user_message：用户输入的消息文本，如 "我想去成都玩5天"
#   session_id：会话标识，用于关联同一用户的多轮对话，默认 "default"
#   system_message：可选的系统提示词，会作为 SystemMessage 插入消息列表开头，
#                   用于设定 Agent 的角色和行为规范
#   run_id：可选的运行标识，用于追踪单次图执行实例
#   chat_mode：可选的对话模式，如 "travel"、"casual" 等
def create_initial_state(
    user_message: str,
    session_id: str = "default",
    system_message: Optional[str] = None,
    run_id: Optional[str] = None,
    chat_mode: Optional[str] = None,
) -> AgentState:
    """为一次用户交互构建初始图状态。

    如果提供了 system_message，会先插入系统消息，再插入用户消息，
    确保对话列表以"系统设定 → 用户输入"的顺序开始。
    其余字段全部初始化为 None 或空集合，等待后续节点填充。
    """
    # 构建消息列表：先添加系统提示词（如有），再添加用户消息
    messages: list[BaseMessage] = []
    if system_message:
        messages.append(SystemMessage(content=system_message))
    messages.append(HumanMessage(content=user_message))

    # 返回完整的初始状态，所有字段都有明确的默认值
    # 列表/字典类型默认为空，计数器默认为 0，其余为 None
    return AgentState(
        messages=messages,
        chat_mode=chat_mode,
        intent=None,
        intent_detail=None,
        strategy=None,
        strategy_detail=None,
        routing=None,
        plan_id=None,
        plan_explanation=None,
        plan=None,
        validation_status=None,
        validation_errors=None,
        current_step=0,
        execution_round=0,
        parallelism=None,
        max_parallelism=None,
        execution_state=None,
        execution_stats=None,
        execution_summary=None,
        execution_trace=[],
        execution_budget=None,
        fused_tool_results=None,
        early_stop_reason=None,
        verify_retry_count=0,
        verify_result=None,
        self_check_result=None,
        tools_used=[],
        tool_results={},
        answer=None,
        reasoning=None,
        session_id=session_id,
        run_id=run_id,
        error=None,
    )


# 【核心】旅行 Agent 系统提示词
# 作用：作为 SystemMessage 注入到对话消息列表开头，定义 Agent 的角色、
# 职责、约束和回答风格。LLM 会以此为"人设"指导后续所有回复行为。
#
# 系统提示词的核心要素：
#   1. 角色定义——"你是专业旅行助手"，明确 Agent 的身份
#   2. 职责范围——意图识别、工具调用、结构化输出，划定能力边界
#   3. 约束规则——ReAct 模式、禁止重复调用、高风险信息必须验证，防止幻觉
#   4. 回答风格——先结论后依据、标注不确定性、降级方案，保证回答质量
TRAVEL_AGENT_SYSTEM_PROMPT = """你是专业旅行助手，负责帮助用户完成旅行决策与规划。

你的职责:
1. 准确识别用户意图（推荐、景点、行程、预算、出行建议）。
2. 需要事实时调用工具，不编造工具结果。
3. 输出结构化、可执行、贴近现实的建议。

约束:
1. 遵循 ReAct：Thought -> Action -> Observation。
2. 避免重复调用同一工具同一参数。
3. 价格/政策/签证/退改类高风险信息，必须基于工具验证后回答。

回答风格:
1. 先结论，再依据，再可选方案。
2. 不确定信息要明确标注不确定性。
3. 信息不足时只提出 1-2 个澄清问题。
4. 工具失败时给降级方案，不要中断回复。
"""
