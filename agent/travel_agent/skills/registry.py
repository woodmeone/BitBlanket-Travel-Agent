"""技能注册表 —— 管理旅行Agent可用的领域技能。

本模块是旅行Agent的"技能目录"，负责注册、查询和筛选Agent可调用的领域技能。
每个技能通过 SkillContract（技能契约）描述其输入/输出、所属子Agent、优先级等元信息，
运行时根据用户意图和上下文自动匹配最合适的技能。

典型流程（以"成都3日游"为例）：
  1. 用户提出"我想去成都玩3天"
  2. SkillRegistry 根据意图信号(destination_discovery)匹配到 CityResearchSkill
  3. CityResearchSkill 调用 search_cities 工具获取成都信息
  4. 后续依次触发 AttractionResearchSkill → PlanSynthesisSkill 等技能链

核心概念：
  - SkillContract：技能契约，定义一个技能的完整规格（输入/输出/优先级/意图信号等）
  - SkillRegistry：运行时注册表，持有所有已启用的技能契约，支持按名称/子Agent查询
  - SubAgent：子Agent，如 research（调研）、planning（规划）、budget（预算）、verification（验证）
"""

from __future__ import annotations

from dataclasses import replace  # dataclass 不可变替换，用于创建修改了部分字段的新实例
from typing import TYPE_CHECKING, Any, Iterable, Optional

# TYPE_CHECKING 是 Python 类型检查的惯用模式：
#   在类型检查工具（如 mypy）运行时导入 Tool 类型，
#   在实际运行时不导入，避免循环依赖或不必要的依赖加载
if TYPE_CHECKING:
    from langchain_core.tools import Tool  # LangChain 工具基类，定义了 name/description/func 等属性
else:
    Tool = Any

from ..contracts import (
    SkillContract,           # 技能契约：定义技能的完整规格
    SkillInputContract,      # 输入契约：定义技能所需的上下文字段
    SkillMarketMetadata,     # 市场元数据：技能的版本、文档路径、标签等
    SkillOutputContract,     # 输出契约：定义技能产出的制品和字段
    SkillSelectionPolicy,    # 选择策略：定义技能的优先级、意图信号、偏好上下文
)

# ---- 技能市场文档和测试固件的路径常量 ----
_SKILL_CATALOG_DOC = "docs/reference/skills-market-catalog.md"        # 技能市场目录文档
_SKILL_ONBOARDING_DOC = "docs/governance/skills-market-onboarding.md" # 技能入驻指南文档
_SKILL_PROMPT_ANCHOR = "agent/travel_agent/graph/state.py::TRAVEL_AGENT_SYSTEM_PROMPT"  # Agent系统提示词锚点
_SKILL_EVAL_FIXTURE = "tests/test_skill_registry_unit.py"             # 评估测试固件
_SKILL_TEST_FIXTURE = "tests/test_skill_registry_unit.py"             # 单元测试固件


class SkillRegistry:
    """【核心】运行时技能注册表，持有所有已启用的技能契约。

    职责：
      - 注册/替换技能契约（register）
      - 按名称查询技能（get）
      - 按子Agent筛选技能（for_subagent）
      - 导出诊断信息（to_dict）

    示例：注册表就像一个"技能超市"，Agent根据用户需求到超市里挑选合适的技能。
    """

    def __init__(self, skills: Optional[Iterable[SkillContract]] = None):
        """初始化注册表，可选地预加载一批技能契约。

        Args:
            skills: 可选的技能契约迭代器，初始化时批量注册
        """
        self._skills: dict[str, SkillContract] = {}  # 技能名 → 技能契约的映射
        for skill in skills or []:
            self.register(skill)

    def register(self, skill: SkillContract) -> None:
        """注册或替换一个技能契约（按名称去重）。

        若已存在同名技能，则覆盖旧契约。

        Args:
            skill: 要注册的技能契约
        """
        self._skills[skill.name] = skill

    def get(self, name: str) -> Optional[SkillContract]:
        """按名称查询技能契约。

        Args:
            name: 技能名称，如 "CityResearchSkill"

        Returns:
            匹配的技能契约，未找到则返回 None
        """
        return self._skills.get(name)

    def all_skills(self) -> list[SkillContract]:
        """返回所有已注册技能，按名称字典序排列（保证确定性输出）。

        Returns:
            排序后的技能契约列表
        """
        return [self._skills[name] for name in sorted(self._skills)]

    def for_subagent(self, subagent: str) -> list[SkillContract]:
        """【核心】筛选指定子Agent可消费的技能。

        每个技能契约的 allowed_subagents 字段声明了哪些子Agent可以使用该技能。
        例如：CityResearchSkill 只允许 research 子Agent使用。

        Args:
            subagent: 子Agent名称，如 "research"、"planning"、"budget"

        Returns:
            该子Agent可用的技能列表
        """
        return [skill for skill in self.all_skills() if subagent in skill.allowed_subagents]

    def to_dict(self) -> dict[str, dict[str, object]]:
        """导出为 JSON 可序列化的技能映射，用于诊断和调试。

        Returns:
            技能名 → 技能字典的映射
        """
        return {skill.name: skill.to_dict() for skill in self.all_skills()}

    def __len__(self) -> int:
        """返回已注册技能的数量。"""
        return len(self._skills)


def build_default_skill_registry(tools: Optional[Iterable[Tool]] = None) -> SkillRegistry:
    """【核心】构建默认技能注册表，根据当前可用的工具集过滤技能。

    流程：
      1. 解析可用工具名称集合
      2. 遍历默认技能目录
      3. 过滤掉工具不可用的技能（即技能声明的 tool_names 中无可用工具）
      4. 注册剩余技能

    Args:
        tools: LangChain Tool 可迭代对象，若为 None 则注册所有默认技能

    Returns:
        填充好的 SkillRegistry 实例
    """
    available_tool_names = _resolve_tool_names(tools)
    registry = SkillRegistry()
    for spec in _default_skill_contracts():
        if available_tool_names:
            # 只保留当前环境中可用的工具名
            filtered_tool_names = [name for name in spec.tool_names if name in available_tool_names]
            if not filtered_tool_names:
                # 该技能所需工具全部不可用，跳过此技能
                continue
            # 用 dataclasses.replace 创建修改了 tool_names 的新契约实例
            spec = replace(spec, tool_names=filtered_tool_names)
        registry.register(spec)
    return registry


def _resolve_tool_names(tools: Optional[Iterable[Tool]]) -> set[str]:
    """从 LangChain Tool 迭代器中提取工具名称集合。

    LangChain Tool 对象有 name 属性标识工具名称（如 "search_cities"）。

    Args:
        tools: LangChain Tool 可迭代对象

    Returns:
        工具名称集合
    """
    if tools is None:
        return set()
    tool_names: set[str] = set()
    for tool in tools:
        name = getattr(tool, "name", None)  # 安全获取 name 属性
        if isinstance(name, str) and name.strip():
            tool_names.add(name)
    return tool_names


def _default_skill_contracts() -> list[SkillContract]:
    """【核心】返回第一阶段的默认技能目录。

    技能目录定义了旅行Agent的全部领域技能，每个技能包含：
      - name: 技能名称
      - description: 技能描述
      - tool_names: 依赖的工具列表（LangChain Tool 名称）
      - allowed_subagents: 允许使用该技能的子Agent列表
      - input_contract: 输入契约（必需/可选上下文）
      - output_contract: 输出契约（产出制品和字段）
      - selection_policy: 选择策略（优先级、意图信号、偏好上下文）
      - market_metadata: 市场元数据（版本、文档、标签等）

    技能按优先级(priority)从低到高排列，数值越低越优先被选中。
    """
    return [
        # ============================================================
        # 技能1：城市调研技能
        # 场景：用户说"我想去成都玩"，Agent需要先发现候选目的地
        # ============================================================
        SkillContract(
            name="CityResearchSkill",
            description="Discover and shortlist candidate destinations from user intent.",
            tool_names=["search_cities"],  # 依赖 search_cities 工具
            allowed_subagents=["research"],  # 仅 research 子Agent可用
            input_contract=SkillInputContract(
                required_context=["user_intent"],  # 必需：用户意图（如"想去成都"）
                optional_context=["budget_preferences", "companion_profile", "season"],  # 可选：预算/同伴/季节
            ),
            output_contract=SkillOutputContract(
                artifact="ResearchDossier",  # 产出制品：调研档案
                fields=["candidateDestinations", "selectionReasons", "citySignals"],  # 候选城市/选择理由/城市信号
            ),
            output_artifact="ResearchDossier",
            market_metadata=SkillMarketMetadata(
                owner="research-subagent",  # 技能所有者
                version="2026.03",
                docs_path=_SKILL_CATALOG_DOC,
                test_fixture=_SKILL_TEST_FIXTURE,
                prompt_asset=_SKILL_PROMPT_ANCHOR,
                eval_fixture=_SKILL_EVAL_FIXTURE,
                tags=["research", "destination-discovery", "artifact-first"],
            ),
            selection_policy=SkillSelectionPolicy(
                priority=10,  # 最高优先级（数值越低越优先）
                intent_signals=["destination_discovery", "where_to_go", "city_shortlist"],  # 意图信号关键词
                preferred_context=["user_intent", "budget_preferences"],  # 偏好上下文
                notes=["Use first when the run still needs candidate destinations."],
            ),
            metadata={"onboarding_doc": _SKILL_ONBOARDING_DOC},
        ),
        # ============================================================
        # 技能2：景点调研技能
        # 场景：已确定去成都，需要收集景点级证据（如宽窄巷子、锦里等）
        # ============================================================
        SkillContract(
            name="AttractionResearchSkill",
            description="Collect attraction-level evidence for candidate destinations.",
            tool_names=["query_attractions"],  # 依赖 query_attractions 工具
            allowed_subagents=["research"],
            input_contract=SkillInputContract(
                required_context=["candidate_destinations"],  # 必需：候选目的地列表
                optional_context=["travel_style", "must_visit_preferences"],  # 可选：旅行风格/必游偏好
            ),
            output_contract=SkillOutputContract(
                artifact="ResearchDossier",
                fields=["attractionEvidence", "openingHours", "supportingFacts"],  # 景点证据/开放时间/支撑事实
            ),
            output_artifact="ResearchDossier",
            freshness_policy="prefer_recent",  # 新鲜度策略：优先使用最新数据
            market_metadata=SkillMarketMetadata(
                owner="research-subagent",
                version="2026.03",
                docs_path=_SKILL_CATALOG_DOC,
                test_fixture=_SKILL_TEST_FIXTURE,
                prompt_asset=_SKILL_PROMPT_ANCHOR,
                eval_fixture=_SKILL_EVAL_FIXTURE,
                tags=["research", "attractions", "evidence"],
            ),
            selection_policy=SkillSelectionPolicy(
                priority=20,  # 次高优先级（在城市调研之后）
                intent_signals=["attractions", "must_visit", "poi"],  # poi = Point of Interest 兴趣点
                preferred_context=["candidate_destinations", "must_visit_preferences"],
                notes=["Promote after destination shortlist exists and POI detail matters."],
            ),
            metadata={"onboarding_doc": _SKILL_ONBOARDING_DOC},
        ),
        # ============================================================
        # 技能3：天气查询技能
        # 场景：规划"成都3日游"时，需确认出行日期的天气情况
        # 特点：跨子Agent使用（research/planning/verification均可调用）
        # ============================================================
        SkillContract(
            name="WeatherLookupSkill",
            description="Inject weather and seasonality evidence into planning decisions.",
            tool_names=["get_weather"],  # 依赖 get_weather 工具
            allowed_subagents=["research", "planning", "verification"],  # 多个子Agent可使用
            input_contract=SkillInputContract(
                required_context=["candidate_destinations"],
                optional_context=["travel_dates", "season", "route_constraints"],  # 旅行日期/季节/路线约束
            ),
            output_contract=SkillOutputContract(
                artifact="ResearchDossier",
                fields=["weatherSignals", "seasonalityNotes", "staleWarnings"],  # 天气信号/季节性备注/过期警告
            ),
            output_artifact="ResearchDossier",
            freshness_policy="must_refresh_if_stale",  # 新鲜度策略：数据过期时必须刷新
            market_metadata=SkillMarketMetadata(
                owner="research-subagent",
                version="2026.03",
                docs_path=_SKILL_CATALOG_DOC,
                test_fixture=_SKILL_TEST_FIXTURE,
                prompt_asset=_SKILL_PROMPT_ANCHOR,
                eval_fixture=_SKILL_EVAL_FIXTURE,
                tags=["weather", "freshness", "cross-subagent"],
            ),
            selection_policy=SkillSelectionPolicy(
                priority=40,
                intent_signals=["weather", "seasonality", "rain", "freshness"],
                preferred_context=["travel_dates", "candidate_destinations", "route_constraints"],
                notes=["Use when dates or freshness-sensitive routing can change the plan."],
            ),
            metadata={"onboarding_doc": _SKILL_ONBOARDING_DOC},
        ),
        # ============================================================
        # 技能4：酒店报价技能
        # 场景：成都3日游需要住宿，查询酒店价格用于预算权衡
        # ============================================================
        SkillContract(
            name="HotelQuoteSkill",
            description="Gather accommodation options used by budget and itinerary tradeoffs.",
            tool_names=["query_hotels"],  # 依赖 query_hotels 工具
            allowed_subagents=["budget", "planning"],  # 预算和规划子Agent可用
            input_contract=SkillInputContract(
                required_context=["destinations", "stay_nights"],  # 必需：目的地/住宿晚数
                optional_context=["budget_mode", "hotel_preferences"],  # 可选：预算模式/酒店偏好
            ),
            output_contract=SkillOutputContract(
                artifact="BudgetReport",  # 产出制品：预算报告
                fields=["hotelQuotes", "priceBands", "tradeoffNotes"],  # 酒店报价/价格区间/权衡备注
            ),
            output_artifact="BudgetReport",
            freshness_policy="must_refresh_if_stale",  # 酒店价格变化快，过期必须刷新
            evidence_required=True,  # 需要证据支撑（报价必须有来源）
            market_metadata=SkillMarketMetadata(
                owner="budget-subagent",
                version="2026.03",
                docs_path=_SKILL_CATALOG_DOC,
                test_fixture=_SKILL_TEST_FIXTURE,
                prompt_asset=_SKILL_PROMPT_ANCHOR,
                eval_fixture=_SKILL_EVAL_FIXTURE,
                tags=["budget", "quotes", "evidence"],
            ),
            selection_policy=SkillSelectionPolicy(
                priority=20,
                intent_signals=["budget", "hotel", "stay"],
                preferred_context=["destinations", "stay_nights", "budget_mode"],
                notes=["Run before aggregation when the budget view still needs hotel quotes."],
            ),
            metadata={"onboarding_doc": _SKILL_ONBOARDING_DOC},
        ),
        # ============================================================
        # 技能5：预算汇总技能
        # 场景：成都3日游，汇总住宿+交通+活动费用，生成总预算视图
        # ============================================================
        SkillContract(
            name="BudgetAggregationSkill",
            description="Aggregate accommodation, transport, and activity costs into a budget view.",
            tool_names=["calculate_budget"],  # 依赖 calculate_budget 工具
            allowed_subagents=["budget"],
            input_contract=SkillInputContract(
                required_context=["hotel_quotes", "transport_estimates", "activity_estimates"],  # 必需：酒店报价/交通估算/活动估算
                optional_context=["budget_mode", "group_size"],  # 可选：预算模式/团队规模
            ),
            output_contract=SkillOutputContract(
                artifact="BudgetReport",
                fields=["executionBudget", "budgetSummary", "budgetRisks"],  # 执行预算/预算摘要/预算风险
            ),
            output_artifact="BudgetReport",
            evidence_required=True,  # 需要证据支撑
            market_metadata=SkillMarketMetadata(
                owner="budget-subagent",
                version="2026.03",
                docs_path=_SKILL_CATALOG_DOC,
                test_fixture=_SKILL_TEST_FIXTURE,
                prompt_asset=_SKILL_PROMPT_ANCHOR,
                eval_fixture=_SKILL_EVAL_FIXTURE,
                tags=["budget", "aggregation", "artifact-first"],
            ),
            selection_policy=SkillSelectionPolicy(
                priority=30,
                intent_signals=["budget", "cost", "tradeoff"],
                preferred_context=["hotel_quotes", "transport_estimates", "activity_estimates"],
                notes=["Promote once quote-level evidence exists and a final budget summary is needed."],
            ),
            metadata={"onboarding_doc": _SKILL_ONBOARDING_DOC},
        ),
        # ============================================================
        # 技能6：行程综合技能
        # 场景：成都3日游，将用户意图和调研证据转化为每日行程步骤
        # 如：Day1 宽窄巷子→锦里→春熙路，Day2 都江堰→青城山...
        # ============================================================
        SkillContract(
            name="PlanSynthesisSkill",
            description="Transform user intent and evidence into itinerary steps.",
            tool_names=["plan_itinerary"],  # 依赖 plan_itinerary 工具
            allowed_subagents=["planning"],
            input_contract=SkillInputContract(
                required_context=["user_intent", "research_dossier"],  # 必需：用户意图/调研档案
                optional_context=["budget_report", "pace_preference", "route_constraints"],  # 可选：预算报告/节奏偏好/路线约束
            ),
            output_contract=SkillOutputContract(
                artifact="ItineraryDraft",  # 产出制品：行程草稿
                fields=["dailySteps", "routeOutline", "planningExplanation"],  # 每日步骤/路线概要/规划说明
            ),
            output_artifact="ItineraryDraft",
            market_metadata=SkillMarketMetadata(
                owner="planning-subagent",
                version="2026.03",
                docs_path=_SKILL_CATALOG_DOC,
                test_fixture=_SKILL_TEST_FIXTURE,
                prompt_asset=_SKILL_PROMPT_ANCHOR,
                eval_fixture=_SKILL_EVAL_FIXTURE,
                tags=["planning", "itinerary", "artifact-first"],
            ),
            selection_policy=SkillSelectionPolicy(
                priority=10,  # 规划阶段最高优先级
                intent_signals=["itinerary", "plan", "route"],
                preferred_context=["research_dossier", "budget_report"],
                notes=["Keep first for itinerary drafting once core intent and evidence are ready."],
            ),
            metadata={"onboarding_doc": _SKILL_ONBOARDING_DOC},
        ),
        # ============================================================
        # 技能7：旅行贴士技能
        # 场景：成都3日游，提供目的地注意事项（如"带伞"、"提前预约"等）
        # ============================================================
        SkillContract(
            name="TravelTipsSkill",
            description="Provide destination-specific advice and policy-related reminders.",
            tool_names=["get_travel_tips"],  # 依赖 get_travel_tips 工具
            allowed_subagents=["research", "verification"],  # 调研和验证子Agent可用
            input_contract=SkillInputContract(
                required_context=["destinations"],
                optional_context=["travel_dates", "traveler_profile", "policy_alerts"],  # 旅行日期/旅行者画像/政策提醒
            ),
            output_contract=SkillOutputContract(
                artifact="ResearchDossier",
                fields=["travelTips", "policyNotes", "reminders"],  # 旅行贴士/政策备注/提醒
            ),
            output_artifact="ResearchDossier",
            market_metadata=SkillMarketMetadata(
                owner="verification-subagent",
                version="2026.03",
                docs_path=_SKILL_CATALOG_DOC,
                test_fixture=_SKILL_TEST_FIXTURE,
                prompt_asset=_SKILL_PROMPT_ANCHOR,
                eval_fixture=_SKILL_EVAL_FIXTURE,
                tags=["verification", "tips", "policy"],
            ),
            selection_policy=SkillSelectionPolicy(
                priority=35,
                intent_signals=["tips", "policy", "packing"],
                preferred_context=["destinations", "travel_dates", "policy_alerts"],
                notes=["Use when the run needs traveler-facing reminders or policy checks."],
            ),
            metadata={"onboarding_doc": _SKILL_ONBOARDING_DOC},
        ),
    ]
