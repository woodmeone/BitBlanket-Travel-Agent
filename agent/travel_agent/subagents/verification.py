"""验证子代理（Verification Subagent）模块。

职责：审核一致性、时效性和质量风险。
    verification 子代理是旅行规划的"质检员"，负责：
    - 检查行程逻辑一致性（如时间冲突、地点不可达）
    - 验证数据时效性（如价格信息是否过期）
    - 评估整体质量风险（如降级回退次数过多）

    类比旅行社：verification 子代理就是"审核专员"，
    在行程方案交付给客户前做最后一遍质量检查，
    确保没有逻辑错误或过时信息。
"""

from __future__ import annotations

from typing import Any, Optional

from .base import BaseSubagent


class VerificationSubagent(BaseSubagent):
    """验证子代理，基于现有验证/自检输出实现。

    覆写基类的 artifact_patch_from_done 方法，
    从完成事件中提取验证结果和预算质量指标。
    """

    def artifact_patch_from_done(
        self,
        done_event: dict[str, Any],  # 完成事件，包含 verification_passed、stale_result_count 等
        *,
        user_message: str,  # 用户原始消息
        session_id: str,  # 会话ID
        chat_mode: Optional[str],  # 对话模式
    ) -> dict[str, object]:
        """【核心】从完成事件构建验证产物补丁。

        验证子代理的产物包含两部分：
        1. verification: 验证结果（是否通过、是否需要重试、问题列表）
        2. budget: 预算质量指标（降级步数、过期结果数），与 budget 子代理共享

        旅行场景举例：
            验证子代理检查行程后发现 Day2 下午同时安排了两个景点（时间冲突），
            → verification_passed=False, summary="验证发现问题，可能需要后续处理"
            或者所有检查通过 → verification_passed=True, summary="验证完成"
        """
        _ = (user_message, session_id, chat_mode)
        passed = done_event.get("verification_passed")  # 验证是否通过: True/False/None(未执行验证)
        stale = int(done_event.get("stale_result_count", 0) or 0)  # 过期结果数量
        fallback_steps = int(done_event.get("fallback_steps", 0) or 0)  # 降级回退步数

        # 根据验证结果生成摘要
        summary = "Verification completed."  # 默认：验证完成
        if passed is False:
            # 验证未通过，存在需要关注的问题
            summary = "Verification found issues and may require follow-up."
        elif stale > 0:
            # 验证通过但存在过期数据，需注意时效性
            summary = "Verification completed with stale results noted."

        return {
            "verification": {
                "passed": passed,  # 验证是否通过
                "should_retry": False,  # 是否建议重试（snake_case）
                "shouldRetry": False,  # camelCase 版本
                "issues": [],  # 发现的问题列表，如 ["Day2时间冲突", "酒店价格数据过期"]
                "refresh_targets": [],  # 需要刷新的数据目标（snake_case）
                "refreshTargets": [],  # camelCase 版本
                "summary": summary,  # 验证摘要
            },
            "budget": {
                # 验证子代理也输出预算质量指标，因为数据时效性和降级情况
                # 直接影响预算子代理的结果可信度
                "fallback_steps": fallback_steps,  # 降级回退步数（snake_case）
                "fallbackSteps": fallback_steps,  # camelCase 版本
                "stale_result_count": stale,  # 过期结果数量（snake_case）
                "staleResultCount": stale,  # camelCase 版本
            },
            "metadata": {
                "verification_subagent_completed": True,  # 标记验证子代理已完成
            },
        }
