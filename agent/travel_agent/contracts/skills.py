"""Skill-layer contracts bridging subagents, governance, and low-level tools.

【模块说明】
本模块定义了"技能层"契约，描述 Agent 可复用的领域技能。
技能是子代理和底层工具之间的桥梁，类似于"岗位说明书"：
- 定义了技能需要什么输入（SkillInputContract）
- 定义了技能产出什么输出（SkillOutputContract）
- 定义了技能的元数据、选择策略等管理信息

【核心概念 - 什么是"技能"(Skill)?】
技能是 Agent 的"专业能力"，比工具更高层。例如：
- 工具：search_hotels（搜索酒店）- 底层API调用
- 技能：hotel_recommendation（酒店推荐）- 组合多个工具+LLM推理的专业能力
一个技能可能使用多个工具，并包含业务逻辑和验证规则。

【应用场景举例】
定义一个"酒店推荐"技能：
- name: "hotel_recommendation"
- description: "根据用户偏好和预算推荐合适的酒店"
- tool_names: ["search_hotels", "get_hotel_reviews"]（使用2个工具）
- allowed_subagents: ["research", "planning"]（只有research和planning子代理可用）
- input_contract: 需要目的地、预算等上下文
- output_contract: 产出 hotel_artifact，包含推荐酒店列表
"""

from __future__ import annotations

# asdict: 将 dataclass 实例转为字典的内置函数
from dataclasses import asdict, dataclass, field
from typing import Any, Optional


# 技能输入契约 - 描述技能运行前需要具备的上下文
@dataclass(slots=True)
class SkillInputContract:
    """Describe the context a skill expects before it is safe to run.

    【说明】定义技能安全运行所需的前置上下文。
    类似于"做菜前需要备齐的食材清单"：必须有的（required）和可选的（optional）。

    【应用场景】"酒店推荐"技能的输入契约：
    - required_context: ["destination", "budget"]（必须有目的地和预算）
    - optional_context: ["preferred_style", "accessibility_needs"]（可选偏好）
    → 如果缺少 destination 或 budget，该技能不会被触发
    """

    required_context: list[str] = field(default_factory=list)  # 必需的上下文字段名列表
    optional_context: list[str] = field(default_factory=list)  # 可选的上下文字段名列表


# 技能输出契约 - 描述技能运行后产出的结果结构
@dataclass(slots=True)
class SkillOutputContract:
    """Describe the structured result shape produced by one skill.

    【说明】定义技能产出的结果格式，包括产物名称和包含的字段。
    类似于"菜品出品标准"：规定这道菜叫什么名字、包含哪些组成部分。

    【应用场景】"酒店推荐"技能的输出契约：
    - artifact: "hotel_recommendations"（产物名称）
    - fields: ["hotels", "price_range", "recommendation_reasons"]（产物包含的字段）
    """

    artifact: Optional[str] = None  # 产物名称，如 "hotel_recommendations"
    fields: list[str] = field(default_factory=list)  # 产物包含的字段名列表


# 技能市场元数据 - 技能的"商品标签"，记录归属、版本、文档等管理信息
@dataclass(slots=True)
class SkillMarketMetadata:
    """Track ownership and onboarding hooks for one cataloged skill.

    【说明】技能的"商品标签"，用于技能市场的管理和治理。
    类似于App Store中每个App的信息页：开发者、版本号、文档链接、测试要求等。
    """

    owner: str = "travel-agent-platform"  # 技能所有者/团队
    version: str = "2026.03"  # 技能版本号
    docs_path: Optional[str] = None  # 文档路径
    test_fixture: Optional[str] = None  # 测试固件路径（测试用的模拟数据）
    prompt_asset: Optional[str] = None  # 提示词资源路径
    eval_fixture: Optional[str] = None  # 评估固件路径
    onboarding_requirements: list[str] = field(
        default_factory=lambda: ["schema", "tests", "docs", "eval"]
    )  # 上线要求清单：必须有schema、测试、文档、评估
    status: str = "active"  # 技能状态："active"=活跃, "deprecated"=已废弃
    tags: list[str] = field(default_factory=list)  # 标签，用于分类和搜索


# 技能选择策略 - 决定子代理何时优先选择此技能
@dataclass(slots=True)
class SkillSelectionPolicy:
    """Describe when one subagent should prioritize a skill over its peers.

    【说明】定义技能的优先级和触发条件，帮助子代理在多个可选技能中做出选择。
    类似于"推荐算法"：根据用户意图和上下文，决定推荐哪个技能。

    【应用场景】子代理需要选择酒店相关技能：
    - priority=10（高优先级）的 "hotel_recommendation" 技能
    - priority=50（低优先级）的 "budget_hotel_search" 技能
    - intent_signals: ["hotel", "住宿"] → 当用户提到"酒店"时匹配
    → 子代理优先选择 hotel_recommendation 技能
    """

    priority: int = 100  # 优先级，数字越小越优先（默认100）
    intent_signals: list[str] = field(default_factory=list)  # 意图信号关键词，如 ["hotel", "住宿"]
    preferred_context: list[str] = field(default_factory=list)  # 偏好的上下文条件
    notes: list[str] = field(default_factory=list)  # 备注说明


# 【核心】技能契约 - 一个可复用领域技能的完整定义
@dataclass(slots=True)
class SkillContract:
    """Capability contract describing one reusable domain skill.

    【说明】技能的完整定义契约，是技能层的核心数据结构。
    它将输入/输出契约、元数据、选择策略等组合在一起，
    形成一个完整的"技能档案"。

    【应用场景】注册一个"酒店推荐"技能到技能市场：
    SkillContract(
        name="hotel_recommendation",
        description="根据用户偏好和预算推荐合适的酒店",
        tool_names=["search_hotels", "get_hotel_reviews"],
        allowed_subagents=["research", "planning"],
        freshness_policy="best_effort",  # 数据新鲜度策略：尽力获取最新数据
        fallback_policy="graceful_degrade",  # 降级策略：优雅降级
        evidence_required=True,  # 需要提供推荐依据
    )
    """

    name: str  # 技能名称，唯一标识，如 "hotel_recommendation"
    description: str  # 技能描述，说明该技能的功能
    tool_names: list[str] = field(default_factory=list)  # 该技能使用的工具名称列表
    allowed_subagents: list[str] = field(default_factory=list)  # 允许使用该技能的子代理列表
    input_contract: SkillInputContract = field(default_factory=SkillInputContract)  # 输入契约
    output_contract: SkillOutputContract = field(default_factory=SkillOutputContract)  # 输出契约
    freshness_policy: str = "best_effort"  # 数据新鲜度策略："best_effort"=尽力获取最新
    fallback_policy: str = "graceful_degrade"  # 降级策略："graceful_degrade"=优雅降级
    output_artifact: Optional[str] = None  # 输出产物名称（与output_contract.artifact同步）
    evidence_required: bool = False  # 是否需要提供执行依据（如推荐理由）
    market_metadata: SkillMarketMetadata = field(default_factory=SkillMarketMetadata)  # 市场元数据
    selection_policy: SkillSelectionPolicy = field(default_factory=SkillSelectionPolicy)  # 选择策略
    metadata: dict[str, Any] = field(default_factory=dict)  # 扩展元数据字典

    def __post_init__(self) -> None:
        """Keep the legacy `output_artifact` field aligned with the structured contract.

        【说明】__post_init__ 是 dataclass 的特殊方法，在 __init__ 之后自动调用。
        这里用于同步 output_artifact 和 output_contract.artifact 两个字段，
        确保无论设置哪个，另一个也会被更新。类似于"双向绑定"。
        """
        if self.output_artifact and not self.output_contract.artifact:
            self.output_contract.artifact = self.output_artifact
        elif self.output_contract.artifact and self.output_artifact is None:
            self.output_artifact = self.output_contract.artifact

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary for diagnostics and docs.

        【说明】将技能契约转为字典，用于诊断和文档生成。
        asdict() 会递归地将所有嵌套的 dataclass 也转为字典。
        """
        payload = asdict(self)
        if self.output_artifact and not payload["output_contract"].get("artifact"):
            payload["output_contract"]["artifact"] = self.output_artifact
        return payload
