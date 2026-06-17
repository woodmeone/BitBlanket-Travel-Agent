"""子代理（Subagent）基类模块。

子代理概念说明：
    在旅行 Agent 架构中，主 Agent（Supervisor）将复杂任务拆分给多个"专家"——即子代理。
    每个子代理专注于一个特定领域，类似旅行社中不同岗位的专员：
    - research（研究）：负责目的地信息收集，如景点、天气、签证政策等
    - planning（规划）：负责行程编排，如每日路线、时间分配等
    - budget（预算）：负责费用估算与权衡，如机票比价、酒店预算等
    - verification（验证）：负责质量审核，如行程一致性检查、数据时效性验证等

    子代理通过 SkillContract（技能契约）声明自己拥有的技能和工具，
    并通过 selection_plan（选择计划）机制决定在给定上下文中哪些技能可以被激活。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from ..contracts import SkillContract


@dataclass(slots=True)  # slots=True: 使用 __slots__ 优化内存占用和属性访问速度
class SkillSelectionDecision:
    """描述子代理在一次选择计划中对某个技能候选的决策结果。

    举例：用户说"我想去东京5天，预算1万"，research 子代理会评估：
    - "search_attractions" 技能匹配了意图信号"景点"，状态为 ready
    - "search_visa" 技能缺少必需上下文"国籍"，状态为 blocked
    """

    skill: str  # 技能名称，如 "search_attractions"
    status: str  # 决策状态: "ready"(可执行) / "blocked"(缺少必需上下文) / "standby"(意图不匹配)
    priority: int  # 优先级数值，越小越优先执行
    matched_intent_signals: list[str] = field(default_factory=list)  # 匹配到的意图信号，如 ["景点", "美食"]
    matched_preferred_context: list[str] = field(default_factory=list)  # 匹配到的偏好上下文，如 ["目的地=东京"]
    missing_required_context: list[str] = field(default_factory=list)  # 缺少的必需上下文，如 ["用户国籍"]
    notes: list[str] = field(default_factory=list)  # 附加说明

    def to_dict(self) -> dict[str, Any]:
        """将决策结果转为可 JSON 序列化的字典。"""
        return {
            "skill": self.skill,
            "status": self.status,
            "priority": self.priority,
            "matched_intent_signals": list(self.matched_intent_signals),
            "matched_preferred_context": list(self.matched_preferred_context),
            "missing_required_context": list(self.missing_required_context),
            "notes": list(self.notes),
        }


@dataclass(slots=True)
class BaseSubagent:
    """子代理基类，所有子代理（research/planning/budget/verification）的公共抽象。

    每个子代理持有若干 SkillContract（技能契约），通过技能声明自己能做什么、
    需要什么上下文、如何被选择。基类提供了技能查询、选择策略计算、
    事件构建等通用能力。
    """

    name: str  # 子代理名称，如 "research"、"planning"
    description: str  # 子代理职责描述
    skills: list[SkillContract] = field(default_factory=list)  # 该子代理拥有的技能列表

    def skill_names(self) -> list[str]:
        """返回该子代理拥有的所有技能名称。"""
        return [skill.name for skill in self.skills]

    def tool_names(self) -> list[str]:
        """返回该子代理通过技能可调用的所有工具名称（去重）。

        工具是技能的底层执行单元，一个技能可能使用多个工具。
        例如 "search_flights" 技能可能使用 "flight_api" 和 "price_cache" 两个工具。
        """
        seen: list[str] = []
        for skill in self.skills:
            for tool_name in skill.tool_names:
                if tool_name not in seen:
                    seen.append(tool_name)
        return seen

    def selection_policy(self) -> list[dict[str, Any]]:
        """【核心】返回该子代理的静态技能选择策略。

        静态策略不考虑当前上下文，仅展示每个技能的声明式选择规则，
        用于调试和策略预览。
        """
        return [
            {
                "skill": skill.name,
                "priority": skill.selection_policy.priority,
                "intent_signals": list(skill.selection_policy.intent_signals),
                "required_context": list(skill.input_contract.required_context),
                "preferred_context": list(skill.selection_policy.preferred_context),
                "freshness_policy": skill.freshness_policy,
                "fallback_policy": skill.fallback_policy,
                "evidence_required": skill.evidence_required,
                "notes": list(skill.selection_policy.notes),
            }
            for skill in self._ordered_skills()
        ]

    def selection_plan(
        self,
        *,
        context_keys: Optional[Iterable[str]] = None,
        intent_signals: Optional[Iterable[str]] = None,
    ) -> list[dict[str, Any]]:
        """【核心】根据当前上下文和意图信号，计算该子代理的技能选择计划。

        这是子代理调度最关键的方法：给定当前对话中已有的上下文（如目的地=东京、
        天数=5）和用户意图信号（如"景点"、"预算"），为每个技能计算一个决策状态：
        - ready: 所有必需上下文已满足，且意图信号匹配
        - blocked: 缺少必需上下文（如搜索签证需要"用户国籍"但未提供）
        - standby: 必需上下文满足但意图信号不匹配（如用户没提预算，budget技能待命）

        旅行场景举例：
            用户说"我想去京都看红叶"
            → context_keys = ["目的地=京都", "主题=红叶"]
            → intent_signals = ["景点", "自然风光"]
            → research 子代理的 "search_attractions" 技能: ready（匹配"景点"信号）
            → budget 子代理的 "estimate_cost" 技能: standby（没提预算相关意图）
        """
        # 将上下文键和意图信号归一化（小写+去空格），用于不区分大小写的匹配
        normalized_context = {_normalize_token(value) for value in context_keys or [] if _normalize_token(value)}
        normalized_signals = {_normalize_token(value) for value in intent_signals or [] if _normalize_token(value)}
        decisions: list[SkillSelectionDecision] = []
        for skill in self._ordered_skills():
            required_context = [_normalize_token(value) for value in skill.input_contract.required_context]
            preferred_context = [_normalize_token(value) for value in skill.selection_policy.preferred_context]
            policy_signals = [_normalize_token(value) for value in skill.selection_policy.intent_signals]

            # 计算缺少的必需上下文（阻塞技能执行的关键缺失）
            missing_required_context = [
                raw_value
                for raw_value, normalized_value in zip(skill.input_contract.required_context, required_context)
                if normalized_value and normalized_value not in normalized_context
            ]
            # 计算已匹配的偏好上下文（非必需但有则更好）
            matched_preferred_context = [
                raw_value
                for raw_value, normalized_value in zip(skill.selection_policy.preferred_context, preferred_context)
                if normalized_value and normalized_value in normalized_context
            ]
            # 计算已匹配的意图信号（用户表达的需求方向）
            matched_intent_signals = [
                raw_value
                for raw_value, normalized_value in zip(skill.selection_policy.intent_signals, policy_signals)
                if normalized_value and normalized_value in normalized_signals
            ]

            # 【核心】状态判定逻辑
            status = "ready"
            if missing_required_context:
                # 缺少必需上下文 → 阻塞，无法执行
                status = "blocked"
            elif normalized_signals and policy_signals and not matched_intent_signals:
                # 有意图信号但无一匹配 → 待命，暂不需要执行
                status = "standby"

            decisions.append(
                SkillSelectionDecision(
                    skill=skill.name,
                    status=status,
                    priority=skill.selection_policy.priority,
                    matched_intent_signals=matched_intent_signals,
                    matched_preferred_context=matched_preferred_context,
                    missing_required_context=missing_required_context,
                    notes=list(skill.selection_policy.notes),
                )
            )

        return [decision.to_dict() for decision in decisions]

    def start_event(
        self,
        *,
        session_id: str,  # 会话ID，标识一次用户对话
        run_id: Optional[str],  # 运行ID，标识一次子代理执行
        sequence: int,  # 执行序号，同一会话中的第几次子代理调用
        trigger: str,  # 触发原因，如 "user_message" 或 "auto_retry"
        chat_mode: Optional[str],  # 对话模式，如 "react"（推理+行动）或 "plan"（规划模式）
    ) -> dict[str, Any]:
        """构建子代理启动事件，用于流式输出和日志记录。"""
        return {
            "type": "subagent_start",
            "subagent": self.name,
            "description": self.description,
            "skills": self.skill_names(),
            "tool_names": self.tool_names(),
            "session_id": session_id,
            "run_id": run_id,
            "sequence": sequence,
            "trigger": trigger,
            "chat_mode": chat_mode,
        }

    def end_event(
        self,
        *,
        session_id: str,
        run_id: Optional[str],
        sequence: int,
        status: str = "completed",  # 结束状态: "completed"(成功) / "failed"(失败) / "partial"(部分完成)
        summary: str = "",  # 执行摘要，如 "已收集3个目的地的景点信息"
    ) -> dict[str, Any]:
        """构建子代理结束事件，用于流式输出和日志记录。"""
        return {
            "type": "subagent_end",
            "subagent": self.name,
            "session_id": session_id,
            "run_id": run_id,
            "sequence": sequence,
            "status": status,
            "summary": summary,
        }

    def artifact_patch_from_preview(self, preview: dict[str, Any]) -> dict[str, Any]:
        """从计划预览数据构建部分产物补丁。子类可覆写以提供领域特定的产物数据。

        产物（artifact）是子代理的输出结果，如行程表、预算报告等。
        "补丁"意味着只更新产物的部分字段，而非替换整个产物。
        """
        _ = preview
        return {}

    def artifact_patch_from_done(
        self,
        done_event: dict[str, Any],  # 完成事件，包含执行结果数据
        *,
        user_message: str,  # 用户原始消息
        session_id: str,  # 会话ID
        chat_mode: Optional[str],  # 对话模式
    ) -> dict[str, Any]:
        """从最终完成事件构建部分产物补丁。子类可覆写以提供领域特定的产物数据。"""
        _ = (done_event, user_message, session_id, chat_mode)
        return {}

    def _ordered_skills(self) -> list[SkillContract]:
        """按选择策略优先级排序技能，优先级相同时按名称排序，保证确定性顺序。"""
        return sorted(
            self.skills,
            key=lambda skill: (skill.selection_policy.priority, skill.name),
        )


def _normalize_token(value: object) -> str:
    """将上下文键或意图信号归一化为小写字符串，用于不区分大小写的匹配比较。

    例如: "目的地=东京" → "目的地=东京", "  Budget  " → "budget"
    """
    return str(value or "").strip().lower()
