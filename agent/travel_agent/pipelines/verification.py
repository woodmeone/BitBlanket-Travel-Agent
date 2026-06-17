"""
验证流水线（Verification Pipeline）

评估工具执行结果的新鲜度（freshness）和完整性（completeness），
并决定是重试刷新还是降级回答。

本模块从 LangGraph 图节点中抽取出来，以降低阶段间的耦合度。

典型流程：
  工具结果 → 新鲜度检查 → 完整性检查 → 时效一致性检查 → 风险策略检查 → 决策（重试/降级/通过）

旅行场景举例：
  用户问"成都3日游预算" → 查到酒店价格是3天前的（过期数据）
  → 验证流水线发现 is_stale=True → 建议重试刷新酒店数据
  → 若重试后仍过期 → 降级回答并标注"价格可能已变动"
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel


class VerificationPipeline:
    """【核心】验证流水线，评估证据的新鲜度/完整性，决定重试或降级流程。"""

    def __init__(
        self,
        *,
        runtime_config: Any,  # 运行时配置对象，包含 timeliness_controls_enabled 等开关
        refreshable_tools: set[str],  # 可刷新的工具名称集合，如 {"get_weather", "query_hotels"}
        stage_output_model: type[BaseModel],  # 阶段输出的 Pydantic 模型类
        issue_model: type[BaseModel],  # 问题模型的 Pydantic 类，用于结构化记录验证问题
        result_model: type[BaseModel],  # 验证结果模型的 Pydantic 类，包含 passed/should_retry 等字段
        validate_stage_output: Callable[[type[BaseModel], dict[str, Any]], dict[str, Any]],  # 阶段输出校验函数
        last_user_text: Callable[[Mapping[str, Any]], str],  # 从状态中提取用户最近一条消息文本
        is_high_risk_query: Callable[[str, str], bool],  # 判断是否为高风险查询（如价格、签证等敏感问题）
    ) -> None:
        """存储评估一轮验证阶段所需的协作者。"""
        self.runtime_config = runtime_config
        self.refreshable_tools = refreshable_tools
        self.stage_output_model = stage_output_model
        self.issue_model = issue_model
        self.result_model = result_model
        self.validate_stage_output = validate_stage_output
        self.last_user_text = last_user_text
        self.is_high_risk_query = is_high_risk_query

    def build(self, state: Mapping[str, Any]) -> dict[str, Any]:
        """【核心】构建一轮验证阶段的状态补丁。

        验证维度：
          1. 证据完整性：高风险问题是否有成功的工具结果
          2. 必选工具覆盖：策略要求的工具是否都有结果
          3. 数据新鲜度：工具结果是否过期（is_stale）
          4. 时效一致性：多个工具结果的时间跨度是否过大
          5. 风险策略合规：高风险问题是否开启了验证

        决策逻辑：
          - 可重试（should_retry=True）：有过期数据且可刷新，或缺少必选工具结果
          - 降级回答：重试后仍无法获得稳定数据
          - 通过（passed=True）：无任何问题

        旅行场景举例：
          用户问"成都3日游预算" → get_weather 返回过期数据
          → issue_type="stale_data" → should_retry=True → 触发刷新重试
        """
        intent = str(state.get("intent") or "general")  # 当前意图
        strategy_detail = self._as_dict(state.get("strategy_detail"))  # 策略详情
        requires_verification = bool(strategy_detail.get("requires_verification", False))  # 策略是否要求验证
        required_tools = [str(item) for item in strategy_detail.get("required_tools", [])]  # 策略要求的必选工具列表
        verify_retry_count = self._safe_int(state.get("verify_retry_count"), 0)  # 已重试次数
        tool_results = self._as_dict(state.get("tool_results"))  # 工具执行结果字典
        user_text = self.last_user_text(state)  # 用户最近的查询文本
        issues: list[BaseModel] = []  # 收集的验证问题列表

        # ---- 维度1：证据完整性检查 ----
        # 筛选成功的工具结果（success=True）
        successful_results = [
            item
            for item in tool_results.values()
            if isinstance(item, dict) and bool(item.get("success"))
        ]
        # 高风险问题但没有任何成功的工具结果 → 严重问题
        if requires_verification and not successful_results:
            issues.append(
                self.issue_model(
                    issue_type="missing_evidence",  # 缺少证据
                    message="高风险问题缺少工具成功结果，无法验证结论。",
                    severity="high",  # 严重级别：高
                )
            )

        # ---- 维度2：必选工具覆盖检查 ----
        # 收集已成功执行的工具名称
        matched_success_tools = {
            str(item.get("tool_name") or "").split(":")[-1]  # 取冒号后最后一部分作为工具名
            for item in successful_results
            if isinstance(item, dict)
        }
        # 找出缺失的必选工具
        missing_required = [name for name in required_tools if name not in matched_success_tools]
        if requires_verification and missing_required:
            issues.append(
                self.issue_model(
                    issue_type="required_tools_missing",  # 必选工具缺失
                    message=f"缺少必选验证工具结果: {missing_required}",
                    severity="high",
                )
            )

        # ---- 维度3：数据新鲜度检查 ----
        stale_count = 0  # 过期结果计数
        refresh_targets: list[str] = []  # 需要刷新重试的步骤 ID 列表
        refresh_tools: list[str] = []  # 需要刷新的工具名称列表
        for key, item in tool_results.items():
            if not isinstance(item, dict) or not bool(item.get("success")):
                continue
            if not bool(item.get("is_stale", False)):  # is_stale: 工具结果是否过期
                continue
            stale_count += 1
            tool_name = str(item.get("tool_name") or "").split(":")[-1]
            step_id = str(key).split(":", 1)[0].strip()  # 从 key 中提取步骤 ID，格式为 "step_id:tool_name"
            # 仅当工具在可刷新列表中时，才加入刷新目标
            if tool_name in self.refreshable_tools and step_id:
                if step_id not in refresh_targets:
                    refresh_targets.append(step_id)
                if tool_name not in refresh_tools:
                    refresh_tools.append(tool_name)

        if stale_count > 0:
            issues.append(
                self.issue_model(
                    issue_type="stale_data",  # 数据过期
                    message=f"存在 {stale_count} 条过期结果，建议刷新后再回答。",
                    severity="medium",
                )
            )
            # 已重试过但仍有过期数据 → 建议降级回答
            if verify_retry_count >= 1:
                issues.append(
                    self.issue_model(
                        issue_type="stale_refresh_failed",  # 刷新失败
                        message="已尝试刷新过期数据，但仍无法得到稳定实时结果，建议按降级策略回答并标注不确定性。",
                        severity="high",
                    )
                )
            # 有过期数据但无可刷新的工具步骤 → 建议降级回答
            elif not refresh_targets:
                issues.append(
                    self.issue_model(
                        issue_type="stale_unrefreshable",  # 过期但不可刷新
                        message="存在过期结果，但缺少可刷新的天气/酒店工具步骤，建议按降级策略回答。",
                        severity="medium",
                    )
                )

        # 若运行时未启用时效性控制，清除刷新目标（不执行刷新重试）
        if not self.runtime_config.timeliness_controls_enabled:
            refresh_targets = []
            refresh_tools = []

        # ---- 维度4：时效一致性检查 ----
        # 检查多个工具结果的获取时间跨度是否过大（超过7天）
        fetched_dates: list[datetime] = []
        for item in successful_results:
            raw = item.get("fetched_at")  # 工具结果的获取时间
            if not raw:
                continue
            try:
                dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))  # 解析 ISO 格式时间
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)  # 无时区信息时默认 UTC
                else:
                    dt = dt.astimezone(timezone.utc)  # 统一转为 UTC
                fetched_dates.append(dt)
            except Exception:
                continue
        # 若时间跨度超过7天，可能存在时效不一致
        if len(fetched_dates) >= 2:
            span_seconds = (max(fetched_dates) - min(fetched_dates)).total_seconds()
            if span_seconds > 7 * 24 * 3600:
                issues.append(
                    self.issue_model(
                        issue_type="date_inconsistency",  # 时间不一致
                        message="工具结果时间跨度过大，可能存在时效不一致。",
                        severity="medium",
                    )
                )

        # ---- 维度5：风险策略合规检查 ----
        # 高风险查询但未开启验证策略 → 策略违规
        if self.is_high_risk_query(user_text, intent) and not requires_verification:
            issues.append(
                self.issue_model(
                    issue_type="verification_policy_violation",  # 验证策略违规
                    message="高风险问题未开启验证策略。",
                    severity="high",
                )
            )

        # ---- 决策：是否重试 ----
        # 过期数据可重试条件：有过期数据 + 有可刷新目标 + 未重试过
        stale_retryable = stale_count > 0 and bool(refresh_targets) and verify_retry_count < 1
        # 结构性可重试条件：缺少证据或必选工具 + 未重试过
        structural_retryable = any(
            item.issue_type in {"missing_evidence", "required_tools_missing"}
            for item in issues
        ) and verify_retry_count < 1
        should_retry = stale_retryable or structural_retryable
        # 若非过期可重试，清除刷新目标
        if not stale_retryable:
            refresh_targets = []
            refresh_tools = []

        # ---- 构建验证结果 ----
        passed = len(issues) == 0  # 无任何问题则通过
        summary = "verification_passed" if passed else "; ".join(item.message for item in issues)  # 汇总信息

        result = self.result_model(
            passed=passed,  # 是否通过验证
            should_retry=should_retry,  # 是否应重试
            refresh_targets=refresh_targets,  # 需要刷新重试的步骤 ID
            refresh_tools=refresh_tools,  # 需要刷新的工具名称
            issues=issues,  # 验证问题列表
            summary=summary,  # 验证摘要
        )
        return self.validate_stage_output(
            self.stage_output_model,
            {
                "verify_result": result.model_dump(),  # 验证结果的字典形式
                "verify_retry_count": verify_retry_count + (1 if should_retry else 0),  # 更新重试计数
                "early_stop_reason": state.get("early_stop_reason") if passed else summary,  # 提前终止原因
            },
        )

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        """将可选的映射类型值强制转换为普通字典。若非字典则返回空字典。"""
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _safe_int(value: Any, default: int) -> int:
        """安全地将值转换为整数，转换失败时返回默认值。"""
        try:
            return int(value)
        except (TypeError, ValueError):
            return default


__all__ = ["VerificationPipeline"]
