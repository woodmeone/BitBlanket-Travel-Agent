"""规划子代理（Planning Subagent）模块。

职责：将用户意图和研究证据转化为行程草稿。
    planning 子代理是旅行规划的核心"编排者"，负责：
    - 根据目的地、天数、偏好等信息编排每日行程
    - 生成行程预览（preview）和最终行程产物（artifact）
    - 协调时间分配、景点顺序、交通衔接等

    类比旅行社：planning 子代理就是"行程规划师"，
    根据客户需求和研究部门提供的资料，制作详细的旅行日程表。
"""

from __future__ import annotations

from typing import Any, Optional

from ..artifacts import build_trip_plan_artifact_from_plan_preview
from .base import BaseSubagent


class PlanningSubagent(BaseSubagent):
    """规划子代理，基于现有规划器和产物构建器实现。

    覆写基类的两个产物补丁方法，提供行程规划领域特定的产物数据。
    """

    def artifact_patch_from_preview(self, preview: dict[str, Any]) -> dict[str, Any]:
        """【核心】从计划预览数据构建规划产物补丁。

        当系统处于"预览模式"时调用，用户可以看到行程草稿但尚未最终确认。

        Args:
            preview: 计划预览数据，包含 session_id 等信息

        Returns:
            包含 itinerary（行程）和 metadata 的产物补丁

        旅行场景举例：
            用户说"帮我规划京都3日游"，系统生成预览行程，
            包含 Day1: 岚山竹林 → Day2: 伏见稻荷 → Day3: 金阁寺
        """
        artifact = build_trip_plan_artifact_from_plan_preview(
            preview,
            user_message="",
            session_id=str(preview.get("session_id") or "default"),
        )
        return {
            "itinerary": artifact.get("itinerary", {}),  # 行程数据，包含每日安排
            "metadata": {
                "planning_preview_available": True,  # 标记预览可用
            },
        }

    def artifact_patch_from_done(
        self,
        done_event: dict[str, Any],  # 完成事件，包含 plan_id 等结果数据
        *,
        user_message: str,  # 用户原始消息
        session_id: str,  # 会话ID
        chat_mode: Optional[str],  # 对话模式
    ) -> dict[str, Any]:
        """【核心】从最终完成事件构建规划产物补丁。

        当规划流程完成时调用，生成最终的行程产物数据。
        产物中同时包含 camelCase 和 snake_case 字段名，
        以兼容前端不同命名风格的消费方。

        旅行场景举例：
            规划完成后，产物包含 plan_id="plan_001"、
            explanation="为您规划了京都3日深度游"、
            validation_status="pass"（验证通过）
        """
        _ = (session_id, chat_mode)
        plan_id = done_event.get("plan_id")  # 行程计划ID
        return {
            "itinerary": {
                "plan_id": plan_id,
                "planId": plan_id,  # camelCase 版本，兼容前端
                "explanation": user_message,  # 行程说明，来自用户消息
                "steps": [],  # 行程步骤列表，后续由前端填充
                "validation_status": "pass",  # 验证状态: "pass" / "fail"
                "validationStatus": "pass",  # camelCase 版本
                "validation_errors": [],  # 验证错误列表
                "validationErrors": [],  # camelCase 版本
            },
            "metadata": {
                "planning_subagent_completed": True,  # 标记规划子代理已完成
            },
        }
