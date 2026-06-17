"""Agent 图执行的运行时配置注册模块。

本模块从环境变量中读取运行时配置，构建不可变的 AgentRuntimeConfig 对象，
控制 Agent 图执行过程中的各类开关和阈值，包括：
- 可靠性/时效性/安全性/成本控制开关
- 流式事件版本和意图结构化方法
- 工具调用的超时、重试、冷却、熔断等参数
- 执行轮次、计划步骤、早停置信度等限制
- 工具评分权重（新鲜度/可信度/覆盖率）

典型场景：部署时通过环境变量配置"成都3日游"Agent 的行为：
- AGENT_MAX_PARALLELISM=3 允许同时调用3个工具
- AGENT_TOOL_TIMEOUT_SECONDS=30 工具超时30秒
- AGENT_CIRCUIT_BREAKER_THRESHOLD=5 连续5次失败后熔断
"""

from __future__ import annotations  # 允许在类型注解中使用尚未定义的类型（前向引用）

import logging
import os
# dataclass：Python 数据类装饰器，自动生成 __init__、__repr__ 等方法
# frozen=True 表示实例不可变（创建后字段不可修改），适合配置对象
# asdict：将 dataclass 实例转为字典，用于序列化
from dataclasses import asdict, dataclass

logger = logging.getLogger(__name__)  # 模块级日志器

# 支持的流式事件协议版本集合
_SUPPORTED_STREAM_EVENT_VERSIONS = {"v1", "v2"}

# 支持的意图结构化提取方法集合
# - json_schema：通过 JSON Schema 约束输出格式（推荐，最精确）
# - function_calling：通过函数调用模拟结构化输出
# - json_mode：仅要求 LLM 输出合法 JSON，不做格式约束
_SUPPORTED_INTENT_STRUCTURED_METHODS = {"json_schema", "function_calling", "json_mode"}


@dataclass(frozen=True)  # frozen=True：实例不可变，创建后字段不可修改，适合配置对象
class AgentRuntimeConfig:
    """Agent 运行时配置的标准化数据类。

    所有字段均从环境变量读取，提供默认值兜底。
    frozen=True 保证配置在运行期间不被意外修改。

    典型场景：Agent 处理"成都3日游"请求时，根据本配置决定：
    - 是否启用可靠性控制（如工具结果校验）
    - 工具调用超时多久
    - 最多执行几轮工具调用
    - 工具评分中新鲜度、可信度、覆盖率各占多少权重
    """

    # ===== 控制开关 =====
    reliability_controls_enabled: bool  # 可靠性控制开关，启用后对工具结果做校验
    timeliness_controls_enabled: bool  # 时效性控制开关，启用后检查数据是否过期
    security_controls_enabled: bool  # 安全性控制开关，启用后过滤敏感信息
    cost_controls_enabled: bool  # 成本控制开关，启用后限制 token 用量和工具调用次数

    # ===== 协议配置 =====
    stream_events_version: str  # 流式事件协议版本，"v1" 或 "v2"
    intent_structured_methods: tuple[str, ...]  # 意图结构化提取方法的优先级元组，如 ("json_schema", "function_calling")

    # ===== 工具调用参数 =====
    default_max_parallelism: int  # 默认最大并行工具调用数，如同时查天气+景点
    default_tool_timeout_seconds: int  # 单次工具调用超时秒数
    default_tool_max_retries: int  # 工具调用失败后的最大重试次数
    tool_cooldown_seconds: int  # 工具调用冷却时间（秒），防止频繁调用同一工具
    circuit_breaker_threshold: int  # 熔断阈值，连续失败次数达到此值后停止调用该工具

    # ===== 执行限制 =====
    max_plan_steps: int  # 行程计划最大步骤数，如成都3日游最多拆分为6个步骤
    max_execution_rounds: int  # 最大执行轮次，每轮可调用多个工具
    early_stop_confidence_threshold: float  # 早停置信度阈值，LLM 置信度超过此值时提前结束

    # ===== 工具评分权重（三者之和应为 1.0）=====
    tool_score_freshness_weight: float  # 新鲜度权重，数据越新分数越高（如今天的天气比上周的更有价值）
    tool_score_credibility_weight: float  # 可信度权重，官方来源比用户评论更可信
    tool_score_coverage_weight: float  # 覆盖率权重，信息越全面分数越高

    # ===== 单轮限制 =====
    round_max_tools: int  # 单轮最大工具调用数
    round_max_elapsed_ms: int  # 单轮最大耗时（毫秒）
    round_max_tokens: int  # 单轮最大 token 消耗

    def to_dict(self) -> dict[str, object]:
        """将 dataclass 字段转为可序列化的字典。

        利用 dataclasses.asdict 自动转换所有字段，
        适用于日志记录、API 响应等场景。

        Returns:
            包含所有配置字段的字典
        """
        return asdict(self)


def _parse_int_env(name: str, default: int, min_value: int = 0) -> int:
    """解析整数类型的环境变量，带下界校验。

    环境变量是操作系统中存储配置的键值对，程序运行时可读取。
    本函数从环境变量读取整数值，若值无效或低于下界则回退到默认值。

    Args:
        name: 环境变量名，如 "AGENT_MAX_PARALLELISM"
        default: 默认值，环境变量未设置或值无效时使用
        min_value: 允许的最小值，低于此值回退到默认值

    Returns:
        解析后的整数值
    """
    raw = str(os.getenv(name, str(default))).strip()  # os.getenv：读取环境变量，不存在时返回默认值
    try:
        value = int(raw)
        if value < min_value:
            raise ValueError(f"value must be >= {min_value}")
        return value
    except Exception:
        logger.warning("Invalid %s=%s, fallback=%s", name, raw, default)  # 记录警告，不抛异常
        return default


def _parse_bool_env(name: str, default: bool) -> bool:
    """解析布尔类型的环境变量，支持显式的 true/false 关键字。

    布尔环境变量可接受的真值：1/true/yes/on
    可接受的假值：0/false/no/off
    其他值回退到默认值并记录警告。

    Args:
        name: 环境变量名，如 "AGENT_RELIABILITY_CONTROLS_ENABLED"
        default: 默认布尔值

    Returns:
        解析后的布尔值
    """
    raw = str(os.getenv(name, str(default))).strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    logger.warning("Invalid %s=%s, fallback=%s", name, raw, default)
    return default


def _resolve_stream_events_version() -> str:
    """解析流式事件协议版本，不支持时回退到默认版本。

    从环境变量 AGENT_STREAM_EVENTS_VERSION 读取版本号，
    仅支持 "v1" 和 "v2"，其他值回退到 "v1"。

    Returns:
        流式事件协议版本字符串，如 "v1"
    """
    raw = str(os.getenv("AGENT_STREAM_EVENTS_VERSION", "v1")).strip().lower()
    if raw in _SUPPORTED_STREAM_EVENT_VERSIONS:
        return raw
    logger.warning("Unsupported AGENT_STREAM_EVENTS_VERSION=%s, fallback=v1", raw)
    return "v1"


def _resolve_intent_structured_methods() -> tuple[str, ...]:
    """构建意图结构化提取方法的优先级回退元组。

    从环境变量 AGENT_INTENT_STRUCTURED_METHOD 读取首选方法，
    然后按优先级排列回退方法（去重保序）。
    若首选方法不在支持列表中，跳过它。

    典型场景：首选 "json_schema"，回退顺序为
    ("json_schema", "function_calling", "json_mode")，
    即优先用 JSON Schema 约束输出，不支持时回退到函数调用模式。

    Returns:
        去重保序的方法元组，如 ("json_schema", "function_calling", "json_mode")
    """
    preferred = str(os.getenv("AGENT_INTENT_STRUCTURED_METHOD", "json_schema")).strip().lower()
    fallback_order = [preferred, "json_schema", "function_calling", "json_mode"]  # 首选优先，其余为回退
    methods: list[str] = []
    for method in fallback_order:
        if method not in _SUPPORTED_INTENT_STRUCTURED_METHODS:
            continue  # 跳过不支持的方法
        if method not in methods:
            methods.append(method)  # 去重保序：已存在则不重复添加
    if not methods:
        methods = ["json_schema", "function_calling", "json_mode"]  # 兜底：全部方法
    return tuple(methods)


def _parse_float_env(name: str, default: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    """解析浮点类型的环境变量，带范围校验。

    用于解析权重、阈值等 0.0~1.0 范围的配置值，
    超出范围时回退到默认值。

    Args:
        name: 环境变量名，如 "AGENT_TOOL_SCORE_FRESHNESS_WEIGHT"
        default: 默认浮点值
        min_value: 允许的最小值（含）
        max_value: 允许的最大值（含）

    Returns:
        解析后的浮点值
    """
    raw = str(os.getenv(name, str(default))).strip()
    try:
        value = float(raw)
        if value < min_value or value > max_value:
            raise ValueError(f"value must be in [{min_value}, {max_value}]")
        return value
    except Exception:
        logger.warning("Invalid %s=%s, fallback=%s", name, raw, default)
        return default


def get_runtime_config() -> AgentRuntimeConfig:
    """【核心】读取环境变量并返回不可变的运行时配置对象。

    所有配置项均从环境变量读取，未设置时使用默认值。
    返回的 AgentRuntimeConfig 实例因 frozen=True 而不可修改，
    保证整个运行周期内配置一致。

    典型场景：Agent 启动时调用此函数获取配置，如：
    - AGENT_MAX_PARALLELISM=3 → 同时查成都天气+景点+酒店
    - AGENT_TOOL_TIMEOUT_SECONDS=30 → 单次工具调用最多等30秒
    - AGENT_CIRCUIT_BREAKER_THRESHOLD=5 → 天气API连续5次失败后熔断

    Returns:
        AgentRuntimeConfig: 不可变的运行时配置实例
    """
    return AgentRuntimeConfig(
        # ===== 控制开关 =====
        reliability_controls_enabled=_parse_bool_env("AGENT_RELIABILITY_CONTROLS_ENABLED", default=True),  # 可靠性控制，默认开启
        timeliness_controls_enabled=_parse_bool_env("AGENT_TIMELINESS_CONTROLS_ENABLED", default=True),  # 时效性控制，默认开启
        security_controls_enabled=_parse_bool_env("AGENT_SECURITY_CONTROLS_ENABLED", default=True),  # 安全性控制，默认开启
        cost_controls_enabled=_parse_bool_env("AGENT_COST_CONTROLS_ENABLED", default=True),  # 成本控制，默认开启

        # ===== 协议配置 =====
        stream_events_version=_resolve_stream_events_version(),  # 流式事件版本，默认 v1
        intent_structured_methods=_resolve_intent_structured_methods(),  # 意图提取方法优先级

        # ===== 工具调用参数 =====
        default_max_parallelism=_parse_int_env("AGENT_MAX_PARALLELISM", default=2, min_value=1),  # 最大并行数，默认2
        default_tool_timeout_seconds=_parse_int_env("AGENT_TOOL_TIMEOUT_SECONDS", default=20, min_value=1),  # 工具超时，默认20秒
        default_tool_max_retries=_parse_int_env("AGENT_TOOL_MAX_RETRIES", default=1, min_value=0),  # 最大重试，默认1次
        tool_cooldown_seconds=_parse_int_env("AGENT_TOOL_COOLDOWN_SECONDS", default=45, min_value=1),  # 冷却时间，默认45秒
        circuit_breaker_threshold=_parse_int_env("AGENT_CIRCUIT_BREAKER_THRESHOLD", default=3, min_value=1),  # 熔断阈值，默认3次

        # ===== 执行限制 =====
        max_plan_steps=_parse_int_env("AGENT_MAX_PLAN_STEPS", default=6, min_value=1),  # 最大计划步骤，默认6步
        max_execution_rounds=_parse_int_env("AGENT_MAX_EXECUTION_ROUNDS", default=8, min_value=1),  # 最大执行轮次，默认8轮
        early_stop_confidence_threshold=_parse_float_env("AGENT_EARLY_STOP_CONFIDENCE", default=0.9, min_value=0.5, max_value=1.0),  # 早停置信度，默认0.9

        # ===== 工具评分权重（三者之和 = 1.0）=====
        tool_score_freshness_weight=_parse_float_env("AGENT_TOOL_SCORE_FRESHNESS_WEIGHT", default=0.4, min_value=0.0, max_value=1.0),  # 新鲜度权重，默认0.4
        tool_score_credibility_weight=_parse_float_env("AGENT_TOOL_SCORE_CREDIBILITY_WEIGHT", default=0.4, min_value=0.0, max_value=1.0),  # 可信度权重，默认0.4
        tool_score_coverage_weight=_parse_float_env("AGENT_TOOL_SCORE_COVERAGE_WEIGHT", default=0.2, min_value=0.0, max_value=1.0),  # 覆盖率权重，默认0.2

        # ===== 单轮限制 =====
        round_max_tools=_parse_int_env("AGENT_ROUND_MAX_TOOLS", default=4, min_value=1),  # 单轮最大工具数，默认4
        round_max_elapsed_ms=_parse_int_env("AGENT_ROUND_MAX_ELAPSED_MS", default=15000, min_value=500),  # 单轮最大耗时，默认15秒
        round_max_tokens=_parse_int_env("AGENT_ROUND_MAX_TOKENS", default=2500, min_value=200),  # 单轮最大token，默认2500
    )
