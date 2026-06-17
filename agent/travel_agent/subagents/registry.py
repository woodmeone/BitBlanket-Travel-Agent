"""子代理注册表模块。

注册表（Registry）模式说明：
    注册表是一个集中管理所有子代理实例的容器，负责：
    1. 按名称查找子代理
    2. 将工具调用路由到对应的子代理
    3. 根据阶段/标签推断应该由哪个子代理处理
    4. 汇总各子代理的产物补丁

    类比旅行社：注册表就像旅行社的"调度中心"，
    当客户提出需求时，调度中心决定把任务分配给哪个专员（子代理）。
"""

from __future__ import annotations

from typing import Iterable, Optional

from ..skills import SkillRegistry
from .base import BaseSubagent
from .budget import BudgetSubagent
from .planning import PlanningSubagent
from .research import ResearchSubagent
from .verification import VerificationSubagent


class SubagentRegistry:
    """子代理注册表，管理所有已启用的子代理及其工具映射。

    注册表维护一个 name → subagent 的映射，提供按名称查找、
    按工具名路由、按阶段/标签推断等查询能力。
    """

    def __init__(self, subagents: Iterable[BaseSubagent]):
        """用已启用的子代理实例初始化注册表。

        Args:
            subagents: 子代理实例的可迭代集合，如 [ResearchSubagent(...), PlanningSubagent(...)]
        """
        self._subagents = {subagent.name: subagent for subagent in subagents}

    def names(self) -> list[str]:
        """返回已启用子代理的名称列表，按固定顺序排列。

        顺序为: research → planning → budget → verification，
        对应旅行规划的标准流程：先研究、再规划、算预算、最后验证。
        """
        return [name for name in ["research", "planning", "budget", "verification"] if name in self._subagents]

    def get(self, name: str) -> Optional[BaseSubagent]:
        """按名称获取一个子代理实例，不存在则返回 None。"""
        return self._subagents.get(name)

    def skill_names(self, name: str) -> list[str]:
        """返回指定子代理拥有的技能名称列表。"""
        subagent = self.get(name)
        return subagent.skill_names() if subagent is not None else []

    def selection_policy(self, name: str) -> list[dict[str, object]]:
        """返回指定子代理的静态技能选择策略。"""
        subagent = self.get(name)
        return subagent.selection_policy() if subagent is not None else []

    def selection_plan(
        self,
        name: str,
        *,
        context_keys: Optional[Iterable[str]] = None,
        intent_signals: Optional[Iterable[str]] = None,
    ) -> list[dict[str, object]]:
        """返回指定子代理的上下文感知技能选择计划。"""
        subagent = self.get(name)
        if subagent is None:
            return []
        return subagent.selection_plan(
            context_keys=context_keys,
            intent_signals=intent_signals,
        )

    def resolve_subagent_for_stage(
        self,
        *,
        stage: Optional[str],  # 阶段标识，如 "budget"、"query"
        label: Optional[str] = None,  # 事件标签文本，可包含中英文关键词
        explicit_subagent: Optional[str] = None,  # 显式指定的子代理名称，优先级最高
    ) -> Optional[str]:
        """【核心】根据阶段和标签推断最可能处理该事件的子代理。

        推断优先级：
        1. 显式指定（explicit_subagent）→ 直接使用
        2. 标签文本关键词匹配 → 如标签含"预算"则路由到 budget 子代理
        3. 阶段标识匹配 → 如 stage="query" 则路由到 research 子代理
        4. 均不匹配 → 返回 None

        旅行场景举例：
            - 用户说"帮我查一下京都的酒店价格" → 标签含"查询" → research 子代理
            - 系统进入预算计算阶段 → stage="budget" → budget 子代理
            - 用户说"这个行程预算超了" → 标签含"预算" → budget 子代理
        """
        # 优先级1: 显式指定
        if explicit_subagent in self._subagents:
            return explicit_subagent

        # 优先级2: 标签文本关键词匹配（支持中英文）
        label_text = str(label or "")
        lowered = label_text.lower()
        if "budget" in lowered or "cost" in lowered or "预算" in label_text:
            return "budget" if "budget" in self._subagents else None
        if "计划" in label_text or "planning" in lowered:
            return "planning" if "planning" in self._subagents else None
        if "查询" in label_text or "research" in lowered:
            return "research" if "research" in self._subagents else None
        if "验证" in label_text or "verify" in lowered:
            return "verification" if "verification" in self._subagents else None

        # 优先级3: 阶段标识匹配
        if stage in {"budget", "costing"} and "budget" in self._subagents:
            return "budget"
        if stage == "query" and "research" in self._subagents:
            return "research"
        return None

    def resolve_subagent_for_tool(self, tool_name: str) -> Optional[str]:
        """根据工具名称反查拥有该工具的子代理。

        旅行场景举例：调用 "flight_search_api" 工具 → 查到属于 research 子代理
        """
        for name in self.names():
            subagent = self._subagents[name]
            if tool_name in subagent.tool_names():
                return name
        return None

    def preview_artifact_patch(self, preview: dict[str, object]) -> dict[str, object]:
        """返回规划子代理的计划预览产物补丁。

        仅 planning 子代理支持预览模式，其他子代理不需要。
        """
        planning = self.get("planning")
        if planning is None:
            return {}
        return planning.artifact_patch_from_preview(preview)

    def done_artifact_patches(
        self,
        done_event: dict[str, object],
        *,
        user_message: str,
        session_id: str,
        chat_mode: Optional[str],
    ) -> dict[str, dict[str, object]]:
        """【核心】汇总所有子代理的完成产物补丁。

        遍历每个子代理，让其从完成事件中提取各自的产物数据，
        最终返回一个 {子代理名: 产物补丁} 的映射。

        旅行场景举例：
            done_event 触发后，research 提取研究证据，planning 提取行程表，
            budget 提取预算报告，verification 提取验证结果，
            合并后形成完整的旅行规划产物。
        """
        patches: dict[str, dict[str, object]] = {}
        for name in self.names():
            subagent = self._subagents[name]
            patch = subagent.artifact_patch_from_done(
                done_event,
                user_message=user_message,
                session_id=session_id,
                chat_mode=chat_mode,
            )
            if patch:
                patches[name] = patch
        return patches


def build_default_subagent_registry(skill_registry: SkillRegistry) -> SubagentRegistry:
    """构建默认的子代理注册表，包含全部4个子代理。

    Args:
        skill_registry: 技能注册表，提供 for_subagent() 方法按子代理名获取技能列表

    Returns:
        包含 research/planning/budget/verification 四个子代理的注册表实例

    四个子代理的职责分工：
        - research: 收集目的地证据和旅行信号（景点、天气、签证等）
        - planning: 将意图和证据转化为行程草稿（每日路线、时间安排等）
        - budget: 估算费用范围和权衡方案（机票、酒店、餐饮等）
        - verification: 审核一致性、时效性和质量风险（行程冲突、数据过期等）
    """
    return SubagentRegistry(
        [
            ResearchSubagent(
                name="research",
                description="Collect destination evidence and travel signals.",
                skills=skill_registry.for_subagent("research"),
            ),
            PlanningSubagent(
                name="planning",
                description="Turn intent and evidence into itinerary drafts.",
                skills=skill_registry.for_subagent("planning"),
            ),
            BudgetSubagent(
                name="budget",
                description="Estimate cost envelopes and tradeoff ranges.",
                skills=skill_registry.for_subagent("budget"),
            ),
            VerificationSubagent(
                name="verification",
                description="Audit consistency, freshness, and quality risk.",
                skills=skill_registry.for_subagent("verification"),
            ),
        ]
    )
