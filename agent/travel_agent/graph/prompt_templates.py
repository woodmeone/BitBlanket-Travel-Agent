"""提示词构建器与意图专属引导模板模块。

本模块为旅行 Agent 图节点提供提示词（Prompt）的构建能力，包括：
- INTENT_GUIDANCE：各意图类型的回答要求模板，控制 Agent 的输出格式
- INTENT_REACT_PROMPTS：各意图类型的 ReAct 策略提示，控制 Agent 的工具调用行为
- REACT_CONSTRAINTS：ReAct 推理约束规则
- build_system_prompt / build_answer_prompt / build_direct_prompt：提示词构建函数

典型场景：用户问"成都3日游"，意图识别为"itinerary"后，
本模块提供行程规划专用的回答要求（按天排列上午/下午/晚上）
和 ReAct 策略（先收集景点和天气，再生成日程）。
"""

from __future__ import annotations  # 允许在类型注解中使用尚未定义的类型（前向引用）

from typing import Optional  # 可选类型，表示参数可以为 None

# 【核心】意图引导模板 —— 根据不同意图类型，定义 Agent 回答的格式要求
# 每种意图对应一种回答结构，确保输出符合用户预期
INTENT_GUIDANCE: dict[str, str] = {
    "recommend": "先给候选目的地对比（适合人群、季节、预算区间），再给推荐结论。",  # 目的地推荐：如"成都vs重庆3日游，哪个更适合亲子？"
    "attractions": "先给景点清单、开放时间与建议游玩时长，再给动线建议。",  # 景点查询：如"宽窄巷子几点开门？建议玩多久？"
    "itinerary": "先给按天行程（上午/下午/晚上），再给交通与备选方案。",  # 行程规划：如"成都3日游第1天上午去宽窄巷子，下午去武侯祠"
    "budget": "先给分项预算（交通/住宿/门票/餐饮），再给总预算区间与可降本项。",  # 预算测算：如"成都3日游大概要花多少钱？"
    "tips": "先给风险提醒和准备清单，再给可执行注意事项。",  # 旅行建议：如"去成都需要注意什么？"
    "general": "直接回答；信息不足时只补充 1-2 个澄清问题。",  # 通用问答：兜底意图
    "unclear": "先用一句话确认需求，再给可选方向。",  # 意图不明：如用户只说"旅游"
}

# 【核心】意图 ReAct 策略提示 —— 根据不同意图类型，定义 Agent 的工具调用策略
# 控制何时调用工具、优先验证什么信息
INTENT_REACT_PROMPTS: dict[str, str] = {
    "recommend": "你是目的地推荐策略助手。只在缺少事实时调用工具。",  # 推荐场景：优先用已有知识，仅缺少数据时查工具
    "attractions": "你是景点查询策略助手。优先返回可验证的开放时间和票务信息。",  # 景点场景：必须验证开放时间和票价
    "itinerary": "你是行程规划策略助手。先收集景点和天气，再生成日程。",  # 行程场景：先查景点+天气，再排日程
    "budget": "你是预算测算策略助手。涉及价格必须先工具验证再作答。",  # 预算场景：价格信息必须工具验证，避免过时数据
    "tips": "你是旅行建议策略助手。优先给风险规避与操作清单。",  # 建议场景：侧重安全和实操
    "general": "你是通用问答策略助手。无需工具时保持简洁。",  # 通用场景：能不调用工具就不调用
    "unclear": "你是澄清策略助手。优先补齐关键信息。",  # 澄清场景：先搞清楚用户到底想问什么
}

# 【核心】ReAct 推理约束 —— 限制 Agent 的推理和工具调用行为，防止过度调用
# ReAct（Reasoning + Acting）是一种让 LLM 交替进行思考和行动的推理框架
REACT_CONSTRAINTS = """
ReAct 约束：
1. 严格按 Thought -> Action -> Observation 的顺序执行。  # 思考→行动→观察，循环推进
2. 若 Observation 已能支撑结论，不再继续调用工具。  # 避免过度调用，如天气已查到就不再重复查
3. 不得重复调用同一工具同一参数。  # 防止死循环，如不会连续两次查"成都天气"
4. 涉及价格、政策、签证、退改等高风险结论时，必须先有工具验证结果。  # 时效敏感信息必须验证
""".strip()


def build_system_prompt(base_prompt: str, intent: Optional[str]) -> str:
    """【核心】构建运行时系统提示词，拼接策略引导和 ReAct 约束。

    将基础提示词、意图对应的 ReAct 策略、回答要求和 ReAct 约束
    组合为完整的系统提示词，供 LLM 使用。

    典型场景：用户问"成都3日游"，意图识别为"itinerary"，
    系统提示词将包含行程规划策略（先收集景点和天气）和
    按天排列的回答要求。

    Args:
        base_prompt: 基础提示词模板，定义 Agent 的角色和基本行为
        intent: 检测到的意图标签，如 "itinerary"、"budget" 等，为 None 时默认 "general"

    Returns:
        拼接后的完整系统提示词字符串
    """
    intent_key = (intent or "general").lower()  # 意图键值，统一小写，默认 "general"
    guidance = INTENT_GUIDANCE.get(intent_key, INTENT_GUIDANCE["general"])  # 获取对应意图的回答要求
    react_prompt = INTENT_REACT_PROMPTS.get(intent_key, INTENT_REACT_PROMPTS["general"])  # 获取对应意图的 ReAct 策略
    return f"{base_prompt}\n\n任务策略:\n{react_prompt}\n\n回答要求:\n{guidance}\n\n{REACT_CONSTRAINTS}"


def build_answer_prompt(
    user_question: str,  # 用户原始问题，如"帮我规划成都3日游"
    context: str,  # 工具调用结果上下文，如天气数据、景点信息等
    tools_used: list[str],  # 本次使用的工具名称列表，如 ["weather_search", "attraction_search"]
    intent: Optional[str],  # 意图标签，如 "itinerary"
    evidence_required: bool = False,  # 是否强制要求在答案末尾追加证据来源
) -> str:
    """【核心】基于用户问题和工具证据构建答案生成提示词。

    根据是否使用了工具，生成不同结构的提示词：
    - 使用了工具：包含上下文和证据引用要求
    - 未使用工具：直接要求给出可执行建议

    典型场景：用户问"成都3日游"，Agent 调用了天气和景点工具后，
    本函数将工具返回的天气数据、景点信息作为上下文，
    要求 Agent 基于这些证据生成按天排列的行程。

    Args:
        user_question: 用户输入的旅行问题
        context: 工具调用返回的上下文信息（如天气、景点数据）
        tools_used: 本次执行使用的工具名称列表
        intent: 检测到的意图标签
        evidence_required: 是否强制要求在答案中追加证据来源小节

    Returns:
        答案生成提示词字符串
    """
    guidance = INTENT_GUIDANCE.get((intent or "general").lower(), INTENT_GUIDANCE["general"])
    if tools_used:
        # 使用了工具时，要求引用证据来源
        evidence_instruction = (
            '必须在答案末尾追加"证据来源"小节，并逐条包含 `source` 与 `fetched_at` 字段。'
            if evidence_required
            else "请基于工具结果回答，优先引用 source/fetched_at；涉及时效信息时明确日期。"
        )
        return (
            f"用户问题: {user_question}\n\n"
            f"{context}\n\n"
            f"任务类型: {intent or 'general'}\n"
            f"回答要求: {guidance}\n"
            f"{evidence_instruction}"
        )
    # 未使用工具时，直接要求给出建议
    return (
        f"用户问题: {user_question}\n\n"
        f"任务类型: {intent or 'general'}\n"
        f"回答要求: {guidance}\n"
        "请直接给出可执行建议。"
    )


def build_direct_prompt(user_question: str, intent: Optional[str]) -> str:
    """构建直接回答提示词，用于跳过工具编排的场景。

    当 Agent 判断无需调用工具时（如通用问答），使用本函数
    构建简化版提示词，直接要求 LLM 给出回答。

    典型场景：用户问"旅行一般带什么行李"，意图为"general"，
    无需调用天气或景点工具，直接给出通用建议即可。

    Args:
        user_question: 用户输入的旅行问题
        intent: 检测到的意图标签

    Returns:
        直接回答提示词字符串
    """
    guidance = INTENT_GUIDANCE.get((intent or "general").lower(), INTENT_GUIDANCE["general"])
    return (
        f"用户问题: {user_question}\n\n"
        f"任务类型: {intent or 'general'}\n"
        f"回答要求: {guidance}\n"
        "若关键信息不足，请在结尾给出最多 2 个澄清问题。"
    )
