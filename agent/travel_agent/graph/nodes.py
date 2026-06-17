"""
【核心模块】旅游 Agent 图节点实现

本模块是旅游 Agent 的核心节点实现，基于 LangGraph 框架构建完整的对话处理流程。
主要包含以下阶段：

1. 意图识别（intent_node）：分析用户输入，识别旅游意图（推荐/景点/行程/预算/建议等）
2. 策略路由（strategy_node）：根据意图和置信度决定执行路径（plan/react/direct）
3. 计划生成（plan_node）：生成可执行的工具调用计划
4. 工具执行（execute_node）：并行执行工具，支持重试/超时/熔断/预算控制
5. 结果验证（verify_node）：校验工具结果的新鲜度和完整性
6. 回答生成（answer_node / direct_answer_node）：基于工具证据或直接生成回答
7. 自检（self_check_node）：最终回答质量检查

数据模型基于 Pydantic（Python 数据验证库，通过 BaseModel 定义带类型约束的数据结构，
自动进行字段校验和序列化）。异步方法使用 async/await 实现非阻塞并发执行。
"""

# ---- 标准库导入 ----
from __future__ import annotations  # 允许在类型注解中使用前向引用（如方法签名中引用尚未定义的类）

import asyncio  # 异步并发框架，用于并行执行工具调用
import json
import logging
import re
import time
from collections import Counter  # 计数器，用于检测工具调用循环
from datetime import datetime, timezone
from typing import Any, Callable, Literal, Optional  # Literal: 限定变量只能取特定字面值

# ---- 第三方库导入 ----
from pydantic import BaseModel, ValidationError  # BaseModel: Pydantic 数据模型基类，提供字段校验和序列化；ValidationError: 校验失败时抛出的异常
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage  # LangChain 消息类型：AI回复/用户输入/系统提示
from langchain_core.output_parsers import JsonOutputParser  # JSON 输出解析器，将 LLM 输出解析为 Pydantic 模型
from langchain_core.runnables import Runnable  # LangChain 可运行接口，统一 LLM 调用抽象
from langchain_core.tools import Tool  # LangChain 工具定义基类
from langgraph.prebuilt import ToolNode  # LangGraph 预置工具执行节点

# ---- 项目内部导入 ----
from ..pipelines import PlanningPipeline, VerificationPipeline  # 计划生成/验证流水线
from .prompt_templates import build_answer_prompt, build_direct_prompt, build_system_prompt  # 提示词模板构建
from .runtime_config import get_runtime_config  # 运行时配置（超时/重试/预算等参数）
from .state import AgentState, TRAVEL_AGENT_SYSTEM_PROMPT  # Agent 状态定义和系统提示词

logger = logging.getLogger(__name__)

# =====================================================================
# 常量定义区域
# =====================================================================

# ---- 工具执行可靠性参数 ----
DEFAULT_TOOL_TIMEOUT_SECONDS = 20  # 工具默认超时时间（秒），超时后自动终止并标记失败
DEFAULT_TOOL_MAX_RETRIES = 1  # 工具调用默认最大重试次数（不含首次调用）
DEFAULT_TOOL_PARALLELISM = 2  # 工具默认并行度，控制同时执行的工具数量
DEFAULT_TOOL_COOLDOWN_SECONDS = 45  # 熔断器冷却时间（秒），工具连续失败触发熔断后的恢复等待期
DEFAULT_CIRCUIT_BREAKER_THRESHOLD = 3  # 熔断器触发阈值，工具连续失败达到此次数后开启熔断

# ---- 安全相关参数 ----
SENSITIVE_PARAM_KEYS = {"api_key", "token", "authorization", "password", "secret"}  # 敏感参数键名集合，日志中会被脱敏为 ***
PROMPT_INJECTION_PATTERNS = (  # 提示注入攻击模式，检测用户输入中是否包含恶意指令
    "ignore previous instructions",
    "reveal system prompt",
    "show developer message",
    "泄露系统提示词",
    "忽略之前指令",
)
MAX_PARAM_VALUE_LENGTH = 1000  # 参数值最大长度，超出部分在日志中截断
MAX_SAME_TOOL_INVOCATIONS = 2  # 同一工具签名（工具名+参数）在同一轮中最大调用次数，防止死循环

# ---- 业务默认值 ----
DEFAULT_DAY_COUNT = 3  # 默认旅行天数
DEFAULT_PEOPLE_COUNT = 1  # 默认出行人数
DEFAULT_BUDGET_CNY = 3000  # 默认预算（人民币）

# ---- 高风险关键词 ----
HIGH_RISK_KEYWORDS = (  # 高风险查询关键词，涉及价格/政策等需要强验证的信息
    "价格",
    "票价",
    "预算",
    "费用",
    "政策",
    "签证",
    "退改",
    "机票",
    "酒店价格",
)

# ---- 可刷新过期数据的工具集合 ----
STALE_REFRESHABLE_TOOLS = {"get_weather", "query_hotels"}  # 这些工具返回的数据有时效性，验证阶段可触发刷新重试

# ---- 意图-工具策略映射 ----
# 定义每种意图对应的"必需工具"和"可选工具"，以及是否需要验证
# 例如：itinerary（行程规划）意图需要 plan_itinerary 工具，可选 query_attractions/get_weather/query_hotels
INTENT_TOOL_POLICY: dict[str, dict[str, Any]] = {
    "recommend": {"required": ["search_cities"], "optional": ["get_weather", "query_hotels"], "verify_required": False},
    "attractions": {"required": ["query_attractions"], "optional": ["get_weather"], "verify_required": False},
    "itinerary": {"required": ["plan_itinerary"], "optional": ["query_attractions", "get_weather", "query_hotels"], "verify_required": False},
    "budget": {"required": ["calculate_budget"], "optional": ["query_hotels", "get_weather"], "verify_required": True},  # 预算类必须验证
    "tips": {"required": ["get_travel_tips"], "optional": ["get_weather"], "verify_required": False},
    "hotel": {"required": ["query_hotels"], "optional": ["get_weather"], "verify_required": True},  # 酒店类必须验证
    "policy": {"required": [], "optional": ["get_travel_tips"], "verify_required": True},  # 政策类必须验证
    "general": {"required": [], "optional": ["search_cities"], "verify_required": False},
}

# ---- 城市提示列表 ----
# 用于从用户输入中推断目的地城市，支持中英文匹配
CITY_HINTS = [
    "北京",
    "上海",
    "广州",
    "深圳",
    "杭州",
    "南京",
    "苏州",
    "成都",
    "重庆",
    "西安",
    "武汉",
    "长沙",
    "厦门",
    "青岛",
    "大连",
    "三亚",
    "昆明",
    "丽江",
    "大理",
    "拉萨",
    "哈尔滨",
]
EN_CITY_HINTS = [  # 英文城市名列表，与 CITY_HINTS 一一对应，用于英文输入的城市匹配
    "Beijing",
    "Shanghai",
    "Guangzhou",
    "Shenzhen",
    "Hangzhou",
    "Nanjing",
    "Suzhou",
    "Chengdu",
    "Chongqing",
    "Xi'an",
    "Wuhan",
    "Changsha",
    "Xiamen",
    "Qingdao",
    "Dalian",
    "Sanya",
    "Kunming",
    "Lijiang",
    "Dali",
    "Lhasa",
    "Harbin",
]


def _resolve_parallelism_default() -> int:
    """从运行时配置获取默认工具并行度，作为 fallback 值使用。"""
    return get_runtime_config().default_max_parallelism


# =====================================================================
# 数据模型定义（基于 Pydantic BaseModel，提供自动字段校验和序列化）
# =====================================================================

class IntentResult(BaseModel):
    """意图识别结果模型 —— 由 LLM 结构化输出解析而来。

    例如用户输入"成都3日游"，解析结果为：
      intent="itinerary", confidence=0.9, entities={"city":"成都","days":3}, requires_tools=True
    """

    intent: str  # 识别出的意图类型：recommend/attractions/itinerary/budget/tips/general/unclear
    confidence: float  # 置信度（0.0~1.0），低于阈值时走 direct 路由
    entities: dict  # 从用户输入中提取的实体，如城市名、天数、人数等
    requires_tools: bool  # 是否需要调用工具来满足用户需求


class PlanStep(BaseModel):
    """单个可执行计划步骤 —— 由计划生成阶段产出。

    例如：step=1, tool="query_attractions", params={"city":"成都"}, description="查询成都景点"
    """

    step: int  # 步骤序号
    tool: str  # 要调用的工具名称
    params: dict  # 工具调用参数
    description: str  # 步骤描述，用于日志和调试


class ExecutionResult(BaseModel):
    """工具执行结果信封 —— 标准化单次工具调用的结果，包含成功/失败状态和元数据。"""

    success: bool  # 工具是否执行成功
    tool_name: str  # 工具名称
    result: Any  # 工具返回的原始结果数据
    attempt: int = 1  # 当前是第几次尝试（含重试）
    started_at: Optional[str] = None  # 执行开始时间（ISO 格式）
    ended_at: Optional[str] = None  # 执行结束时间（ISO 格式）
    error_code: Optional[str] = None  # 错误码，如 TOOL_TIMEOUT/CIRCUIT_OPEN/DEPENDENCY_FAILED 等
    error: Optional[str] = None  # 错误详情描述
    source: Optional[str] = None  # 数据来源标识，如 "weather_provider"、"hotel_inventory"
    fetched_at: Optional[str] = None  # 数据实际获取时间
    ttl_seconds: Optional[int] = None  # 数据有效期（秒），过期后需刷新
    is_stale: bool = False  # 数据是否已过期
    provider_used: Optional[str] = None  # 实际使用的数据提供者
    provider_chain: Optional[list[str]] = None  # 数据提供者链（主→备）
    fallback_used: bool = False  # 是否使用了备用数据源
    refresh_attempted: bool = False  # 是否尝试了刷新过期数据
    refresh_success: bool = False  # 刷新是否成功
    fallback_suggestion: Optional[str] = None  # 失败时的降级建议文本


class ToolOrchestratorDecision(BaseModel):
    """工具编排器调度决策 —— 描述本轮选中和跳过的工具步骤。"""

    selected: list[dict[str, Any]]  # 本轮被选中执行的工具步骤列表
    skipped: list[dict[str, Any]]  # 被跳过的工具步骤列表（含跳过原因）
    budget_stop_reason: Optional[str] = None  # 预算耗尽时的停止原因说明


class ToolOrchestrator:
    """工具编排器 —— 核心调度组件，负责在预算/并行度/循环检测约束下选择本轮要执行的工具步骤。

    调度逻辑：
    1. 遍历所有可运行步骤（runnable）
    2. 跳过重复签名（同一工具+参数组合在本轮已出现）→ 防止同轮重复
    3. 跳过超限签名（同一签名历史调用次数超过 max_same_invocations）→ 防止死循环
    4. 跳过预算超限步骤（已使用工具数 >= max_tools）→ 控制成本
    5. 选中的步骤数不超过并行度上限（parallel_cap）
    """

    def __init__(self, runtime_config):
        """初始化工具编排器。

        Args:
            runtime_config: 运行时配置对象，包含预算上限、重试策略等参数
        """
        self.runtime_config = runtime_config

    def select(
        self,
        runnable: list[dict[str, Any]],
        trace_counter: Counter,
        signature_getter: Callable[[dict[str, Any]], str],
        max_same_invocations: int,
        requested_parallelism: int,
        max_parallelism: int,
        budget: dict[str, Any],
    ) -> ToolOrchestratorDecision:
        """在循环检测、预算和并行度约束下选择可执行的工具步骤。

        Args:
            runnable: 本轮所有可运行的候选步骤列表
            trace_counter: 签名计数器，记录历史调用次数，用于检测循环
            signature_getter: 回调函数，根据步骤生成稳定签名（工具名+参数哈希）
            max_same_invocations: 同一签名最大允许调用次数
            requested_parallelism: 请求的并行度
            max_parallelism: 最大允许并行度
            budget: 当前预算快照，含 tools_used/max_tools 等字段

        Returns:
            ToolOrchestratorDecision: 包含 selected（选中步骤）、skipped（跳过步骤+原因）、budget_stop_reason
        """
        selected: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []
        seen_signatures: set[str] = set()  # 本轮已见过的步骤签名，用于去重
        tool_used = int(budget.get("tools_used", 0) or 0)  # 当前已使用的工具调用次数
        max_tools = int(budget.get("max_tools", self.runtime_config.round_max_tools) or self.runtime_config.round_max_tools)  # 本轮最大工具调用次数

        # 并行度上限 = min(请求并行度, 最大并行度, 候选步骤数)，至少为1
        parallel_cap = max(1, min(requested_parallelism, max_parallelism, len(runnable)))
        for step in runnable:
            signature = signature_getter(step)
            # 检查1：同轮重复签名 → 跳过
            if signature in seen_signatures:
                skipped.append({**step, "_skip_code": "LOOP_DETECTED", "_skip_reason": f"duplicated signature in round: {signature}"})
                continue
            # 检查2：历史调用次数超限 → 跳过（防止死循环）
            if trace_counter.get(signature, 0) >= max_same_invocations:
                skipped.append({**step, "_skip_code": "LOOP_DETECTED", "_skip_reason": f"repeated signature exceeded limit: {signature}"})
                continue
            # 检查3：工具预算已耗尽 → 跳过
            if tool_used >= max_tools:
                skipped.append({**step, "_skip_code": "ROUND_TOOL_BUDGET_EXCEEDED", "_skip_reason": f"max tools reached: {max_tools}"})
                continue
            # 通过所有检查 → 选中执行
            seen_signatures.add(signature)
            selected.append(step)
            tool_used += 1
            # 达到并行度上限则停止选择
            if len(selected) >= parallel_cap:
                break

        # 如果没有选中任何步骤且存在预算超限的跳过项，记录预算停止原因
        budget_stop_reason = None
        if not selected and any(item.get("_skip_code") == "ROUND_TOOL_BUDGET_EXCEEDED" for item in skipped):
            budget_stop_reason = f"本轮工具预算已达上限({max_tools})，将执行降级策略。"
        return ToolOrchestratorDecision(selected=selected, skipped=skipped, budget_stop_reason=budget_stop_reason)

class StrategyResult(BaseModel):
    """策略路由结果 —— 描述当前查询的工具策略和路由模式。

    三种路由模式：
    - plan: 需要工具执行，走"计划→执行→验证→回答"完整流程
    - react: ReAct 模式，LLM 自主决定工具调用（当前版本与 plan 合并处理）
    - direct: 无需工具，直接由 LLM 生成回答
    """

    strategy: str  # 策略名称，如 "itinerary"、"itinerary+budget"（含次要意图时用+连接）
    primary_intent: str = "general"  # 主意图
    secondary_intent: Optional[str] = None  # 次要意图，如行程查询中同时涉及预算
    required_tools: list[str] = []  # 必需工具列表
    optional_tools: list[str] = []  # 可选工具列表
    requires_verification: bool = False  # 是否需要验证工具结果
    routing: Literal["plan", "react", "direct"] = "direct"  # 路由模式（Literal 限定只能取这三个值）
    reason: str = ""  # 路由决策原因


class VerifyIssue(BaseModel):
    """单个验证问题 —— 验证阶段发现的工具结果缺陷。"""

    issue_type: str  # 问题类型，如 stale_data（数据过期）、incomplete_data（数据不完整）
    message: str  # 问题描述
    severity: Literal["low", "medium", "high"] = "medium"  # 严重程度


class VerifyResult(BaseModel):
    """验证结果 —— 决定是否需要重试工具调用或直接进入回答阶段。"""

    passed: bool  # 验证是否通过
    should_retry: bool = False  # 是否需要重试（刷新过期数据后重新执行）
    refresh_targets: list[str] = []  # 需要刷新的步骤 ID 列表
    refresh_tools: list[str] = []  # 需要刷新的工具名称列表
    issues: list[VerifyIssue] = []  # 发现的问题列表
    summary: str = ""  # 验证摘要


class SelfCheckResult(BaseModel):
    """自检结果 —— 最终回答生成后的质量检查。"""

    passed: bool  # 自检是否通过
    missing_items: list[str] = []  # 缺失项列表，如 empty_answer/incomplete_ending/missing_source_trace
    summary: str = ""  # 自检摘要


# ---- 各阶段输出模型（用于状态校验和类型安全） ----

class IntentStageOutput(BaseModel):
    """意图阶段输出 —— 写入 state 的意图识别结果。"""

    intent: str  # 识别出的意图
    intent_detail: dict[str, Any]  # 意图详情（含 confidence/entities/requires_tools）


class StrategyStageOutput(BaseModel):
    """策略阶段输出 —— 写入 state 的策略路由结果。"""

    strategy: str  # 策略名称
    strategy_detail: dict[str, Any]  # 策略详情（含工具列表/验证要求等）
    routing: Literal["plan", "react", "direct"]  # 路由模式


class PlanStageOutput(BaseModel):
    """计划/执行阶段输出 —— 写入 state 的完整执行结果。"""

    plan_id: str  # 计划唯一标识
    plan_explanation: str  # 计划说明
    plan: list[dict[str, Any]]  # 计划步骤列表
    validation_status: Literal["pass", "warn", "fail"] = "pass"  # 计划校验状态
    validation_errors: list[dict[str, Any]] = []  # 校验错误列表
    current_step: int  # 当前步骤序号
    execution_round: int  # 当前执行轮次
    execution_state: dict[str, Any]  # 执行状态（completed/failed/blocked 步骤集合）
    execution_stats: dict[str, Any]  # 执行统计（步骤明细/成功率/延迟等）
    execution_summary: dict[str, Any]  # 执行汇总
    execution_trace: list[dict[str, Any]]  # 执行轨迹（用于循环检测）
    execution_budget: dict[str, Any]  # 执行预算（tools_used/elapsed_ms/tokens_used）
    fused_tool_results: Optional[dict[str, Any]] = None  # 融合后的工具证据
    early_stop_reason: Optional[str] = None  # 提前停止原因
    verify_retry_count: int = 0  # 验证重试次数
    verify_result: Optional[dict[str, Any]] = None  # 验证结果
    tools_used: list[str]  # 已使用的工具名称列表
    tool_results: dict[str, Any]  # 工具执行结果映射


class AnswerStageOutput(BaseModel):
    """回答阶段输出 —— 写入 state 的最终回答。"""

    messages: list[Any]  # 消息列表（含 AI 回复）
    answer: str  # 生成的回答文本
    reasoning: str  # 推理过程摘要
    fused_tool_results: Optional[dict[str, Any]] = None  # 融合后的工具证据


class VerifyStageOutput(BaseModel):
    """验证阶段输出 —— 写入 state 的验证结果。"""

    verify_result: dict[str, Any]  # 验证结果详情
    verify_retry_count: int  # 验证重试次数
    early_stop_reason: Optional[str] = None  # 提前停止原因


class SelfCheckStageOutput(BaseModel):
    """自检阶段输出 —— 写入 state 的自检结果。"""

    answer: str  # 可能经过修补的回答文本
    self_check_result: dict[str, Any]  # 自检结果详情


class AgentNodes:
    """【核心类】旅游 Agent 图节点实现 —— 封装 LangGraph 工作流中的所有节点方法。

    节点流程：
    用户输入 → intent_node（意图识别）→ strategy_node（策略路由）
        ├─ direct 路由 → direct_answer_node → self_check_node → 返回
        └─ plan/react 路由 → plan_node（计划生成）→ execute_node（工具执行，可循环）
              → verify_node（结果验证）→ answer_node（回答生成）→ self_check_node → 返回

    类属性：
        _GLOBAL_TOOL_HEALTH: 全局工具健康状态字典（跨实例共享），用于熔断器状态管理
    """
    _GLOBAL_TOOL_HEALTH: dict[str, dict[str, Any]] = {}

    def __init__(
        self,
        llm: Runnable,
        tools: list[Tool],
        system_prompt: str | None = None,
        planner_hooks: Optional[dict[str, Callable[[dict], list[dict]]]] = None,
        routing_llm: Optional[Runnable] = None,
    ):
        """初始化 Agent 节点运行时依赖。

        核心初始化内容：
        1. LLM 绑定：主模型（llm）用于推理和回答，路由模型（routing_llm）用于意图/策略判断
        2. 工具注册：构建 tool_map（工具名→工具实例映射）和 ToolNode
        3. 意图结构化输出：尝试构建 with_structured_output 链，不支持时回退到 JSON 解析器
        4. 工具健康追踪：超时 SLA 表、数据源配置表、熔断器状态
        5. 流水线初始化：PlanningPipeline（计划生成）和 VerificationPipeline（结果验证）

        Args:
            llm: 主 LLM 模型（LangChain Runnable 接口），用于推理和回答生成
            tools: 注册的工具列表，供计划/执行阶段使用
            system_prompt: 系统提示词，注入到模型上下文开头
            planner_hooks: 可选的计划器钩子，用于测试/实验中覆盖计划器行为
            routing_llm: 可选的路由模型，用于意图/策略判断（不指定时使用主模型）
        """
        self.llm = llm
        self.routing_llm = routing_llm or llm  # 路由模型，未指定时复用主模型
        self.tools = tools
        self.system_prompt = system_prompt or TRAVEL_AGENT_SYSTEM_PROMPT
        self.tool_map = {tool.name: tool for tool in tools}  # 工具名→工具实例映射，用于按名查找工具
        self._planner_hooks = planner_hooks or {}
        self.runtime_config = get_runtime_config()  # 加载运行时配置
        self._max_same_tool_invocations = MAX_SAME_TOOL_INVOCATIONS  # 同一工具签名最大调用次数
        self.orchestrator = ToolOrchestrator(self.runtime_config)  # 工具编排器实例

        # 构建带工具绑定的 LLM（用于 ReAct 模式）和带结构化输出的意图识别 LLM
        self.llm_with_tools = llm.bind_tools(tools)
        self.llm_with_intent = self._build_intent_structured_llm()
        if self.llm_with_intent is None:
            # 结构化输出不可用时，回退到 JSON 输出解析器
            self.intent_parser = JsonOutputParser(pydantic_object=IntentResult)

        self.tool_node = ToolNode(tools)  # LangGraph 预置工具执行节点
        self._tool_health = AgentNodes._GLOBAL_TOOL_HEALTH  # 引用全局工具健康状态（跨实例共享）
        # 工具超时 SLA 表：每个工具的预期最大响应时间（秒）
        self._tool_timeout_sla: dict[str, int] = {
            "search_cities": 10,
            "query_attractions": 15,
            "query_hotels": 15,
            "calculate_budget": 8,
            "plan_itinerary": 20,
            "get_travel_tips": 8,
            "get_weather": 10,
        }
        # 工具数据源配置表：每个工具的数据来源和有效期（TTL）
        self._tool_source_profile: dict[str, dict[str, Any]] = {
            "search_cities": {"source": "travel_catalog", "ttl_seconds": 86400},  # 旅行目录，24h 有效
            "query_attractions": {"source": "travel_catalog", "ttl_seconds": 21600},  # 6h 有效
            "query_hotels": {"source": "hotel_inventory", "ttl_seconds": 1800},  # 酒店库存，30min 有效
            "calculate_budget": {"source": "budget_ruleset", "ttl_seconds": 86400},  # 预算规则，24h 有效
            "plan_itinerary": {"source": "itinerary_planner", "ttl_seconds": 86400},  # 行程规划，24h 有效
            "get_travel_tips": {"source": "travel_guide", "ttl_seconds": 86400},  # 旅行建议，24h 有效
            "get_weather": {"source": "weather_provider", "ttl_seconds": 1800},  # 天气数据，30min 有效
        }
        # 初始化计划生成流水线
        self.planning_pipeline = PlanningPipeline(
            runtime_config=self.runtime_config,
            tool_names=set(self.tool_map),
            planner_hooks=self._planner_hooks,
            stage_output_model=PlanStageOutput,
            validate_stage_output=self._validate_stage_output,
            build_execution_summary=self._build_execution_summary,
            validation_result_builder=self._build_planning_validation_result,
            step_signature=self._step_signature,
        )
        self.verification_pipeline = VerificationPipeline(
            runtime_config=self.runtime_config,
            refreshable_tools=set(STALE_REFRESHABLE_TOOLS),
            stage_output_model=VerifyStageOutput,
            issue_model=VerifyIssue,
            result_model=VerifyResult,
            validate_stage_output=self._validate_stage_output,
            last_user_text=self._last_user_text,
            is_high_risk_query=self._is_high_risk_query,
        )

    def _build_intent_structured_llm(self) -> Optional[Runnable]:
        """构建意图识别的结构化输出 LLM 链。

        尝试多种结构化输出方法（如 function_calling/json_schema），
        如果模型不支持则返回 None，后续回退到 JSON 文本解析。
        """
        if self._should_disable_structured_intent():
            logger.info("[Intent Node] Structured output disabled for current routing model")
            return None
        for method in self.runtime_config.intent_structured_methods:
            try:
                llm_with_intent = self.routing_llm.with_structured_output(IntentResult, method=method)
                logger.info("[Intent Node] Structured output enabled with method=%s", method)
                return llm_with_intent
            except Exception as exc:
                logger.debug("[Intent Node] Structured output method=%s unavailable: %s", method, exc)

        logger.warning("Structured output unavailable; fallback to JSON parser")
        return None

    def _should_disable_structured_intent(self) -> bool:
        """判断当前路由模型是否应禁用结构化意图解析。

        某些模型（如 MiniMax）不支持结构化输出，需要回退到 JSON 文本解析。
        通过检查模型名称属性来判断模型类型。
        """
        model_markers: list[str] = []
        for attr in ("model", "model_name", "name"):
            value = getattr(self.routing_llm, attr, None)
            if value:
                model_markers.append(str(value).lower())

        model_dump = " ".join(model_markers)
        if "minimax" in model_dump:
            return True
        return False

    @staticmethod
    def _validate_stage_output(model: type[BaseModel], payload: dict[str, Any]) -> dict[str, Any]:
        """使用 Pydantic 模型校验阶段输出数据，确保类型安全后返回字典。

        Args:
            model: 期望的 Pydantic 输出模型类（如 IntentStageOutput）
            payload: 待校验的原始数据字典

        Returns:
            校验通过后的字典数据（model_validate 校验 + model_dump 序列化）
        """
        validated = model.model_validate(payload)
        return validated.model_dump()

    @staticmethod
    def _coerce_llm_content_to_text(content: Any) -> str:
        """将 LLM 输出的异构内容格式统一转为纯文本。

        LLM 输出可能是：纯字符串、字符串列表、含 text/content 键的字典列表。
        此方法统一处理这些格式，提取有效文本内容。

        Args:
            content: LLM 原始输出内容

        Returns:
            提取并拼接后的纯文本字符串
        """
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
                    if isinstance(text, str) and text.strip():
                        parts.append(text)
                        continue
                    nested = item.get("content")
                    if isinstance(nested, str) and nested.strip():
                        parts.append(nested)
            merged = "".join(parts).strip()
            if merged:
                return merged
        return str(content or "").strip()

    def intent_node(self, state: AgentState) -> AgentState:
        """【核心】意图识别节点 —— 分析用户输入，识别旅游意图并提取实体。

        处理流程：
        1. 从 state 中获取最新用户消息
        2. 构建意图识别提示词，要求 LLM 返回 JSON 格式的意图分析结果
        3. 优先使用结构化输出（with_structured_output），失败时回退到 JSON 文本解析
        4. JSON 解析也失败时，使用关键词启发式推断意图
        5. 将识别结果写入 state

        应用场景举例 —— 用户输入"成都3日游"：
        - intent: "itinerary"（行程规划意图）
        - confidence: 0.9（高置信度）
        - entities: {"city": "成都", "days": 3}（提取出城市和天数）
        - requires_tools: True（需要调用 plan_itinerary 等工具）

        Args:
            state: LangGraph 状态快照，包含 messages 等字段

        Returns:
            更新后的状态（含 intent 和 intent_detail 字段）
        """
        logger.info("[Intent Node] Analyzing user intent...")

        messages = state["messages"]
        last_message = messages[-1] if messages else HumanMessage(content="")

        intent_prompt = f"""请分析下面用户旅游咨询的意图。

用户消息: {last_message.content}

可选意图:
- recommend: 需要目的地推荐
- attractions: 查询景点信息
- itinerary: 需要行程规划
- budget: 需要预算估算
- tips: 需要旅行建议
- general: 一般旅游问答
- unclear: 意图不明确

请仅返回 JSON（不要输出多余文本）:
{{
  "intent": "recommend|attractions|itinerary|budget|tips|general|unclear",
  "confidence": 0.0,
  "entities": {{}},
  "requires_tools": false
}}"""

        try:
            intent = "general"  # 默认意图
            intent_detail = {  # 默认意图详情
                "confidence": 0.5,
                "entities": {},
                "requires_tools": False,
            }

            # 优先尝试结构化输出解析
            structured_failed = False
            if self.llm_with_intent:
                try:
                    result = self.llm_with_intent.invoke([SystemMessage(content=intent_prompt)])
                    intent = result.intent
                    intent_detail = {
                        "confidence": result.confidence,
                        "entities": result.entities,
                        "requires_tools": result.requires_tools,
                    }
                except Exception as exc:
                    structured_failed = True
                    logger.warning("[Intent Node] Structured parse failed, fallback to prompt JSON: %s", exc)

            # 结构化输出失败或不可用时，回退到 JSON 文本解析
            if structured_failed or not self.llm_with_intent:
                response = self.routing_llm.invoke([SystemMessage(content=intent_prompt)])
                parsed = self._parse_intent_response_fallback(response, str(last_message.content or ""))
                intent = parsed.get("intent", "general")
                intent_detail = {
                    "confidence": parsed.get("confidence", 0.5),
                    "entities": parsed.get("entities", {}),
                    "requires_tools": parsed.get("requires_tools", False),
                }

            logger.info("[Intent Node] Detected intent=%s", intent)
            return self._validate_stage_output(
                IntentStageOutput,
                {"intent": intent, "intent_detail": intent_detail},
            )
        except Exception as exc:
            # 所有解析方式都失败时，返回默认 general 意图
            logger.warning("[Intent Node] Failed to parse intent: %s", exc)
            return self._validate_stage_output(
                IntentStageOutput,
                {
                    "intent": "general",
                    "intent_detail": {
                        "confidence": 0.5,
                        "entities": {},
                        "requires_tools": False,
                    },
                },
            )

    def _parse_intent_response_fallback(self, response: Any, user_text: str) -> dict[str, Any]:
        """意图 JSON 回退解析 —— 当结构化输出不可用时，从 LLM 文本响应中提取意图。

        解析优先级：
        1. JsonOutputParser 解析（Pydantic 模型校验）
        2. 正则提取首个 JSON 对象后 json.loads 解析
        3. 关键词启发式推断（_infer_intent_by_keywords）

        Args:
            response: LLM 原始响应对象
            user_text: 用户原始输入文本

        Returns:
            解析后的意图字典
        """
        try:
            return self.intent_parser.invoke(response)
        except Exception as parser_exc:
            logger.warning("[Intent Node] JSON parser fallback failed: %s", parser_exc)
            raw_text = self._coerce_llm_content_to_text(getattr(response, "content", response))
            extracted = self._extract_first_json_object(raw_text)
            if extracted:
                try:
                    parsed = json.loads(extracted)
                    if isinstance(parsed, dict):
                        return parsed
                except Exception:
                    pass

        return self._infer_intent_by_keywords(user_text)

    @staticmethod
    def _extract_first_json_object(text: str) -> str:
        """从混合文本中提取第一个 JSON 对象子串。

        LLM 有时在 JSON 前后输出额外文字，此方法定位第一个 { 和最后一个 } 之间的内容。
        """
        if not text:
            return ""
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end < 0 or end <= start:
            return ""
        return text[start : end + 1]

    @staticmethod
    def _infer_intent_by_keywords(user_text: str) -> dict[str, Any]:
        """关键词启发式意图推断 —— 当 LLM 输出无效时，根据关键词匹配推断意图。

        匹配规则（按优先级从高到低）：
        - 包含"预算/费用/花费/价格/票价" → budget 意图
        - 包含"行程/路线/几天/安排/攻略" → itinerary 意图
        - 包含"景点/打卡/必去/门票" → attractions 意图
        - 包含"推荐/去哪/目的地" → recommend 意图
        - 包含"注意/提醒/建议/避坑" → tips 意图
        - 其他 → general 意图
        """
        text = (user_text or "").lower()
        intent = "general"
        requires_tools = False
        confidence = 0.55

        if any(key in text for key in ["预算", "费用", "花费", "价格", "票价"]):
            intent = "budget"
            requires_tools = True
            confidence = 0.8
        elif any(key in text for key in ["行程", "路线", "几天", "安排", "攻略"]):
            intent = "itinerary"
            requires_tools = True
            confidence = 0.8
        elif any(key in text for key in ["景点", "打卡", "必去", "门票"]):
            intent = "attractions"
            requires_tools = True
            confidence = 0.75
        elif any(key in text for key in ["推荐", "去哪", "目的地"]):
            intent = "recommend"
            requires_tools = True
            confidence = 0.72
        elif any(key in text for key in ["注意", "提醒", "建议", "避坑"]):
            intent = "tips"
            confidence = 0.65

        return {
            "intent": intent,
            "confidence": confidence,
            "entities": {},
            "requires_tools": requires_tools,
        }

    def strategy_node(self, state: AgentState) -> AgentState:
        """【核心】策略路由节点 —— 根据意图和置信度决定执行路径和工具策略。

        三种路由模式：
        - plan: 需要工具执行，走"计划→执行→验证→回答"完整流程
          触发条件：意图需要工具（requires_tools=True）或属于 recommend/attractions/itinerary/budget/tips
        - react: ReAct 模式（当前版本与 plan 合并处理，由 routing_decision 进一步区分）
        - direct: 无需工具，直接由 LLM 生成回答
          触发条件：意图不需要工具且置信度较高

        特殊路由规则：
        - 高风险查询（涉及价格/政策等）→ 强制走 plan 路由并要求验证
        - 预算/酒店/政策类意图 → 必须验证（verify_required=True）

        应用场景举例：
        - "成都3日游" → intent=itinerary, requires_tools=True → 路由到 plan
        - "旅游一般注意事项" → intent=tips, requires_tools=False → 路由到 direct
        - "北京酒店价格" → intent=hotel, 高风险 → 强制 plan + 验证

        Args:
            state: LangGraph 状态快照，含 intent/intent_detail 等字段

        Returns:
            更新后的状态（含 strategy/strategy_detail/routing 字段）
        """
        intent = state.get("intent", "general")
        intent_detail = state.get("intent_detail", {})
        requires_tools = bool(intent_detail.get("requires_tools", False))
        confidence = float(intent_detail.get("confidence", 0.0) or 0.0)
        user_text = self._last_user_text(state)
        high_risk = self._is_high_risk_query(user_text, intent)  # 检查是否为高风险查询
        primary_intent = str(intent or "general").lower()
        secondary_intent = self._infer_secondary_intent(primary_intent, user_text, intent_detail)  # 推断次要意图
        strategy = primary_intent if not secondary_intent else f"{primary_intent}+{secondary_intent}"
        required_tools, optional_tools = self._resolve_tool_policy(primary_intent, secondary_intent)  # 解析工具策略
        policy_verify_required = self._is_verify_required(primary_intent, secondary_intent)  # 检查是否需要验证
        reason = "default_strategy"
        # 规则1：高风险查询 → 强制 plan 路由 + 验证
        if high_risk:
            logger.info("[Strategy Node] Routing to plan due to high-risk query (intent=%s)", intent)
            output = StrategyResult(
                strategy=strategy,
                primary_intent=primary_intent,
                secondary_intent=secondary_intent,
                required_tools=required_tools,
                optional_tools=optional_tools,
                requires_verification=True,
                routing="plan",
                reason="high_risk_requires_tool_verification",
            )
            return self._validate_stage_output(
                StrategyStageOutput,
                {
                    "strategy": output.strategy,
                    "strategy_detail": output.model_dump(),
                    "routing": output.routing,
                },
            )

        # 规则2：需要工具或属于特定意图 → plan 路由
        if requires_tools or intent in {"recommend", "attractions", "itinerary", "budget", "tips"}:
            reason = "intent_or_requires_tools"
            output = StrategyResult(
                strategy=strategy,
                primary_intent=primary_intent,
                secondary_intent=secondary_intent,
                required_tools=required_tools,
                optional_tools=optional_tools,
                requires_verification=bool(policy_verify_required),
                routing="plan",
                reason=reason,
            )
            logger.info("[Strategy Node] Routing to plan (intent=%s, requires_tools=%s)", intent, requires_tools)
            return self._validate_stage_output(
                StrategyStageOutput,
                {
                    "strategy": output.strategy,
                    "strategy_detail": output.model_dump(),
                    "routing": output.routing,
                },
            )

        # 规则3：高置信度且不需要工具 → direct 路由
        if confidence >= self.runtime_config.early_stop_confidence_threshold:
            reason = "high_confidence_direct"

        logger.info("[Strategy Node] Routing to direct (intent=%s)", intent)
        output = StrategyResult(
            strategy=strategy,
            primary_intent=primary_intent,
            secondary_intent=secondary_intent,
            required_tools=required_tools,
            optional_tools=optional_tools,
            requires_verification=False,
            routing="direct",
            reason=reason,
        )
        return self._validate_stage_output(
            StrategyStageOutput,
            {
                "strategy": output.strategy,
                "strategy_detail": output.model_dump(),
                "routing": output.routing,
            },
        )

    def router_node(self, state: AgentState) -> AgentState:
        """路由节点 —— 轻量级包装，直接委托给 strategy_node。用于图构建时的节点映射。"""
        return self.strategy_node(state)

    def routing_decision(self, state: AgentState) -> Literal["plan", "react", "direct"]:
        """路由决策方法 —— 根据 state 中的 routing 和 chat_mode 决定条件边的目标节点。

        决策逻辑：
        - routing != "plan" → 返回 "direct"（直接回答路径）
        - routing == "plan" 且 chat_mode == "plan" → 返回 "plan"（计划执行路径）
        - routing == "plan" 且 chat_mode != "plan" → 返回 "react"（ReAct 路径）

        Args:
            state: LangGraph 状态快照

        Returns:
            条件边标签："plan"/"react"/"direct"
        """
        routing = state.get("routing", "direct")
        if routing != "plan":
            return "direct"

        chat_mode = str(state.get("chat_mode") or "react").strip().lower()
        if chat_mode == "plan":
            return "plan"
        return "react"

    def plan_node(self, state: AgentState) -> AgentState:
        """计划生成节点 —— 根据意图和工具策略生成可执行的工具调用计划。

        委托给 PlanningPipeline.build() 执行，包括：
        1. 根据意图确定必需/可选工具
        2. 生成带依赖关系的步骤序列
        3. 校验计划合法性（工具是否注册、参数是否合法）
        4. 返回包含 plan/execution_state/execution_budget 的状态更新
        """
        return self.planning_pipeline.build(state)

    def _build_planning_validation_result(
        self,
        *,
        tool_name: str,
        code: str,
        message: str,
        timestamp: str,
    ) -> dict[str, Any]:
        """构建计划校验失败时的标准化 ExecutionResult。"""
        result = ExecutionResult(
            success=False,
            tool_name=tool_name,
            result="",
            attempt=0,
            error_code=code,
            error=message,
            started_at=timestamp,
            ended_at=timestamp,
        )
        self._attach_execution_metadata(result, tool_name)
        return result.model_dump()

    async def execute_node(self, state: AgentState) -> AgentState:
        """【核心】工具执行节点 —— 执行计划中的工具步骤，支持重试/超时/熔断/预算控制。

        执行流程：
        1. 从 state 中读取计划步骤和执行状态
        2. 处理验证阶段触发的刷新重试（将过期步骤重新标记为待执行）
        3. 筛选可运行步骤（依赖步骤已完成）
        4. 通过 ToolOrchestrator 在预算/并行度/循环检测约束下选择本轮执行步骤
        5. 使用 asyncio.gather 并行执行选中的步骤
        6. 收集执行结果，更新 completed/failed/blocked 状态和执行预算
        7. 检查是否触发早停（预算耗尽/核心步骤已完成）

        可靠性机制：
        - 重试：工具调用失败后按指数退避重试（_run_tool_with_retry）
        - 超时：每个工具有独立的 SLA 超时时间（_tool_timeout_sla）
        - 熔断：工具连续失败达到阈值后暂时屏蔽（_mark_tool_failure/_is_tool_circuit_open）
        - 预算控制：每轮有工具调用次数/耗时/token 数上限（execution_budget）
        - 循环检测：同一工具签名不允许重复调用超过阈值（MAX_SAME_TOOL_INVOCATIONS）

        应用场景举例 —— 执行"成都3日游"计划：
        1. 步骤1: query_attractions(city="成都") → 成功，获取景点列表
        2. 步骤2: get_weather(city="成都") → 成功，获取天气信息
        3. 步骤3: plan_itinerary(destination="成都", days=3) → 依赖步骤1、2完成后执行
        4. 如果步骤2超时 → 标记失败，步骤3仍可执行（非强依赖）

        Args:
            state: LangGraph 状态快照

        Returns:
            更新后的状态（含 execution_state/tool_results/execution_budget 等）
        """
        logger.info("[Execute Node] Executing tools...")

        plan = state.get("plan", []) or []
        execution_state = state.get("execution_state", {}) or {}
        completed = set(execution_state.get("completed", []))  # 已完成的步骤 ID 集合
        failed = set(execution_state.get("failed", []))  # 已失败的步骤 ID 集合
        blocked = set(execution_state.get("blocked", []))  # 被阻塞的步骤 ID 集合
        tool_results = state.get("tool_results", {})  # 工具执行结果映射
        tools_used = state.get("tools_used", [])  # 已使用的工具名称列表
        execution_stats = state.get("execution_stats", {}) or {"steps": []}  # 执行统计
        stats_steps = list(execution_stats.get("steps", []))
        execution_trace = list(state.get("execution_trace", []) or [])  # 执行轨迹
        trace_counter = Counter(item.get("signature") for item in execution_trace if item.get("signature"))  # 签名计数器
        early_stop_reason = state.get("early_stop_reason")
        execution_round = self._safe_int(state.get("execution_round"), 0)  # 当前执行轮次
        execution_budget = dict(state.get("execution_budget") or {})  # 执行预算
        # 初始化预算字段默认值
        execution_budget.setdefault("max_tools", self.runtime_config.round_max_tools)
        execution_budget.setdefault("max_elapsed_ms", self.runtime_config.round_max_elapsed_ms)
        execution_budget.setdefault("max_tokens", self.runtime_config.round_max_tokens)
        execution_budget.setdefault("tools_used", 0)
        execution_budget.setdefault("elapsed_ms", 0)
        execution_budget.setdefault("tokens_used", 0)
        # 成本控制未启用时，放宽预算限制
        if not self.runtime_config.cost_controls_enabled:
            execution_budget["max_tools"] = max(int(execution_budget.get("max_tools", 0) or 0), max(1, len(plan)) * 4)
            execution_budget["max_elapsed_ms"] = max(int(execution_budget.get("max_elapsed_ms", 0) or 0), 1_000_000_000)
            execution_budget["max_tokens"] = max(int(execution_budget.get("max_tokens", 0) or 0), 1_000_000_000)
        verify_result = state.get("verify_result", {}) or {}
        refresh_targets = self._resolve_refresh_targets(verify_result)  # 解析需要刷新的步骤
        # 时效控制未启用时，跳过刷新
        if not self.runtime_config.timeliness_controls_enabled:
            refresh_targets = []
        refresh_target_set = set(refresh_targets)
        verify_result_update: Optional[dict[str, Any]] = None
        if refresh_target_set:
            # 验证阶段要求刷新过期数据：将刷新目标步骤从 completed/failed/blocked 中移除，使其重新执行
            logger.info("[Execute Node] Refresh retry requested for steps=%s", sorted(refresh_target_set))
            for sid in refresh_target_set:
                completed.discard(sid)
                failed.discard(sid)
                blocked.discard(sid)
            verify_result_update = {
                **verify_result,
                "should_retry": False,
                "refresh_targets": [],
                "refresh_tools": [],
            }

        def _with_refresh(payload: dict[str, Any]) -> dict[str, Any]:
            """Refresh stale tool result payloads using fallback params and annotate refresh metadata.
            
            Purpose:
                Explain how this routine updates graph state, tool execution flow, and downstream decision logic.
            
            Args:
                payload: Structured event payload serialized to one SSE data line.
            
            Returns:
                dict[str, Any]: Structured metadata dictionary for downstream stages.
            """
            if verify_result_update is not None:
                payload["verify_result"] = verify_result_update
            return payload

        # 无计划或无待执行步骤时直接返回
        if not plan:
            logger.info("[Execute Node] No plan to execute")
            return _with_refresh(dict(state))

        pending = [s for s in plan if s["step_id"] not in completed and s["step_id"] not in failed and s["step_id"] not in blocked]  # 筛选待执行步骤
        if not pending:
            logger.info("[Execute Node] No pending plan steps")
            return _with_refresh(dict(state))
        # 检查执行轮次上限
        if execution_round >= self.runtime_config.max_execution_rounds:
            logger.warning(
                "[Execute Node] Max execution rounds reached (%d)",
                self.runtime_config.max_execution_rounds,
            )
            return _with_refresh({
                "execution_round": execution_round,
                "execution_budget": execution_budget,
                "early_stop_reason": f"执行回合达到上限({self.runtime_config.max_execution_rounds})，提前结束。",
                "execution_summary": self._build_execution_summary(stats_steps),
            })

        # 筛选可运行步骤：依赖步骤全部已完成
        runnable: list[dict[str, Any]] = []
        for step in pending:
            deps = set(step.get("depends_on", []))
            if deps.issubset(completed):
                runnable.append(self._apply_refresh_params(step, refresh_target_set))  # 应用刷新参数

        if not runnable:
            # 没有可运行步骤 → 检查是否有因依赖失败而被阻塞的步骤
            blocked_steps = []
            for step in pending:
                if set(step.get("depends_on", [])) & failed:
                    blocked_steps.append(step)
            if blocked_steps:
                for step in blocked_steps:
                    sid = step["step_id"]
                    blocked.add(sid)
                    key = f"{sid}:{step.get('tool')}"
                    tool_results[key] = ExecutionResult(
                        success=False,
                        tool_name=step.get("tool", ""),
                        result="",
                        error_code="DEPENDENCY_FAILED",
                        error=f"Dependent step failed: {step.get('depends_on', [])}",
                    ).model_dump()
                    stats_steps.append(
                        {
                            "step_id": sid,
                            "tool": step.get("tool"),
                            "status": "blocked",
                            "error_code": "DEPENDENCY_FAILED",
                            "duration_ms": 0,
                        }
                    )
            return _with_refresh({
                "current_step": len(completed) + len(failed) + len(blocked),
                "execution_round": execution_round + 1,
                "execution_budget": execution_budget,
                "execution_state": {"completed": sorted(completed), "failed": sorted(failed), "blocked": sorted(blocked)},
                "execution_stats": {**execution_stats, "steps": stats_steps},
                "execution_summary": self._build_execution_summary(stats_steps),
                "tool_results": tool_results,
                "tools_used": tools_used,
            })

        # 通过编排器选择本轮执行的步骤（受预算/并行度/循环检测约束）
        default_parallelism = self.runtime_config.default_max_parallelism
        requested_parallelism = self._safe_int(state.get("parallelism"), default_parallelism)
        max_parallelism = self._safe_int(state.get("max_parallelism"), default_parallelism)
        decision = self.orchestrator.select(
            runnable=runnable,
            trace_counter=trace_counter,
            signature_getter=lambda s: self._step_signature(s.get("tool", ""), s.get("params", {})),
            max_same_invocations=self._max_same_tool_invocations,
            requested_parallelism=requested_parallelism,
            max_parallelism=max_parallelism,
            budget=execution_budget,
        )
        selected = decision.selected
        # 处理被编排器跳过的步骤：标记为 blocked 并记录跳过原因
        for step in decision.skipped:
            sid = step["step_id"]
            signature = self._step_signature(step.get("tool", ""), step.get("params", {}))
            blocked.add(sid)
            key = f"{sid}:{step.get('tool')}"
            error_code = str(step.get("_skip_code") or "ORCHESTRATOR_SKIPPED")
            error_reason = str(step.get("_skip_reason") or "Skipped by orchestrator")
            tool_results[key] = ExecutionResult(
                success=False,
                tool_name=step.get("tool", ""),
                result="",
                error_code=error_code,
                error=error_reason,
                started_at=datetime.now().isoformat(),
                ended_at=datetime.now().isoformat(),
            ).model_dump()
            stats_steps.append(
                {
                    "step_id": sid,
                    "tool": step.get("tool"),
                    "status": "blocked",
                    "error_code": error_code,
                    "duration_ms": 0,
                    "signature": signature,
                }
            )
        if decision.budget_stop_reason and not early_stop_reason:
            early_stop_reason = decision.budget_stop_reason

        if not selected:
            return _with_refresh({
                "current_step": len(completed) + len(failed) + len(blocked),
                "execution_round": execution_round + 1,
                "execution_budget": execution_budget,
                "execution_state": {"completed": sorted(completed), "failed": sorted(failed), "blocked": sorted(blocked)},
                "execution_stats": {**execution_stats, "steps": stats_steps},
                "execution_summary": self._build_execution_summary(stats_steps),
                "execution_trace": execution_trace,
                "early_stop_reason": early_stop_reason,
                "tool_results": tool_results,
                "tools_used": tools_used,
            })

        # 并行执行选中的工具步骤（asyncio.gather 实现并发）
        tasks = [self._execute_plan_step(step, state) for step in selected]
        batch_results = await asyncio.gather(*tasks)

        # 收集执行结果，更新状态
        for step, result_obj, elapsed_ms in batch_results:
            step_id = step["step_id"]
            result_key = f"{step_id}:{result_obj.tool_name}"
            tool_results[result_key] = result_obj.model_dump()
            tools_used.append(result_obj.tool_name)
            signature = self._step_signature(result_obj.tool_name, step.get("params", {}))
            if result_obj.success:
                completed.add(step_id)
                self._mark_tool_success(result_obj.tool_name)  # 记录成功，清除熔断计数
            else:
                failed.add(step_id)
                self._mark_tool_failure(result_obj.tool_name)  # 记录失败，更新熔断计数
            execution_trace.append(
                {
                    "step_id": step_id,
                    "tool": result_obj.tool_name,
                    "signature": signature,
                    "status": "success" if result_obj.success else "failed",
                    "timestamp": datetime.now().isoformat(),
                }
            )
            trace_counter[signature] += 1

            stats_steps.append(
                {
                    "step_id": step_id,
                    "tool": result_obj.tool_name,
                    "depends_on": step.get("depends_on", []),
                    "status": "success" if result_obj.success else "failed",
                    "attempt": result_obj.attempt,
                    "error_code": result_obj.error_code,
                    "fallback_used": result_obj.fallback_used,
                    "is_stale": result_obj.is_stale,
                    "refresh_attempted": result_obj.refresh_attempted,
                    "refresh_success": result_obj.refresh_success,
                    "provider_used": result_obj.provider_used,
                    "started_at": result_obj.started_at,
                    "ended_at": result_obj.ended_at,
                    "duration_ms": elapsed_ms,
                    "signature": signature,
                }
            )
            # 更新执行预算消耗
            execution_budget["tools_used"] = int(execution_budget.get("tools_used", 0) or 0) + 1
            execution_budget["elapsed_ms"] = int(execution_budget.get("elapsed_ms", 0) or 0) + int(elapsed_ms)
            execution_budget["tokens_used"] = int(execution_budget.get("tokens_used", 0) or 0) + self._estimate_result_tokens(
                result_obj.result
            )

        execution_summary = self._build_execution_summary(stats_steps)
        updated_execution_state = {"completed": sorted(completed), "failed": sorted(failed), "blocked": sorted(blocked)}
        # 检查成本控制下的预算耗尽
        if self.runtime_config.cost_controls_enabled:
            if int(execution_budget.get("elapsed_ms", 0) or 0) >= int(execution_budget.get("max_elapsed_ms", 0) or 0):
                early_stop_reason = early_stop_reason or f"每轮总耗时预算已达上限({execution_budget.get('max_elapsed_ms')}ms)"
            if int(execution_budget.get("tokens_used", 0) or 0) >= int(execution_budget.get("max_tokens", 0) or 0):
                early_stop_reason = early_stop_reason or f"每轮 token 预算已达上限({execution_budget.get('max_tokens')})"
        if not early_stop_reason:
            early_stop_reason = self._compute_early_stop_reason(
                state=state,
                plan=plan,
                execution_state=updated_execution_state,
                execution_summary=execution_summary,
                tool_results=tool_results,
            )

        return _with_refresh({
            "current_step": len(completed) + len(failed) + len(blocked),
            "execution_round": execution_round + 1,
            "execution_budget": execution_budget,
            "execution_state": updated_execution_state,
            "execution_stats": {**execution_stats, "steps": stats_steps},
            "execution_summary": execution_summary,
            "execution_trace": execution_trace,
            "early_stop_reason": early_stop_reason,
            "tools_used": tools_used,
            "tool_results": tool_results,
        })

    def verify_node(self, state: AgentState) -> AgentState:
        """验证节点 —— 校验工具结果的新鲜度和完整性，决定是否需要重试。

        委托给 VerificationPipeline.build() 执行，主要检查：
        1. 数据是否过期（TTL 超时）
        2. 数据是否完整（关键字段是否缺失）
        3. 是否需要刷新重试（should_retry=True 时触发 execute_node 重新执行过期步骤）
        """
        return self.verification_pipeline.build(state)

    def verify_decision(self, state: AgentState) -> Literal["execute", "answer"]:
        """验证阶段路由决策 —— 决定是回到执行循环还是进入回答阶段。

        - 验证通过（passed=True）→ "answer"
        - 验证未通过但需要重试（should_retry=True）→ "execute"
        - 验证未通过且不需要重试 → "answer"（降级回答）
        """
        result = state.get("verify_result", {}) or {}
        if bool(result.get("passed", False)):
            return "answer"
        if bool(result.get("should_retry", False)):
            return "execute"
        return "answer"

    def self_check_node(self, state: AgentState) -> AgentState:
        """自检节点 —— 最终回答生成后的质量检查，修补明显缺陷。

        检查项：
        - empty_answer: 回答为空
        - incomplete_ending: 回答末尾无标点（自动补句号）
        - missing_source_trace: 使用了工具但回答中缺少数据来源说明
        """
        answer = str(state.get("answer") or "").strip()
        tools_used = list(state.get("tools_used", []) or [])
        missing_items: list[str] = []
        if not answer:
            missing_items.append("empty_answer")
        if answer and answer[-1] not in {"。", ".", "！", "!", "？", "?"}:
            missing_items.append("incomplete_ending")
        if tools_used and "source" not in answer.lower():
            missing_items.append("missing_source_trace")

        passed = len(missing_items) == 0
        summary = "self_check_passed" if passed else f"self_check_failed:{','.join(missing_items)}"
        checked = SelfCheckResult(passed=passed, missing_items=missing_items, summary=summary)
        patched_answer = answer
        if "incomplete_ending" in missing_items:
            patched_answer = f"{answer}。"
        return self._validate_stage_output(
            SelfCheckStageOutput,
            {
                "answer": patched_answer,
                "self_check_result": checked.model_dump(),
            },
        )

    def should_continue(self, state: AgentState) -> Literal["execute", "answer"]:
        """执行循环继续决策 —— 判断是否需要继续执行工具步骤。

        终止条件（返回 "answer"）：
        - 存在早停原因（early_stop_reason）
        - 执行轮次达到上限
        - 所有步骤已完成/失败/阻塞

        继续条件（返回 "execute"）：
        - 仍有未完成的步骤
        """
        if state.get("early_stop_reason"):
            return "answer"
        if self._safe_int(state.get("execution_round"), 0) >= self.runtime_config.max_execution_rounds:
            return "answer"
        plan = state.get("plan", []) or []
        execution_state = state.get("execution_state", {}) or {}
        completed = len(execution_state.get("completed", []))
        failed = len(execution_state.get("failed", []))
        blocked = len(execution_state.get("blocked", []))
        finished = completed + failed + blocked
        return "execute" if finished < len(plan) else "answer"

    def answer_node(self, state: AgentState) -> AgentState:
        """【核心】回答生成节点 —— 基于工具证据和执行上下文生成最终回答。

        处理流程：
        1. 从 state 中提取执行上下文（计划ID、步骤明细、执行汇总、预算消耗等）
        2. 融合工具结果（_fuse_tool_results），按质量和相关性排序
        3. 构建回答提示词，调用 LLM 生成回答
        4. 根据验证结果添加风险提示前缀：
           - 验证未通过 → 添加"暂定建议"提示
           - 数据过期且刷新失败 → 添加"可能过期"提示
        5. 高风险查询时确保回答包含证据来源说明
        6. 将 AI 回复添加到消息列表

        Args:
            state: LangGraph 状态快照

        Returns:
            更新后的状态（含 messages/answer/reasoning/fused_tool_results）
        """
        logger.info("[Answer Node] Generating answer...")

        messages = state["messages"]
        last_message = messages[-1] if messages else HumanMessage(content="")
        intent = state.get("intent")
        tool_results = state.get("tool_results", {})
        tools_used = state.get("tools_used", [])
        plan_id = state.get("plan_id")
        execution_stats = state.get("execution_stats", {}) or {}
        execution_summary = state.get("execution_summary", {}) or {}
        execution_budget = state.get("execution_budget", {}) or {}
        early_stop_reason = state.get("early_stop_reason")
        strategy_detail = state.get("strategy_detail", {}) or {}
        verify_result = state.get("verify_result", {}) or {}
        verify_required = bool(strategy_detail.get("requires_verification", False))
        verify_passed = bool(verify_result.get("passed", False)) if verify_result else False
        user_question = str(last_message.content or "")
        evidence_required = bool(verify_required or self._is_high_risk_query(user_question, str(intent or "")))  # 是否需要证据来源
        fused_tool_results: Optional[dict[str, Any]] = None

        # 构建执行上下文（供 LLM 参考生成回答）
        context = ""
        if plan_id:
            context += f"\n\n## 执行计划 ID:\n{plan_id}\n"
        if execution_stats.get("steps"):
            context += "\n## 步骤执行明细:\n"
            for item in execution_stats.get("steps", []):
                context += (
                    f"- {item.get('step_id')} {item.get('tool')} {item.get('status')}"
                    f" ({item.get('duration_ms', 0)}ms)\n"
                )
        if execution_summary.get("total_steps", 0) > 0:
            context += "\n## 执行汇总:\n"
            context += (
                f"- 总步骤: {execution_summary.get('total_steps', 0)}\n"
                f"- 成功: {execution_summary.get('success_steps', 0)}\n"
                f"- 失败: {execution_summary.get('failed_steps', 0)}\n"
                f"- 阻塞: {execution_summary.get('blocked_steps', 0)}\n"
                f"- 超时: {execution_summary.get('timeout_steps', 0)}\n"
                f"- 回退: {execution_summary.get('fallback_steps', 0)}\n"
                f"- 成功率: {execution_summary.get('success_rate', 0.0):.2f}\n"
                f"- 延迟P95: {(execution_summary.get('latency_percentiles_ms') or {}).get('p95', 0)}ms\n"
            )
        if execution_budget:
            context += "\n## 执行预算:\n"
            context += (
                f"- tools_used/max_tools: {execution_budget.get('tools_used', 0)}/{execution_budget.get('max_tools', 0)}\n"
                f"- elapsed_ms/max_elapsed_ms: {execution_budget.get('elapsed_ms', 0)}/{execution_budget.get('max_elapsed_ms', 0)}\n"
                f"- tokens_used/max_tokens: {execution_budget.get('tokens_used', 0)}/{execution_budget.get('max_tokens', 0)}\n"
            )
        if early_stop_reason:
            context += f"\n## 早停说明:\n- {early_stop_reason}\n"
        if tool_results:
            # 融合工具结果：按质量排序、分组、截断，生成紧凑的证据摘要
            fused = self._fuse_tool_results(tool_results, intent=intent)
            fused_tool_results = fused
            context += "\n\n## 融合后的工具证据\n"
            context += json.dumps(fused, ensure_ascii=False, indent=2)

        prompt = build_answer_prompt(
            user_question=user_question,
            context=context,
            tools_used=tools_used,
            intent=intent,
            evidence_required=evidence_required,
        )

        response = self.llm.invoke([
            SystemMessage(content=build_system_prompt(self.system_prompt, intent)),
            HumanMessage(content=prompt),
        ])

        # 检测验证问题中是否包含数据过期相关问题
        verify_issue_types = {
            str(item.get("issue_type") or "")
            for item in verify_result.get("issues", [])
            if isinstance(item, dict)
        }
        stale_degraded = bool(verify_issue_types & {"stale_data", "stale_refresh_failed", "stale_unrefreshable"})

        answer = self._coerce_llm_content_to_text(response.content)
        # 根据验证状态添加风险提示前缀
        if verify_required and not verify_passed:
            prefix = (
                "当前结论尚未通过工具验证，以下内容仅为暂定建议而非确定结论。"
                "请先补充或刷新关键信息后再做最终决策。"
            )
            if stale_degraded:
                prefix += "天气/酒店实时数据刷新未完全成功，内容可能存在时效偏差。"
            answer = f"{prefix}\n\n{answer}"
        elif stale_degraded and not verify_passed:
            answer = (
                "以下建议可能包含可能过期的数据，系统已尝试刷新但尚未获得稳定实时结果，请谨慎参考。\n\n"
                + str(answer)
            )

        # 高风险查询时确保回答包含证据来源
        if evidence_required:
            answer = self._ensure_source_evidence_section(
                answer=str(answer or ""),
                tool_results=tool_results,
                intent=intent,
            )
        messages = list(messages)
        messages.append(AIMessage(content=answer))

        logger.info("[Answer Node] Answer generated, length=%d", len(answer))
        return self._validate_stage_output(
            AnswerStageOutput,
            {
                "messages": messages,
                "answer": answer,
                "reasoning": self._render_reasoning(state, tools_used),
                "fused_tool_results": fused_tool_results,
            },
        )

    def direct_answer_node(self, state: AgentState) -> AgentState:
        """直接回答节点 —— 无需工具调用时，由 LLM 直接生成回答。

        安全检查：
        - 策略要求验证 → 拒绝直接回答，提示切换到工具验证模式
        - 高风险查询 → 拒绝直接回答，提示切换到工具验证模式
        - 其他情况 → 调用 LLM 生成直接回答

        Args:
            state: LangGraph 状态快照

        Returns:
            更新后的状态（含 messages/answer/reasoning）
        """
        logger.info("[Direct Answer Node] Generating direct answer...")

        messages = state["messages"]
        last_message = messages[-1] if messages else HumanMessage(content="")
        intent = state.get("intent")
        strategy_detail = state.get("strategy_detail", {}) or {}
        if bool(strategy_detail.get("requires_verification", False)):
            answer = "该任务需要工具验证后才能给出确定性结论，请使用 ReAct 工具模式。"
            messages = list(messages)
            messages.append(AIMessage(content=answer))
            return self._validate_stage_output(
                AnswerStageOutput,
                {
                    "messages": messages,
                    "answer": answer,
                    "reasoning": "策略要求强制验证，拒绝直接给出确定性回答。",
                    "fused_tool_results": None,
                },
            )
        if self._is_high_risk_query(str(last_message.content), str(intent)):
            answer = "该问题涉及价格或政策等高风险信息，请切换到工具验证模式后我再给出结论。"
            messages = list(messages)
            messages.append(AIMessage(content=answer))
            return self._validate_stage_output(
                AnswerStageOutput,
                {
                    "messages": messages,
                    "answer": answer,
                    "reasoning": "高风险问题触发强制工具验证。",
                    "fused_tool_results": None,
                },
            )
        prompt = build_direct_prompt(str(last_message.content), intent)

        response = self.llm.invoke([
            SystemMessage(content=build_system_prompt(self.system_prompt, intent)),
            HumanMessage(content=prompt),
        ])

        answer = self._coerce_llm_content_to_text(response.content)
        messages = list(messages)
        messages.append(AIMessage(content=answer))

        logger.info("[Direct Answer Node] Answer generated, length=%d", len(answer))
        return self._validate_stage_output(
            AnswerStageOutput,
            {
                "messages": messages,
                "answer": answer,
                "reasoning": "直接回答（无需工具）",
                "fused_tool_results": None,
            },
        )

    @staticmethod
    async def _invoke_tool(tool: Tool, params: dict) -> Any:
        """调用单个工具，优先使用异步接口（ainvoke），不支持时回退到线程池调用。

        Args:
            tool: LangChain Tool 实例
            params: 工具调用参数

        Returns:
            工具执行结果
        """
        if hasattr(tool, "ainvoke"):
            return await tool.ainvoke(params)
        return await asyncio.to_thread(tool.invoke, params)

    async def _run_tool_with_retry(
        self,
        tool: Tool,
        tool_name: str,
        params: dict,
        timeout_seconds: int,
        max_retries: int,
    ) -> ExecutionResult:
        """带重试/超时/熔断保护的工具执行。

        执行逻辑：
        1. 检查熔断器状态，若已开启则直接返回 CIRCUIT_OPEN 错误
        2. 循环执行（最多 max_retries+1 次）：
           a. 使用 asyncio.wait_for 设置超时
           b. 成功则立即返回
           c. 超时/异常则记录并按指数退避等待后重试
        3. 所有尝试失败后返回错误结果

        Args:
            tool: 工具实例
            tool_name: 工具名称
            params: 调用参数
            timeout_seconds: 超时时间（秒）
            max_retries: 最大重试次数

        Returns:
            ExecutionResult: 标准化的执行结果
        """
        if not self.runtime_config.reliability_controls_enabled:
            attempts = 1
        else:
            attempts = max(1, max_retries + 1)
        last_error: Optional[Exception] = None
        start_ts = datetime.now().isoformat()

        # 熔断器检查：工具已被熔断时直接返回错误
        if self.runtime_config.reliability_controls_enabled and self._is_tool_circuit_open(tool_name):
            now = datetime.now().isoformat()
            return ExecutionResult(
                success=False,
                tool_name=tool_name,
                result="",
                attempt=0,
                error_code="CIRCUIT_OPEN",
                error=f"Circuit breaker open for tool: {tool_name}",
                started_at=start_ts,
                ended_at=now,
            )

        for attempt in range(1, attempts + 1):
            try:
                result = await asyncio.wait_for(self._invoke_tool(tool, params), timeout=timeout_seconds)
                return ExecutionResult(
                    success=True,
                    tool_name=tool_name,
                    result=result,
                    attempt=attempt,
                    started_at=start_ts,
                    ended_at=datetime.now().isoformat(),
                )
            except TimeoutError as exc:
                last_error = exc
                logger.warning("[Execute Node] Tool %s timeout on attempt=%d", tool_name, attempt)
            except Exception as exc:
                last_error = exc
                logger.warning("[Execute Node] Tool %s error on attempt=%d: %s", tool_name, attempt, exc)
            # 重试间按指数退避等待：0.2s, 0.4s, 0.8s...（上限1.5s）
            if attempt < attempts and self.runtime_config.reliability_controls_enabled:
                await asyncio.sleep(min(1.5, 0.2 * (2 ** (attempt - 1))))

        error_code = "TOOL_TIMEOUT" if isinstance(last_error, TimeoutError) else "TOOL_EXECUTION_ERROR"
        return ExecutionResult(
            success=False,
            tool_name=tool_name,
            result="",
            attempt=attempts,
            error_code=error_code,
            error=str(last_error) if last_error else "Unknown tool execution error",
            started_at=start_ts,
            ended_at=datetime.now().isoformat(),
        )

    async def _execute_plan_step(self, step: dict[str, Any], state: AgentState) -> tuple[dict[str, Any], ExecutionResult, int]:
        """执行单个计划步骤 —— 包含参数校验、安全检查、工具调用和元数据附加。

        执行流程：
        1. 自动修正工具参数（_auto_correct_tool_params）
        2. 检查工具是否注册
        3. 校验参数合法性（Pydantic schema 校验）
        4. 检测不安全参数（提示注入/敏感信息）
        5. 调用工具（带重试/超时/熔断保护）
        6. 标准化结果并附加执行元数据

        Args:
            step: 计划步骤描述
            state: LangGraph 状态快照

        Returns:
            (步骤描述, 执行结果, 耗时毫秒数)
        """
        step_id = step.get("step_id", f"step-{step.get('step', 0)}")
        tool_name = str(step.get("tool", ""))
        params = dict(step.get("params", {}) or {})
        timeout_seconds = self._resolve_timeout_seconds(step, tool_name)
        max_retries = int(step.get("max_retries", self.runtime_config.default_tool_max_retries))
        started = time.perf_counter()
        corrected_params = self._auto_correct_tool_params(tool_name, params, state)  # 自动修正参数
        refresh_requested = bool(corrected_params.get("refresh", False))  # 是否为刷新请求
        step_with_params = {**step, "params": corrected_params}

        logger.info("[Execute Node] Step %s running tool=%s timeout=%ss", step_id, tool_name, timeout_seconds)
        tool = self.tool_map.get(tool_name)
        # 检查1：工具是否注册
        if tool is None:
            result = ExecutionResult(
                success=False,
                tool_name=tool_name,
                result="",
                error_code="TOOL_NOT_REGISTERED",
                error=f"Tool not registered: {tool_name}",
                started_at=datetime.now().isoformat(),
                ended_at=datetime.now().isoformat(),
            )
            result.refresh_attempted = refresh_requested
            self._attach_execution_metadata(result, tool_name)
            return step_with_params, result, int((time.perf_counter() - started) * 1000)

        # 检查2：参数合法性校验（Pydantic schema）
        validation_error = self._validate_tool_params(tool, corrected_params)
        if validation_error is not None:
            result = ExecutionResult(
                success=False,
                tool_name=tool_name,
                result="",
                error_code="PARAM_VALIDATION_ERROR",
                error=validation_error,
                started_at=datetime.now().isoformat(),
                ended_at=datetime.now().isoformat(),
            )
            result.refresh_attempted = refresh_requested
            self._attach_execution_metadata(result, tool_name)
            return step_with_params, result, int((time.perf_counter() - started) * 1000)

        # 检查3：安全参数检测（提示注入/敏感信息）
        unsafe_reason = None
        if self.runtime_config.security_controls_enabled:
            unsafe_reason = self._detect_unsafe_params(corrected_params)
        if unsafe_reason is not None:
            result = ExecutionResult(
                success=False,
                tool_name=tool_name,
                result="",
                error_code="UNSAFE_TOOL_INPUT",
                error=unsafe_reason,
                started_at=datetime.now().isoformat(),
                ended_at=datetime.now().isoformat(),
            )
            result.refresh_attempted = refresh_requested
            self._attach_execution_metadata(result, tool_name)
            return step_with_params, result, int((time.perf_counter() - started) * 1000)

        logger.info(
            "[Execute Node] Step %s invoking %s with params=%s",
            step_id,
            tool_name,
            self._sanitize_params_for_log(corrected_params),
        )

        try:
            result = await self._run_tool_with_retry(
                tool=tool,
                tool_name=tool_name,
                params=corrected_params,
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
            )
        except Exception as exc:
            result = ExecutionResult(
                success=False,
                tool_name=tool_name,
                result="",
                error_code="UNEXPECTED_ERROR",
                error=str(exc),
                started_at=datetime.now().isoformat(),
                ended_at=datetime.now().isoformat(),
            )

        result.refresh_attempted = refresh_requested or bool(result.refresh_attempted)
        if refresh_requested and not result.success and not result.fallback_suggestion:
            result.fallback_suggestion = "实时刷新失败，已降级为可能非实时结果，请谨慎决策"
        if result.success:
            result.result = self._normalize_tool_result(tool_name, result.result)
        self._attach_execution_metadata(result, tool_name)
        return step_with_params, result, int((time.perf_counter() - started) * 1000)

    @staticmethod
    def _step_signature(tool_name: str, params: dict[str, Any]) -> str:
        """生成步骤签名（工具名+参数JSON），用于循环检测和去重。

        例如：_step_signature("query_attractions", {"city": "成都"}) → "query_attractions:{\"city\":\"成都\"}"
        """
        try:
            rendered = json.dumps(params, ensure_ascii=False, sort_keys=True)
        except Exception:
            rendered = str(params)
        return f"{tool_name}:{rendered}"

    def _compute_early_stop_reason(
        self,
        state: AgentState,
        plan: list[dict[str, Any]],
        execution_state: dict[str, Any],
        execution_summary: dict[str, Any],
        tool_results: dict[str, Any],
    ) -> Optional[str]:
        """计算确定性早停原因 —— 当核心步骤已完成时提前结束剩余低价值步骤。

        例如：itinerary 意图的核心工具是 plan_itinerary，一旦它成功执行，
        即可提前结束剩余的 get_weather 等可选步骤。
        """
        finished = (
            len(execution_state.get("completed", []))
            + len(execution_state.get("failed", []))
            + len(execution_state.get("blocked", []))
        )
        if finished >= len(plan):
            return None

        intent = str(state.get("intent", "general"))
        terminal_tool = self._terminal_tool_for_intent(intent)
        if not terminal_tool:
            return None

        for item in tool_results.values():
            if not isinstance(item, dict):
                continue
            if item.get("success") and item.get("tool_name") == terminal_tool:
                rate = float(execution_summary.get("success_rate", 0.0))
                return f"核心步骤已完成（{terminal_tool}），提前结束剩余低价值步骤，当前成功率 {rate:.2f}"

        return None

    @staticmethod
    def _resolve_refresh_targets(verify_result: dict[str, Any]) -> list[str]:
        """从验证结果中解析需要刷新的步骤 ID 列表。"""
        if not isinstance(verify_result, dict):
            return []
        if not bool(verify_result.get("should_retry", False)):
            return []
        raw_targets = verify_result.get("refresh_targets", [])
        if not isinstance(raw_targets, list):
            return []
        targets: list[str] = []
        for item in raw_targets:
            step_id = str(item or "").strip()
            if not step_id:
                continue
            if step_id not in targets:
                targets.append(step_id)
        return targets

    @staticmethod
    def _apply_refresh_params(step: dict[str, Any], refresh_targets: set[str]) -> dict[str, Any]:
        """为需要刷新的步骤添加 refresh=True 参数，触发工具重新获取实时数据。"""
        step_id = str(step.get("step_id") or "")
        tool_name = str(step.get("tool") or "")
        if step_id not in refresh_targets or tool_name not in STALE_REFRESHABLE_TOOLS:
            return step
        params = dict(step.get("params", {}) or {})
        params["refresh"] = True
        return {**step, "params": params}

    @staticmethod
    def _terminal_tool_for_intent(intent: str) -> Optional[str]:
        """返回意图对应的核心工具 —— 核心工具成功后可触发早停。

        例如：itinerary → plan_itinerary, budget → calculate_budget
        """
        mapping = {
            "recommend": "search_cities",
            "attractions": "query_attractions",
            "itinerary": "plan_itinerary",
            "budget": "calculate_budget",
            "tips": "get_travel_tips",
            "hotel": "query_hotels",
        }
        return mapping.get(intent)

    @staticmethod
    def _resolve_tool_policy(primary_intent: str, secondary_intent: Optional[str]) -> tuple[list[str], list[str]]:
        """根据主/次意图解析工具策略 —— 合并必需和可选工具列表。

        例如：主意图=itinerary + 次意图=budget →
          required=["plan_itinerary", "calculate_budget"],
          optional=["query_attractions", "get_weather", "query_hotels"]
        """
        primary = INTENT_TOOL_POLICY.get(primary_intent, INTENT_TOOL_POLICY["general"])
        required = list(primary.get("required", []))
        optional = list(primary.get("optional", []))
        if secondary_intent:
            secondary = INTENT_TOOL_POLICY.get(secondary_intent, INTENT_TOOL_POLICY["general"])
            for name in secondary.get("required", []):
                if name not in required:
                    required.append(name)
            for name in secondary.get("optional", []):
                if name not in optional and name not in required:
                    optional.append(name)
        return required, optional

    @staticmethod
    def _is_verify_required(primary_intent: str, secondary_intent: Optional[str]) -> bool:
        """判断当前意图组合是否需要验证 —— 任一意图要求验证即为 True。"""
        primary_required = bool(INTENT_TOOL_POLICY.get(primary_intent, {}).get("verify_required", False))
        secondary_required = bool(INTENT_TOOL_POLICY.get(str(secondary_intent), {}).get("verify_required", False)) if secondary_intent else False
        return primary_required or secondary_required

    @staticmethod
    def _infer_secondary_intent(primary_intent: str, user_text: str, intent_detail: dict[str, Any]) -> Optional[str]:
        """推断次要意图 —— 从用户文本和实体中检测除主意图外的额外需求。

        例如：用户输入"成都3日游大概多少钱" → 主意图=itinerary, 次要意图=budget
        """
        text = str(user_text or "")
        lowered = text.lower()
        entities = intent_detail.get("entities", {}) if isinstance(intent_detail, dict) else {}
        if primary_intent != "budget" and any(token in text for token in ("预算", "花费", "费用", "价格", "票价")):
            return "budget"
        if primary_intent != "budget" and any(token in lowered for token in ("budget", "cost", "price")):
            return "budget"
        if primary_intent != "itinerary" and any(token in text for token in ("行程", "路线", "安排", "几天", "攻略")):
            return "itinerary"
        if primary_intent != "itinerary" and any(token in lowered for token in ("itinerary", "plan", "route")):
            return "itinerary"
        if primary_intent != "hotel" and any(token in text for token in ("酒店", "住宿", "民宿")):
            return "hotel"
        if primary_intent != "attractions" and any(token in text for token in ("景点", "打卡", "门票")):
            return "attractions"
        if any(key in entities for key in ("days", "people", "budget", "budget_cny")) and primary_intent != "budget":
            return "budget"
        if primary_intent == "itinerary":
            return "budget"
        return None

    @staticmethod
    def _is_consecutive_loop(execution_trace: list[dict[str, Any]], signature: str) -> bool:
        """检测连续循环 —— 最近两次执行轨迹是否为同一签名（表示死循环）。"""
        if len(execution_trace) < 2:
            return False
        latest = execution_trace[-2:]
        return all(item.get("signature") == signature for item in latest)

    @staticmethod
    def _is_high_risk_query(text: str, intent: str) -> bool:
        """检测高风险查询 —— 涉及价格/政策等需要强验证的信息。

        判断规则：
        - intent 为 budget → 高风险
        - 文本包含 HIGH_RISK_KEYWORDS 中的关键词 → 高风险
        """
        intent_lower = str(intent or "").lower()
        if intent_lower in {"budget"}:
            return True
        lowered = str(text or "").lower()
        return any(keyword in lowered for keyword in HIGH_RISK_KEYWORDS)

    def _rank_tool_results(
        self,
        tool_results: dict[str, Any],
        intent: Optional[str],
    ) -> list[tuple[str, Any, float]]:
        """按质量分数对工具结果排序 —— 分数越高越可靠。"""
        ranked: list[tuple[str, Any, float]] = []
        for tool_name, result in tool_results.items():
            score = self._score_tool_result(tool_name, result, intent=intent)
            ranked.append((tool_name, result, score))
        ranked.sort(key=lambda item: item[2], reverse=True)
        return ranked

    def _score_tool_result(self, tool_name: str, result: Any, intent: Optional[str]) -> float:
        """计算单个工具结果的质量分数（0.0~1.0）。

        评分维度（加权平均）：
        - freshness（新鲜度）：数据是否过期，TTL 内按衰减计算
        - credibility（可信度）：是否使用备用源、是否有错误码
        - coverage（覆盖度）：是否为意图的核心工具
        """
        if not isinstance(result, dict):
            return 0.0
        if not result.get("success"):
            return 0.0

        # 新鲜度评分：过期数据0.2，TTL内按时间衰减
        freshness = 1.0
        ttl_seconds = result.get("ttl_seconds")
        fetched_at = result.get("fetched_at")
        is_stale = bool(result.get("is_stale", False))
        if is_stale:
            freshness = 0.2
        elif isinstance(ttl_seconds, int) and isinstance(fetched_at, str):
            try:
                fetched_dt = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
                if fetched_dt.tzinfo is None:
                    fetched_dt = fetched_dt.replace(tzinfo=timezone.utc)
                else:
                    fetched_dt = fetched_dt.astimezone(timezone.utc)
                age = (datetime.now(timezone.utc) - fetched_dt).total_seconds()
                freshness = max(0.1, min(1.0, 1.0 - max(0.0, age) / max(1, ttl_seconds)))
            except Exception:
                freshness = 0.8

        # 可信度评分：备用源-0.2，有错误码-0.4，fallback后缀-0.1
        credibility = 1.0
        if result.get("fallback_used"):
            credibility -= 0.2
        if result.get("error_code"):
            credibility -= 0.4
        provider_used = str(result.get("provider_used") or "")
        if provider_used.endswith("fallback"):
            credibility -= 0.1
        credibility = max(0.0, min(1.0, credibility))

        # 覆盖度评分：核心工具1.0，常用工具0.8，其他0.6
        coverage = 0.6
        expected_tool = self._terminal_tool_for_intent(str(intent or ""))
        canonical_tool_name = str(result.get("tool_name") or tool_name).split(":")[-1]
        if expected_tool and expected_tool in canonical_tool_name:
            coverage = 1.0
        elif canonical_tool_name in {"query_attractions", "query_hotels", "get_weather"}:
            coverage = 0.8

        total_weight = (
            self.runtime_config.tool_score_freshness_weight
            + self.runtime_config.tool_score_credibility_weight
            + self.runtime_config.tool_score_coverage_weight
        )
        if total_weight <= 0:
            return 0.0
        score = (
            freshness * self.runtime_config.tool_score_freshness_weight
            + credibility * self.runtime_config.tool_score_credibility_weight
            + coverage * self.runtime_config.tool_score_coverage_weight
        ) / total_weight
        return round(score, 4)

    @staticmethod
    def _estimate_result_tokens(payload: Any) -> int:
        """Estimate token footprint of normalized tool results for budget tracking.
        
        Purpose:
            Explain how this routine updates graph state, tool execution flow, and downstream decision logic.
        
        Args:
            payload: Structured event payload serialized to one SSE data line.
        
        Returns:
            int: Numeric value used by quotas, counts, or status aggregation.
        """
        try:
            text = json.dumps(payload, ensure_ascii=False) if not isinstance(payload, str) else payload
        except Exception:
            text = str(payload)
        return max(1, len(text) // 4)

    @staticmethod
    def _tool_group(tool_name: str) -> str:
        """Map tool names into logical groups for summary and diagnostics display.
        
        Purpose:
            Explain how this routine updates graph state, tool execution flow, and downstream decision logic.
        
        Args:
            tool_name: Registered tool identifier from the tool map.
        
        Returns:
            str: Normalized text string used by downstream logic.
        """
        name = str(tool_name).split(":")[-1]
        if name in {"search_cities", "query_attractions", "query_hotels", "get_weather"}:
            return "discovery"
        if name in {"calculate_budget"}:
            return "budget"
        if name in {"plan_itinerary"}:
            return "planning"
        if name in {"get_travel_tips"}:
            return "advice"
        return "other"

    def _fuse_tool_results(self, tool_results: dict[str, Any], intent: Optional[str]) -> dict[str, Any]:
        """融合多工具输出为紧凑的证据包 —— 按质量排序、分组、截断，供回答生成使用。

        输出结构：
        - groups: 按工具组（discovery/budget/planning/advice）分组，每组最多3条
        - top_evidence: 全局质量最高的5条证据摘要
        """
        ranked = self._rank_tool_results(tool_results, intent=intent)
        groups: dict[str, list[dict[str, Any]]] = {}
        for tool_name, result, score in ranked:
            group = self._tool_group(tool_name)
            groups.setdefault(group, [])
            if not isinstance(result, dict):
                continue
            if not result.get("success"):
                continue
            payload = result.get("result")
            if isinstance(payload, dict) and "report" in payload:
                payload = payload.get("report")
            groups[group].append(
                {
                    "tool_name": str(result.get("tool_name") or tool_name).split(":")[-1],
                    "score": score,
                    "source": result.get("source"),
                    "fetched_at": result.get("fetched_at"),
                    "is_stale": bool(result.get("is_stale", False)),
                    "summary": str(payload)[:900],
                }
            )
        fused: dict[str, Any] = {"groups": {}, "top_evidence": []}
        for group, items in groups.items():
            items.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
            fused["groups"][group] = items[:3]
        for _, result, score in ranked[:5]:
            if not isinstance(result, dict) or not result.get("success"):
                continue
            fused["top_evidence"].append(
                {
                    "tool_name": result.get("tool_name"),
                    "score": score,
                    "source": result.get("source"),
                    "fetched_at": result.get("fetched_at"),
                }
                )
        return fused

    def _build_source_evidence_entries(
        self,
        tool_results: dict[str, Any],
        intent: Optional[str],
        limit: int = 4,
    ) -> list[dict[str, str]]:
        """Build normalized source-evidence entries from tool result metadata.
        
        Purpose:
            Explain how this routine updates graph state, tool execution flow, and downstream decision logic.
        
        Args:
            tool_results: Collection `tool_results` iterated or aggregated by this routine.
            intent: Detected intent label used for SLO bucket aggregation.
            limit: Numeric control parameter `limit` used for bounds or pagination.
        
        Returns:
            list[dict[str, str]]: Computed value returned to the caller.
        """
        ranked = self._rank_tool_results(tool_results, intent=intent)
        entries: list[dict[str, str]] = []
        for tool_name, result, _score in ranked:
            if not isinstance(result, dict) or not bool(result.get("success")):
                continue
            source = str(result.get("source") or "").strip() or "unavailable"
            fetched_at = str(result.get("fetched_at") or "").strip() or "unavailable"
            canonical_name = str(result.get("tool_name") or tool_name).split(":")[-1]
            entries.append(
                {
                    "tool": canonical_name,
                    "source": source,
                    "fetched_at": fetched_at,
                }
            )
            if len(entries) >= limit:
                break

        if entries:
            return entries
        return [{"tool": "unavailable", "source": "unavailable", "fetched_at": "unavailable"}]

    def _ensure_source_evidence_section(
        self,
        answer: str,
        tool_results: dict[str, Any],
        intent: Optional[str],
    ) -> str:
        """Ensure final answer text contains a formatted source-evidence section.
        
        Purpose:
            Explain how this routine updates graph state, tool execution flow, and downstream decision logic.
        
        Args:
            answer: Generated answer text being validated for completeness or post-processing.
            tool_results: Collection `tool_results` iterated or aggregated by this routine.
            intent: Detected intent label used for SLO bucket aggregation.
        
        Returns:
            str: Normalized text string used by downstream logic.
        """
        lowered = str(answer or "").lower()
        if "source" in lowered and "fetched_at" in lowered:
            return str(answer or "")

        entries = self._build_source_evidence_entries(tool_results, intent=intent)
        lines = ["证据来源:"]
        for item in entries:
            lines.append(
                f"- {item['tool']}: source={item['source']}; fetched_at={item['fetched_at']}"
            )
        section = "\n".join(lines)
        base = str(answer or "").rstrip()
        if base:
            return f"{base}\n\n{section}"
        return section

    def _auto_correct_tool_params(self, tool_name: str, params: dict[str, Any], state: AgentState) -> dict[str, Any]:
        """自动修正工具参数 —— 从实体和上下文中推断缺失/无效参数。

        修正逻辑（按工具分类）：
        - search_cities: 补全 query 参数（优先级：params > entities > 推断城市 > 用户文本 > 默认值）
        - query_attractions/query_hotels/get_weather: 补全 city 参数，get_weather 额外补全 days
        - plan_itinerary: 补全 destination/days/interests
        - get_travel_tips: 补全 destination/season
        - calculate_budget: 补全 destination/days/people/accommodation_level/budget_cny

        应用场景举例 —— 用户输入"成都3日游"：
        - plan_itinerary 工具参数自动修正为：destination="成都", days=3
        - 如果用户未指定天数，使用默认值 DEFAULT_DAY_COUNT=3
        """
        corrected = dict(params or {})
        entities = (state.get("intent_detail") or {}).get("entities", {}) or {}
        user_text = self._last_user_text(state)
        inferred_city = self._infer_city(corrected, entities, user_text)

        if tool_name == "search_cities":
            corrected["query"] = self._coalesce_text(
                corrected.get("query"),
                entities.get("query"),
                entities.get("city"),
                inferred_city,
                user_text,
                default="热门目的地",
            )
        elif tool_name in {"query_attractions", "query_hotels", "get_weather"}:
            corrected["city"] = self._coalesce_text(
                corrected.get("city"),
                entities.get("city"),
                entities.get("destination"),
                inferred_city,
                default="北京",
            )
            if tool_name == "get_weather":
                corrected["days"] = self._normalize_int(
                    corrected.get("days", entities.get("days", DEFAULT_DAY_COUNT)),
                    minimum=1,
                    maximum=15,
                    default=DEFAULT_DAY_COUNT,
                )
        elif tool_name in {"plan_itinerary", "get_travel_tips", "calculate_budget"}:
            corrected["destination"] = self._coalesce_text(
                corrected.get("destination"),
                entities.get("destination"),
                entities.get("city"),
                inferred_city,
                default="北京",
            )
            if tool_name == "plan_itinerary":
                corrected["days"] = self._normalize_int(
                    corrected.get("days", entities.get("days", DEFAULT_DAY_COUNT)),
                    minimum=1,
                    maximum=15,
                    default=DEFAULT_DAY_COUNT,
                )
                interests = corrected.get("interests") or entities.get("interests")
                if isinstance(interests, list):
                    corrected["interests"] = ",".join(str(x) for x in interests if str(x).strip())
            if tool_name == "get_travel_tips":
                season = corrected.get("season") or entities.get("season")
                if season:
                    corrected["season"] = str(season).strip()
            if tool_name == "calculate_budget":
                inferred_budget = self._infer_budget_cny(corrected, entities, user_text)
                corrected["days"] = self._normalize_int(
                    corrected.get("days", entities.get("days", DEFAULT_DAY_COUNT)),
                    minimum=1,
                    maximum=30,
                    default=DEFAULT_DAY_COUNT,
                )
                corrected["people"] = self._normalize_int(
                    corrected.get("people", entities.get("people", DEFAULT_PEOPLE_COUNT)),
                    minimum=1,
                    maximum=10,
                    default=DEFAULT_PEOPLE_COUNT,
                )
                corrected["accommodation_level"] = self._normalize_accommodation_level(
                    corrected.get("accommodation_level", entities.get("level", "medium"))
                )
                if inferred_budget is not None:
                    corrected["budget_cny"] = inferred_budget

        sanitized = {k: v for k, v in corrected.items() if v is not None}
        return sanitized

    @staticmethod
    def _infer_budget_cny(params: dict[str, Any], entities: dict[str, Any], user_text: str) -> Optional[int]:
        """从参数/实体/用户文本中推断预算金额（人民币）。

        推断优先级：params.budget_cny > entities.budget_cny > 正则匹配用户文本中的金额
        """
        for source in (params, entities):
            raw = source.get("budget_cny") or source.get("budget")
            if raw is None:
                continue
            try:
                value = int(str(raw).replace(",", "").strip())
                if value > 0:
                    return value
            except Exception:
                continue
        match = re.search(r"(预算|费用|花费)\s*[:：]?\s*(\d{3,7})", user_text or "")
        if match:
            return int(match.group(2))
        return None

    def _normalize_tool_result(self, tool_name: str, payload: Any) -> Any:
        """标准化工具输出 —— 统一货币格式（CNY）、日期格式、评分精度等。"""
        if not isinstance(payload, dict):
            return payload

        normalized = dict(payload)
        report = normalized.get("report")
        if isinstance(report, str):
            normalized["report"] = self._normalize_report_text(report)

        data = normalized.get("data")
        if isinstance(data, list):
            normalized_data: list[Any] = []
            for item in data:
                if isinstance(item, dict):
                    normalized_data.append(self._normalize_result_item(item))
                else:
                    normalized_data.append(item)
            normalized["data"] = normalized_data
        elif isinstance(data, dict):
            normalized["data"] = self._normalize_result_item(data)

        return normalized

    def _normalize_report_text(self, text: str) -> str:
        """标准化报告文本 —— 统一货币符号（NY→CNY、元→CNY、RMB→CNY）和时间单位（天→days、人→travelers）。"""
        normalized = text
        normalized = re.sub(r"(?<!C)NY\s*", "CNY ", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"(\d+)\s*元", r"CNY \1", normalized)
        normalized = re.sub(r"(\d+)\s*人民币", r"CNY \1", normalized)
        normalized = re.sub(r"(\d+)\s*RMB", r"CNY \1", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"(\d{1,2})\s*天", r"\1 days", normalized)
        normalized = re.sub(r"(\d{1,2})\s*人", r"\1 travelers", normalized)
        return normalized

    def _normalize_result_item(self, item: dict[str, Any]) -> dict[str, Any]:
        """递归标准化嵌套结果项 —— 统一 price/ticket 货币格式、日期字符串、评分精度。"""
        normalized = dict(item)
        for key in ("price", "ticket"):
            value = normalized.get(key)
            if isinstance(value, str):
                normalized[key] = self._normalize_report_text(value)
            elif isinstance(value, (int, float)):
                normalized[key] = f"CNY {int(value)}"

        for key in ("hours", "date", "check_in", "check_out"):
            value = normalized.get(key)
            if value is None:
                continue
            normalized[key] = str(value).strip()

        if "rating" in normalized:
            try:
                normalized["rating"] = round(float(normalized["rating"]), 1)
            except Exception:
                pass
        return normalized

    @staticmethod
    def _normalize_int(value: Any, minimum: int, maximum: int, default: int) -> int:
        """安全整数解析 —— 带上下限约束和默认值回退。"""
        try:
            parsed = int(value)
            return min(maximum, max(minimum, parsed))
        except Exception:
            return default

    @staticmethod
    def _safe_int(value: Any, default: int) -> int:
        """安全整数解析 —— 不抛异常，解析失败返回默认值。"""
        try:
            if value is None:
                return default
            return int(value)
        except Exception:
            return default

    @staticmethod
    def _normalize_accommodation_level(value: Any) -> str:
        """标准化住宿等级标签 → economy/medium/luxury。"""
        text = str(value or "").strip().lower()
        if text in {"economy", "budget", "low"}:
            return "economy"
        if text in {"luxury", "high", "premium"}:
            return "luxury"
        return "medium"

    @staticmethod
    def _coalesce_text(*values: Any, default: str = "") -> str:
        """返回第一个非空文本候选 —— 按优先级依次检查多个值，返回第一个有效文本。"""
        for value in values:
            text = str(value or "").strip()
            if text:
                return text
        return default

    @staticmethod
    def _last_user_text(state: AgentState) -> str:
        """从 state 的消息列表中提取最近一条用户消息文本。"""
        messages = list(state.get("messages", []) or [])
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                return str(msg.content or "").strip()
        return ""

    @staticmethod
    def _infer_city(params: dict[str, Any], entities: dict[str, Any], user_text: str) -> str:
        """推断目的地城市 —— 从参数/实体/用户文本中按优先级匹配城市名。

        匹配优先级：
        1. params/entities 中的 city/destination/query 字段 → 精确匹配 CITY_HINTS/EN_CITY_HINTS
        2. 用户文本中包含 CITY_HINTS 中的城市名 → 子串匹配
        3. 用户文本中包含 EN_CITY_HINTS 中的城市名 → 单词边界匹配
        4. 正则匹配中文城市模式（如"成都市旅游"→"成都"）
        5. 正则匹配英文城市模式（如"Chengdu travel"→"Chengdu"）
        """
        for key in ("city", "destination", "query"):
            text = str(params.get(key) or entities.get(key) or "").strip()
            if text in CITY_HINTS:
                return text
            for city in EN_CITY_HINTS:
                if text.lower() == city.lower():
                    return city
        for city in CITY_HINTS:
            if city and city in user_text:
                return city
        lowered = (user_text or "").lower()
        for city in EN_CITY_HINTS:
            if re.search(rf"\b{re.escape(city.lower())}\b", lowered):
                return city
        match = re.search(r"([\u4e00-\u9fff]{2,6})(?:市|旅游|旅行|景点|天气)", user_text or "")
        if match:
            return match.group(1)
        english_match = re.search(
            r"\b([A-Za-z][A-Za-z\s]{1,20})(?:\s+(?:travel|trip|weather|hotel|attractions))\b",
            user_text or "",
            flags=re.IGNORECASE,
        )
        if english_match:
            return english_match.group(1).strip()
        return ""

    def _resolve_timeout_seconds(self, step: dict[str, Any], tool_name: str) -> int:
        """解析工具超时时间 —— 优先使用步骤指定值，否则查 SLA 表，最后用默认值。"""
        override = step.get("timeout_seconds")
        if override is not None:
            return max(1, int(override))
        return self._tool_timeout_sla.get(tool_name, self.runtime_config.default_tool_timeout_seconds)

    def _is_tool_circuit_open(self, tool_name: str) -> bool:
        """检查工具熔断器是否开启 —— 开启时该工具暂时不可用。"""
        if not self.runtime_config.reliability_controls_enabled:
            return False
        item = self._tool_health.get(tool_name)
        if not item:
            return False
        open_until = float(item.get("open_until", 0))
        return time.time() < open_until

    def _mark_tool_failure(self, tool_name: str) -> None:
        """记录工具失败 —— 递增连续失败计数，达到阈值时开启熔断器。

        熔断机制：连续失败 >= circuit_breaker_threshold 时，设置 open_until = 当前时间 + 冷却时间
        """
        if not self.runtime_config.reliability_controls_enabled:
            return
        now = time.time()
        health = self._tool_health.setdefault(tool_name, {"consecutive_failures": 0, "open_until": 0})
        health["consecutive_failures"] = int(health.get("consecutive_failures", 0)) + 1
        if health["consecutive_failures"] >= self.runtime_config.circuit_breaker_threshold:
            health["open_until"] = now + self.runtime_config.tool_cooldown_seconds

    def _mark_tool_success(self, tool_name: str) -> None:
        """记录工具成功 —— 清除连续失败计数，关闭熔断器（恢复可用）。"""
        if not self.runtime_config.reliability_controls_enabled:
            return
        self._tool_health[tool_name] = {"consecutive_failures": 0, "open_until": 0}

    @classmethod
    def get_global_tool_health_snapshot(cls) -> dict[str, Any]:
        """获取全局工具健康快照 —— 跨实例共享的熔断器状态，用于监控和诊断。"""
        now = time.time()
        tools: dict[str, dict[str, Any]] = {}
        for name, item in cls._GLOBAL_TOOL_HEALTH.items():
            open_until = float(item.get("open_until", 0) or 0)
            tools[name] = {
                "consecutive_failures": int(item.get("consecutive_failures", 0) or 0),
                "open_until": open_until,
                "is_circuit_open": now < open_until,
                "cooldown_remaining_seconds": max(0, int(open_until - now)),
            }

        return {
            "tool_count": len(tools),
            "open_circuit_count": sum(1 for item in tools.values() if item["is_circuit_open"]),
            "tools": tools,
        }

    @staticmethod
    def _render_reasoning(state: AgentState, tools_used: list[str]) -> str:
        """渲染推理过程文本 —— 用于 UI 推理面板和流式事件展示。"""
        plan_id = state.get("plan_id")
        stats = state.get("execution_stats", {}) or {}
        step_count = len(stats.get("steps", []))
        if tools_used:
            tool_str = ", ".join(tools_used)
            if plan_id:
                return f"计划 {plan_id} 执行 {step_count} 步，使用工具: {tool_str}"
            return f"使用工具: {tool_str}"
        return "直接回答"

    @staticmethod
    def _validate_tool_params(tool: Tool, params: dict[str, Any]) -> Optional[str]:
        """校验工具参数 —— 使用 Pydantic schema 校验，返回首个错误描述或 None。"""
        schema = getattr(tool, "args_schema", None)
        if schema is None:
            return None
        try:
            schema.model_validate(params)
        except ValidationError as exc:
            first_error = exc.errors()[0] if exc.errors() else {}
            location = ".".join(str(x) for x in first_error.get("loc", []))
            message = first_error.get("msg", str(exc))
            return f"Invalid params for tool: {location} {message}".strip()
        return None

    @staticmethod
    def _detect_unsafe_params(params: dict[str, Any]) -> Optional[str]:
        """检测不安全参数 —— 递归扫描提示注入模式和敏感信息。"""
        def _walk(value: Any) -> list[str]:
            """递归遍历嵌套参数结构，扫描不安全模式。"""
            found: list[str] = []
            if isinstance(value, str):
                text = value.lower()
                for pattern in PROMPT_INJECTION_PATTERNS:
                    if pattern in text:
                        found.append(pattern)
            elif isinstance(value, dict):
                for nested in value.values():
                    found.extend(_walk(nested))
            elif isinstance(value, list):
                for nested in value:
                    found.extend(_walk(nested))
            return found

        matches = _walk(params)
        if not matches:
            return None
        return f"Unsafe tool input detected: {matches[0]}"

    @staticmethod
    def _sanitize_params_for_log(params: dict[str, Any]) -> dict[str, Any]:
        """日志参数脱敏 —— 敏感键值替换为 ***，超长值截断。"""
        def _sanitize(key: Optional[str], value: Any) -> Any:
            """递归脱敏：敏感键→***，超长字符串→截断。"""
            if key and key.lower() in SENSITIVE_PARAM_KEYS:
                return "***"
            if isinstance(value, str):
                if len(value) > MAX_PARAM_VALUE_LENGTH:
                    return f"{value[:MAX_PARAM_VALUE_LENGTH]}...(truncated)"
                return value
            if isinstance(value, dict):
                return {k: _sanitize(k, v) for k, v in value.items()}
            if isinstance(value, list):
                return [_sanitize(key, v) for v in value]
            return value

        return {k: _sanitize(k, v) for k, v in params.items()}

    @staticmethod
    def _build_execution_summary(stats_steps: list[dict[str, Any]]) -> dict[str, Any]:
        """构建执行汇总 —— 包含成功率、延迟分布、重试直方图、错误码分布、工具级指标等。"""
        total_steps = len(stats_steps)
        success_steps = sum(1 for item in stats_steps if item.get("status") == "success")
        failed_steps = sum(1 for item in stats_steps if item.get("status") == "failed")
        blocked_steps = sum(1 for item in stats_steps if item.get("status") == "blocked")
        timeout_steps = sum(1 for item in stats_steps if item.get("error_code") == "TOOL_TIMEOUT")
        fallback_steps = sum(1 for item in stats_steps if bool(item.get("fallback_used", False)))
        stale_result_count = sum(1 for item in stats_steps if bool(item.get("is_stale", False)))
        duration_values = [int(item.get("duration_ms", 0) or 0) for item in stats_steps]
        avg_duration = int(sum(duration_values) / total_steps) if total_steps else 0
        success_rate = (success_steps / total_steps) if total_steps else 0.0
        fallback_rate = (fallback_steps / total_steps) if total_steps else 0.0

        retry_histogram: dict[str, int] = {}
        error_code_distribution: dict[str, int] = {}
        provider_usage_distribution: dict[str, int] = {}
        for item in stats_steps:
            attempt = int(item.get("attempt", 1) or 1)
            retry_histogram[str(attempt)] = retry_histogram.get(str(attempt), 0) + 1

            error_code = item.get("error_code")
            if error_code:
                key = str(error_code)
                error_code_distribution[key] = error_code_distribution.get(key, 0) + 1

            provider_used = item.get("provider_used")
            if provider_used:
                key = str(provider_used)
                provider_usage_distribution[key] = provider_usage_distribution.get(key, 0) + 1

        tool_metrics: dict[str, dict[str, Any]] = {}
        for item in stats_steps:
            tool = str(item.get("tool") or "unknown")
            metric = tool_metrics.setdefault(
                tool,
                {"calls": 0, "success": 0, "failed": 0, "blocked": 0, "timeouts": 0, "avg_duration_ms": 0},
            )
            metric["calls"] += 1
            status = item.get("status")
            if status == "success":
                metric["success"] += 1
            elif status == "failed":
                metric["failed"] += 1
            elif status == "blocked":
                metric["blocked"] += 1
            if item.get("error_code") == "TOOL_TIMEOUT":
                metric["timeouts"] += 1

        for tool, metric in tool_metrics.items():
            tool_durations = [
                int(item.get("duration_ms", 0) or 0)
                for item in stats_steps
                if str(item.get("tool") or "unknown") == tool
            ]
            metric["avg_duration_ms"] = int(sum(tool_durations) / len(tool_durations)) if tool_durations else 0

        latency_percentiles_ms = {
            "p50": AgentNodes._percentile(duration_values, 50),
            "p95": AgentNodes._percentile(duration_values, 95),
            "p99": AgentNodes._percentile(duration_values, 99),
        }

        return {
            "total_steps": total_steps,
            "success_steps": success_steps,
            "failed_steps": failed_steps,
            "blocked_steps": blocked_steps,
            "timeout_steps": timeout_steps,
            "fallback_steps": fallback_steps,
            "stale_result_count": stale_result_count,
            "success_rate": round(success_rate, 4),
            "tool_hit_rate": round(success_rate, 4),
            "fallback_rate": round(fallback_rate, 4),
            "avg_duration_ms": avg_duration,
            "latency_percentiles_ms": latency_percentiles_ms,
            "retry_histogram": retry_histogram,
            "error_code_distribution": error_code_distribution,
            "provider_usage_distribution": provider_usage_distribution,
            "tool_metrics": tool_metrics,
        }

    @staticmethod
    def _percentile(values: list[int], percentile: int) -> int:
        """计算延迟百分位数 —— 用于 P50/P95/P99 延迟统计。"""
        if not values:
            return 0
        sorted_values = sorted(values)
        if percentile <= 0:
            return sorted_values[0]
        if percentile >= 100:
            return sorted_values[-1]
        rank = int(round((percentile / 100) * (len(sorted_values) - 1)))
        return sorted_values[rank]

    def _attach_execution_metadata(self, result: ExecutionResult, tool_name: str) -> None:
        """附加执行元数据 —— 为工具结果添加数据源、TTL、获取时间、提供者等元信息。

        元数据来源优先级：工具返回的 _meta/meta 字段 > _tool_source_profile 配置
        """
        profile = self._tool_source_profile.get(
            tool_name,
            {"source": f"tool:{tool_name}", "ttl_seconds": DEFAULT_TOOL_TIMEOUT_SECONDS * 30},
        )
        result.source = str(profile.get("source", f"tool:{tool_name}"))
        result.ttl_seconds = int(profile.get("ttl_seconds", DEFAULT_TOOL_TIMEOUT_SECONDS * 30))
        result.fetched_at = datetime.now().isoformat()
        result.is_stale = False
        result.refresh_attempted = bool(result.refresh_attempted)
        result.refresh_success = bool(result.refresh_success)
        result_meta = self._extract_result_meta(result.result)
        if result_meta:
            if result_meta.get("source"):
                result.source = str(result_meta.get("source"))
            if result_meta.get("fetched_at"):
                result.fetched_at = str(result_meta.get("fetched_at"))
            if result_meta.get("ttl_seconds") is not None:
                result.ttl_seconds = int(result_meta.get("ttl_seconds"))
            if result_meta.get("is_stale") is not None:
                result.is_stale = bool(result_meta.get("is_stale"))
            if result_meta.get("provider_used") is not None:
                result.provider_used = str(result_meta.get("provider_used"))
            if result_meta.get("provider_chain") is not None:
                result.provider_chain = list(result_meta.get("provider_chain"))
            if result_meta.get("fallback_used") is not None:
                result.fallback_used = bool(result_meta.get("fallback_used"))
            if result_meta.get("refresh_attempted") is not None:
                result.refresh_attempted = bool(result_meta.get("refresh_attempted"))
            if result_meta.get("refresh_success") is not None:
                result.refresh_success = bool(result_meta.get("refresh_success"))
        if result.refresh_attempted and result.success and not result.refresh_success:
            result.refresh_success = not bool(result.is_stale)
        if result.refresh_attempted and not result.success:
            result.refresh_success = False
        if not result.success:
            result.fallback_suggestion = self._build_fallback_suggestion(
                tool_name=tool_name,
                error_code=result.error_code,
            )
        elif result.refresh_attempted and not result.refresh_success:
            result.fallback_suggestion = "已尝试刷新实时数据但未成功，当前结果可能仍过期，建议谨慎参考"
        elif result.is_stale:
            result.fallback_suggestion = "数据可能已过期，建议刷新实时数据后再确认关键决策"

    @staticmethod
    def _extract_result_meta(result_payload: Any) -> dict[str, Any]:
        """从工具原始结果中提取 _meta/meta 元数据字段。"""
        if not isinstance(result_payload, dict):
            return {}
        raw_meta = result_payload.get("_meta") or result_payload.get("meta")
        if not isinstance(raw_meta, dict):
            return {}
        return raw_meta

    @staticmethod
    def _build_fallback_suggestion(tool_name: str, error_code: Optional[str]) -> str:
        """构建用户友好的降级建议 —— 根据错误类型给出不同的处理建议。

        - TOOL_TIMEOUT → 建议使用缓存信息
        - CIRCUIT_OPEN → 建议切换备用数据源
        - TOOL_NOT_FOUND → 建议使用保守回答
        - PARAM_VALIDATION_ERROR → 建议向用户澄清
        - UNSAFE_TOOL_INPUT → 建议清理高风险指令
        - 其他 → 建议降级为规则模板回答
        """
        if error_code == "TOOL_TIMEOUT":
            return f"{tool_name} 超时，建议使用缓存信息或提供不依赖实时数据的备选方案"
        if error_code == "CIRCUIT_OPEN":
            return f"{tool_name} 当前不可用，建议切换备用数据源"
        if error_code in {"TOOL_NOT_FOUND", "TOOL_NOT_REGISTERED"}:
            return "工具配置缺失，建议使用无需工具的保守回答并提示用户补充信息"
        if error_code == "PARAM_VALIDATION_ERROR":
            return "请求参数不完整，建议向用户澄清并补充信息后重试"
        if error_code == "UNSAFE_TOOL_INPUT":
            return "输入触发安全策略，建议清理高风险指令后再执行"
        return f"{tool_name} 执行失败，建议降级为规则模板回答并标注不确定性"


def create_nodes(llm: Runnable, tools: list[Tool]) -> AgentNodes:
    """工厂函数 —— 使用默认运行时配置创建 AgentNodes 实例。"""
    return AgentNodes(llm, tools)
