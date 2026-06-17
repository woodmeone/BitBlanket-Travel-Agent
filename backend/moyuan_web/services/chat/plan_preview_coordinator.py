"""规划预览协调器，在 plan 模式下生成和规范化计划预览事件。

协调器（Coordinator）模式说明：
    协调器负责编排多个协作组件的交互顺序。本模块协调计划预览的生成、
    规范化和状态更新，将复杂的多步流程封装为单一的 normalize 方法。

    与直接在 Mixin 中实现相比，协调器的优势：
    1. 单一职责：只负责计划预览的编排逻辑
    2. 可测试：可独立实例化和测试
    3. 依赖注入：通过构造函数注入依赖，而非硬编码

Protocol 说明：
    _PlanPreviewState 使用 Python 的 Protocol 定义最小状态合约，
    只要求实现类具有 reasoning_content/final_artifact/subagent_events
    三个属性，而不强制继承特定基类，实现鸭子类型（Duck Typing）。

应用场景：
    用户选择"规划模式"输入"帮我规划三亚5日游"，协调器会：
    1. 推送"开始制定旅行计划..."推理提示
    2. 在工作线程中生成计划预览（含意图、步骤、产物）
    3. 合并预览产物到累积状态
    4. 推送子 Agent 启动/完成事件
    5. 推送计划预览事件和推理摘要
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Optional, Protocol

from .shared import merge_artifact_payload


class _PlanPreviewState(Protocol):
    """规划预览所需的最小状态合约（Protocol）。

    使用 Protocol 定义接口而非抽象基类，实现类只需拥有这三个属性即可，
    无需显式继承，符合 Python 的鸭子类型哲学。
    """

    reasoning_content: str
    final_artifact: dict[str, Any]
    subagent_events: list[dict[str, Any]]


class ChatPlanPreviewCoordinator:
    """生成、规范化和应用计划预览状态更新。"""

    def __init__(
        self,
        *,
        generate_plan_preview: Callable[[str, str], dict[str, Any]],
        get_timestamp: Callable[[], str],
        logger: logging.Logger,
    ) -> None:
        """存储用于生成和时间戳计划预览的协作者。

        Args:
            generate_plan_preview: 计划预览生成函数（来自 ChatService）
            get_timestamp: 时间戳获取函数（来自 ChatHistoryMixin）
            logger: 日志器实例
        """
        self._generate_plan_preview = generate_plan_preview
        self._get_timestamp = get_timestamp
        self._logger = logger

    async def normalize(
        self,
        state: _PlanPreviewState,
        *,
        session_id: str,
        message: str,
    ) -> list[dict[str, Any]]:
        """【核心】规范化计划预览输出为流式事件和状态更新。

        编排流程：
        1. 推送初始推理提示
        2. 在工作线程中生成计划预览
        3. 合并预览产物到累积状态
        4. 推送子 Agent 启动事件
        5. 推送计划预览事件
        6. 推送子 Agent 完成事件
        7. 推送推理摘要
        """
        payloads = self._build_intro_payloads(state)
        plan_preview = await self._load_plan_preview(session_id, message)
        if not plan_preview:
            return payloads

        self._merge_preview_artifacts(state, plan_preview)
        payloads.extend(self._build_subagent_start_payloads(state, plan_preview))
        payloads.append(self._build_preview_payload(plan_preview))
        payloads.extend(self._build_subagent_completion_payloads(state, plan_preview))

        summary_payload = self._build_summary_payload(state, plan_preview)
        if summary_payload is not None:
            payloads.append(summary_payload)

        return payloads

    def _build_intro_payloads(self, state: _PlanPreviewState) -> list[dict[str, Any]]:
        """推送预览生成前显示的初始推理提示。"""
        intro = "开始制定旅行计划..."
        state.reasoning_content += intro
        return [{"type": "reasoning_chunk", "content": intro}]

    async def _load_plan_preview(self, session_id: str, message: str) -> Optional[dict[str, Any]]:
        """在工作线程中运行计划预览生成，并柔化失败。

        使用 asyncio.to_thread 将同步的计划预览生成函数放到工作线程，
        避免阻塞事件循环。生成失败时返回 None，不中断主流程。
        """
        try:
            return await asyncio.to_thread(self._generate_plan_preview, session_id, message)
        except Exception as exc:
            self._logger.warning("Plan preview failed, continue react flow: %s", exc)
            return None

    def _merge_preview_artifacts(self, state: _PlanPreviewState, plan_preview: dict[str, Any]) -> None:
        """将预览产物片段合并到累积的最终产物中。

        预览可能同时包含 artifact（完整产物）和 artifact_patch（增量补丁），
        两者都需要合并。
        """
        state.final_artifact = merge_artifact_payload(state.final_artifact, plan_preview.get("artifact", {}))
        state.final_artifact = merge_artifact_payload(
            state.final_artifact,
            plan_preview.get("artifact_patch", {}),
        )

    def _build_subagent_start_payloads(
        self,
        state: _PlanPreviewState,
        plan_preview: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """构建预览生成阶段的可选子 Agent 启动事件。"""
        preview_subagent = plan_preview.get("subagent")
        if not preview_subagent:
            return []

        preview_skills = plan_preview.get("skills", [])
        state.subagent_events.append(
            {
                "subagent": preview_subagent,
                "skills": preview_skills,
                "trigger": "plan_preview",
                "timestamp": self._get_timestamp(),
            }
        )
        return [
            {
                "type": "subagent_start",
                "subagent": preview_subagent,
                "skills": preview_skills,
            }
        ]

    @staticmethod
    def _build_preview_payload(plan_preview: dict[str, Any]) -> dict[str, Any]:
        """构建客户端消费的公共计划预览载荷。

        包含计划 ID、意图、解释、验证状态、步骤列表和产物。
        """
        return {
            "type": "plan_preview",
            "plan_id": plan_preview.get("plan_id"),
            "intent": plan_preview.get("intent"),
            "explanation": plan_preview.get("plan_explanation"),
            "validation_status": plan_preview.get("validation_status", "pass"),
            "validation_errors": plan_preview.get("validation_errors", []),
            "steps": plan_preview.get("plan", []),
            "artifact": plan_preview.get("artifact", {}),
        }

    def _build_subagent_completion_payloads(
        self,
        state: _PlanPreviewState,
        plan_preview: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """构建预览阶段的可选产物/子 Agent 完成事件。"""
        preview_subagent = plan_preview.get("subagent")
        preview_artifact_patch = plan_preview.get("artifact_patch", {})
        if not preview_subagent or not preview_artifact_patch:
            return []

        state.subagent_events.append(
            {
                "subagent": preview_subagent,
                "status": "preview_ready",
                "summary": "Plan preview artifact prepared.",
                "timestamp": self._get_timestamp(),
            }
        )
        return [
            {
                "type": "artifact_patch",
                "subagent": preview_subagent,
                "artifact_patch": preview_artifact_patch,
            },
            {
                "type": "subagent_end",
                "subagent": preview_subagent,
                "status": "preview_ready",
            },
        ]

    @staticmethod
    def _build_summary_payload(
        state: _PlanPreviewState,
        plan_preview: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        """构建预览步骤可用后显示的推理摘要。

        应用场景：展示 "识别意图：trip_planning，将执行 4 步。"
        """
        preview_steps = plan_preview.get("plan", [])
        if not preview_steps:
            return None

        preview_intent = plan_preview.get("intent")
        preview_summary = f"识别意图：{preview_intent}，将执行 {len(preview_steps)} 步。"
        state.reasoning_content += f" 识别意图：{preview_intent}，共 {len(preview_steps)} 步。"
        return {"type": "reasoning_chunk", "content": preview_summary}
