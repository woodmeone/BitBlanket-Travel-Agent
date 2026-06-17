"""
计划生成流水线（Planning Pipeline）

将用户意图（intent）转化为可执行的工具调用计划（tool execution plan）。
本模块从 LangGraph 图节点中抽取出来，以降低编排层的耦合度。

典型流程：
  用户意图 → 策略分析 → 计划生成 → 工具策略校验 → 规范化 → 输出状态补丁

旅行场景举例：
  用户说"成都3日游" → intent="itinerary" → 生成3步计划：
    s1: query_attractions（查景点）→ s2: get_weather（查天气）→ s3: plan_itinerary（排行程）
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# 默认出行天数
DEFAULT_DAY_COUNT = 3
# 默认出行人数
DEFAULT_PEOPLE_COUNT = 1


class PlanningPipeline:
    """【核心】计划生成流水线，独立于图节点外壳，构建并校验一轮执行计划。"""

    def __init__(
        self,
        *,
        runtime_config: Any,  # 运行时配置对象，包含 max_plan_steps、round_max_tools 等限制参数
        tool_names: set[str],  # 已注册的工具名称集合，用于校验计划中的工具引用
        planner_hooks: dict[str, Callable[[dict[str, Any]], list[dict[str, Any]]]],  # 按意图分发的计划生成钩子，key 为意图名
        stage_output_model: type[BaseModel],  # 阶段输出的 Pydantic 模型类，用于结构化校验
        validate_stage_output: Callable[[type[BaseModel], dict[str, Any]], dict[str, Any]],  # 阶段输出校验函数
        build_execution_summary: Callable[[list[dict[str, Any]]], dict[str, Any]],  # 执行摘要构建函数
        validation_result_builder: Callable[..., dict[str, Any]],  # 验证结果构建函数，用于生成合成的工具结果
        step_signature: Callable[[str, dict[str, Any]], str],  # 步骤签名函数，用于步骤去重和追踪
    ) -> None:
        """存储构建一轮计划阶段状态补丁所需的协作者。"""
        self.runtime_config = runtime_config
        self.tool_names = tool_names
        self.planner_hooks = planner_hooks
        self.stage_output_model = stage_output_model
        self.validate_stage_output = validate_stage_output
        self.build_execution_summary = build_execution_summary
        self.validation_result_builder = validation_result_builder
        self.step_signature = step_signature

    def build(self, state: Mapping[str, Any]) -> dict[str, Any]:
        """【核心】构建并校验一轮计划阶段的状态补丁。

        流程：
          1. 从状态中提取意图、实体、策略信息
          2. 根据意图选择计划生成钩子或使用默认计划
          3. 执行工具策略（注入必选/可选工具步骤）
          4. 规范化计划（去重 step_id、填充默认值）
          5. 校验计划步骤（工具是否已注册）
          6. 输出经过 validate_stage_output 校验的状态补丁

        旅行场景举例：
          state.intent="itinerary", entities={"city":"成都","days":3}
          → 生成3步计划：查景点 → 查天气 → 排行程
        """
        logger.info("[Planning Pipeline] Building execution plan...")

        # 从状态中提取意图信息
        intent = str(state.get("intent", "general") or "general")  # 主意图，如 "itinerary"、"budget"
        intent_detail = self._as_dict(state.get("intent_detail"))  # 意图详情，包含实体等
        entities = self._as_dict(intent_detail.get("entities"))  # 提取的实体，如 {"city":"成都","days":3}
        strategy_detail = self._as_dict(state.get("strategy_detail"))  # 策略详情
        primary_intent = str(strategy_detail.get("primary_intent") or intent or "general")  # 策略主意图
        secondary_intent = strategy_detail.get("secondary_intent")  # 次要意图，如 "itinerary"+"budget"
        required_tools = self._as_text_list(strategy_detail.get("required_tools"))  # 策略要求的必选工具
        optional_tools = self._as_text_list(strategy_detail.get("optional_tools"))  # 策略建议的可选工具

        # 根据意图选择计划生成钩子；若无匹配钩子则使用默认计划
        planner_hook = self.planner_hooks.get(primary_intent) or self.planner_hooks.get(intent)
        used_planner_hook = planner_hook is not None
        if planner_hook is not None:
            try:
                plan = planner_hook(entities)
            except Exception as exc:
                logger.warning("[Planning Pipeline] Planner hook failed (intent=%s): %s", intent, exc)
                plan = []
        else:
            # 无专用钩子时使用默认计划模板
            plan = self._default_plan(primary_intent, entities)
            # 若存在次要意图且与主意图不同，合并次要计划
            if secondary_intent and secondary_intent != primary_intent:
                secondary_plan = self._default_plan(str(secondary_intent), entities)
                plan = self._merge_plans(plan, secondary_plan)

        # 执行工具策略：注入缺失的必选/可选工具步骤
        # 注意：若使用了 planner_hook，则不再注入可选工具（hook 已自行决定）
        plan = self._enforce_tool_policy(
            plan=plan,
            required_tools=required_tools,
            optional_tools=[] if used_planner_hook else optional_tools,
            entities=entities,
        )

        # 规范化计划：统一 step_id、填充默认值和重试设置
        normalized_plan = self._normalize_plan(plan)
        # 若计划步骤数超过配置上限，截断
        if len(normalized_plan) > self.runtime_config.max_plan_steps:
            logger.warning(
                "[Planning Pipeline] Plan truncated from %d to %d by AGENT_MAX_PLAN_STEPS",
                len(normalized_plan),
                self.runtime_config.max_plan_steps,
            )
            normalized_plan = normalized_plan[: self.runtime_config.max_plan_steps]

        # 校验计划步骤中的工具引用是否合法
        validation_status, validation_errors = self._validate_plan_steps(normalized_plan)
        # 收集因工具未注册而被阻塞的步骤 ID
        validation_blocked = [
            str(item.get("step_id"))
            for item in validation_errors
            if item.get("code") == "TOOL_NOT_REGISTERED"
        ]
        # 构建校验统计和合成的工具结果
        stats_steps = self._build_plan_validation_stats(normalized_plan, validation_errors)
        tool_results = self._build_plan_validation_tool_results(validation_errors)
        # 生成唯一的计划 ID
        plan_id = f"plan-{uuid.uuid4().hex[:12]}"
        logger.info("[Planning Pipeline] Plan created with %d steps (plan_id=%s)", len(normalized_plan), plan_id)

        # 构建并返回经过校验的阶段输出
        return self.validate_stage_output(
            self.stage_output_model,
            {
                "plan_id": plan_id,  # 计划唯一标识
                "plan_explanation": self._build_plan_explanation(intent, normalized_plan),  # 计划说明文本
                "plan": normalized_plan,  # 规范化后的计划步骤列表
                "validation_status": validation_status,  # 校验状态："pass" | "warn" | "fail"
                "validation_errors": validation_errors,  # 校验错误列表
                "current_step": 0,  # 当前执行步骤索引，初始为 0
                "execution_round": 0,  # 执行轮次，初始为 0
                "execution_state": {"completed": [], "failed": [], "blocked": sorted(validation_blocked)},  # 执行状态追踪
                "execution_stats": {"plan_id": plan_id, "started_at": self._timestamp(), "steps": stats_steps},  # 执行统计
                "execution_summary": self.build_execution_summary(stats_steps),  # 执行摘要
                "execution_trace": [],  # 执行轨迹，记录每步的输入输出
                "execution_budget": {  # 执行预算限制
                    "max_tools": self.runtime_config.round_max_tools,  # 单轮最大工具调用数
                    "max_elapsed_ms": self.runtime_config.round_max_elapsed_ms,  # 单轮最大耗时（毫秒）
                    "max_tokens": self.runtime_config.round_max_tokens,  # 单轮最大 token 消耗
                    "tools_used": 0,  # 已使用工具数
                    "elapsed_ms": 0,  # 已耗时（毫秒）
                    "tokens_used": 0,  # 已消耗 token 数
                },
                "fused_tool_results": None,  # 融合后的工具结果，初始为空
                "early_stop_reason": None,  # 提前终止原因，初始为空
                "verify_retry_count": 0,  # 验证重试次数，初始为 0
                "verify_result": None,  # 验证结果，初始为空
                "tools_used": [],  # 已使用的工具名称列表
                "tool_results": tool_results,  # 工具执行结果字典
            },
        )

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        """将可选的映射类型值强制转换为普通字典。若非字典则返回空字典。"""
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _as_text_list(value: Any) -> list[str]:
        """将列表类型值规范化为非空字符串列表。若非列表则返回空列表。"""
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if str(item).strip()]

    @staticmethod
    def _timestamp() -> str:
        """返回 ISO 格式的时间戳，用于计划阶段的记录。"""
        return datetime.now().isoformat()

    def _default_plan(self, intent: str, entities: dict[str, Any]) -> list[dict[str, Any]]:
        """【核心】当无专用计划钩子时，根据意图类型生成默认工具计划。

        旅行场景举例：
          intent="itinerary", entities={"city":"成都","days":3}
          → 返回3步计划：
            s1: query_attractions(city="成都") → 查景点池
            s2: get_weather(city="成都", days=3) → 查天气
            s3: plan_itinerary(destination="成都", days=3) → 排行程（依赖 s1、s2）
        """
        if intent == "recommend":
            return [
                {
                    "step": 1,
                    "step_id": "s1",
                    "tool": "search_cities",
                    "params": {"query": entities.get("query", "")},
                    "description": "查询候选目的地",
                    "depends_on": [],
                }
            ]
        if intent == "attractions":
            return [
                {
                    "step": 1,
                    "step_id": "s1",
                    "tool": "query_attractions",
                    "params": {
                        "city": entities.get("city", ""),
                        "category": entities.get("category"),
                    },
                    "description": "查询城市核心景点",
                    "depends_on": [],
                }
            ]
        if intent == "itinerary":
            return [
                {
                    "step": 1,
                    "step_id": "s1",
                    "tool": "query_attractions",
                    "params": {"city": entities.get("city", "")},
                    "description": "查询景点池",
                    "depends_on": [],
                },
                {
                    "step": 2,
                    "step_id": "s2",
                    "tool": "get_weather",
                    "params": {"city": entities.get("city", ""), "days": entities.get("days", DEFAULT_DAY_COUNT)},
                    "description": "查询天气情况",
                    "depends_on": [],
                },
                {
                    "step": 3,
                    "step_id": "s3",
                    "tool": "plan_itinerary",
                    "params": {
                        "destination": entities.get("city", ""),
                        "days": entities.get("days", DEFAULT_DAY_COUNT),
                        "interests": entities.get("interests"),
                    },
                    "description": "生成按天行程建议",
                    "depends_on": ["s1", "s2"],  # 依赖前两步的结果
                },
            ]
        if intent == "budget":
            return [
                {
                    "step": 1,
                    "step_id": "s1",
                    "tool": "calculate_budget",
                    "params": {
                        "destination": entities.get("destination", ""),
                        "days": entities.get("days", DEFAULT_DAY_COUNT),
                        "people": entities.get("people", DEFAULT_PEOPLE_COUNT),
                        "accommodation_level": entities.get("level", "medium"),  # 住宿等级：low/medium/high
                    },
                    "description": "估算总预算",
                    "depends_on": [],
                }
            ]
        if intent == "tips":
            return [
                {
                    "step": 1,
                    "step_id": "s1",
                    "tool": "get_travel_tips",
                    "params": {
                        "destination": entities.get("destination", ""),
                        "season": entities.get("season"),  # 出行季节，如 "summer"
                    },
                    "description": "获取出行提醒",
                    "depends_on": [],
                }
            ]
        return []

    @staticmethod
    def _merge_plans(primary: list[dict[str, Any]], secondary: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """将次要计划中不重复的步骤追加到主计划。

        去重依据：工具名 + 参数的 JSON 签名。
        旅行场景举例：
          主意图="itinerary"（查景点+查天气+排行程），次要意图="budget"（算预算）
          → 合并为4步计划，若预算步骤与景点步骤参数不同则都保留
        """
        merged = list(primary)
        existing_signatures = {
            f"{item.get('tool')}:{json.dumps(item.get('params', {}), ensure_ascii=False, sort_keys=True)}"
            for item in merged
        }
        for item in secondary:
            signature = f"{item.get('tool')}:{json.dumps(item.get('params', {}), ensure_ascii=False, sort_keys=True)}"
            if signature not in existing_signatures:
                merged.append(item)
                existing_signatures.add(signature)
        return merged

    def _enforce_tool_policy(
        self,
        *,
        plan: list[dict[str, Any]],
        required_tools: list[str],  # 策略要求的必选工具，缺失时必须注入
        optional_tools: list[str],  # 策略建议的可选工具，仅在计划较短时注入
        entities: dict[str, Any],  # 实体信息，用于填充注入步骤的参数
    ) -> list[dict[str, Any]]:
        """【核心】注入计划中缺失的必选和可选工具步骤。

        规则：
          - 必选工具（required_tools）：无论计划已有多少步，缺失时必须注入
          - 可选工具（optional_tools）：仅在计划步骤数 ≤ 2 时注入，且不超过 max_plan_steps

        旅行场景举例：
          计划只有1步"查景点"，但策略要求必选"查天气"和可选"查酒店"
          → 注入后变为3步：查景点 + 查天气 + 查酒店
        """
        merged = list(plan)
        existing_tools = {str(item.get("tool", "")) for item in merged}
        next_step = len(merged) + 1

        # 注入缺失的必选工具步骤，必选的工具必须加进去，所以，判断有没有在现有的工具中，没有就加进去
        for tool_name in required_tools:
            if tool_name in existing_tools:
                continue
            step = self._default_step_for_tool(step_num=next_step, tool_name=tool_name, entities=entities, required=True)
            if step:
                merged.append(step)
                existing_tools.add(tool_name)
                next_step += 1

        # 仅在计划较短时注入可选工具步骤，可选的工具不用加进去，只有长度不够才加进去，所以当计划长度小于等于2的时候，就要判断可选工具中有没有在现有工具里，没有就加进去
        if len(merged) <= 2:
            for tool_name in optional_tools:
                if tool_name in existing_tools:
                    continue
                step = self._default_step_for_tool(
                    step_num=next_step,
                    tool_name=tool_name,
                    entities=entities,
                    required=False,
                )
                if step:
                    merged.append(step)
                    existing_tools.add(tool_name)
                    next_step += 1
                if len(merged) >= self.runtime_config.max_plan_steps:
                    break

        return merged

    @staticmethod
    def _default_step_for_tool(
        *,
        step_num: int,  # 步骤序号
        tool_name: str,  # 工具名称
        entities: dict[str, Any],  # 实体信息，用于填充参数
        required: bool,  # 是否为必选工具
    ) -> Optional[dict[str, Any]]:
        """为指定工具构建一个合成的计划步骤。

        根据工具名称从预定义映射中获取默认参数和描述。
        若工具不在映射中则返回 None。
        """
        city = entities.get("city") or entities.get("destination") or "北京"
        days = entities.get("days", DEFAULT_DAY_COUNT)
        mapping: dict[str, dict[str, Any]] = {
            "search_cities": {"params": {"query": entities.get("query") or city}, "description": "补全候选目的地"},
            "query_attractions": {"params": {"city": city, "category": entities.get("category")}, "description": "补全景点信息"},
            "query_hotels": {"params": {"city": city}, "description": "补全酒店信息"},
            "get_weather": {"params": {"city": city, "days": days}, "description": "补全天气信息"},
            "plan_itinerary": {
                "params": {"destination": city, "days": days, "interests": entities.get("interests")},
                "description": "补全行程规划",
            },
            "calculate_budget": {
                "params": {
                    "destination": city,
                    "days": days,
                    "people": entities.get("people", DEFAULT_PEOPLE_COUNT),
                    "accommodation_level": entities.get("level", "medium"),
                },
                "description": "补全预算测算",
            },
            "get_travel_tips": {"params": {"destination": city, "season": entities.get("season")}, "description": "补全出行建议"},
        }
        item = mapping.get(tool_name)
        if not item:
            return None
        return {
            "step": step_num,
            "step_id": f"s{step_num}",
            "tool": tool_name,
            "params": item["params"],
            "description": f"{item['description']} ({'required' if required else 'optional'})",
            "depends_on": [],
        }

    def _validate_plan_steps(
        self,
        plan: list[dict[str, Any]],
    ) -> tuple[Literal["pass", "warn", "fail"], list[dict[str, Any]]]:
        """【核心】校验计划步骤中的工具引用，并分类整体计划状态。

        返回值：
          - "pass"：所有步骤的工具均已注册
          - "warn"：部分步骤工具未注册，但仍有可执行步骤
          - "fail"：所有步骤工具均未注册，计划无法执行

        旅行场景举例：
          计划含3步，其中"query_hotels"未注册 → 返回 "warn"
          计划含1步，且该工具未注册 → 返回 "fail"
        """
        errors: list[dict[str, Any]] = []
        for step in plan:
            tool_name = str(step.get("tool") or "").strip()
            if not tool_name or tool_name not in self.tool_names:
                errors.append(
                    {
                        "step_id": str(step.get("step_id") or ""),
                        "tool": tool_name,
                        "code": "TOOL_NOT_REGISTERED",
                        "message": f"Tool not registered: {tool_name or '<empty>'}",
                    }
                )

        if not errors:
            return "pass", []

        invalid_steps = {
            str(item.get("step_id") or "")
            for item in errors
            if item.get("code") == "TOOL_NOT_REGISTERED"
        }
        status: Literal["pass", "warn", "fail"] = "warn"
        # 若所有步骤均无效，则标记为 fail
        if invalid_steps and len(invalid_steps) >= len(plan):
            status = "fail"
        return status, errors

    def _build_plan_validation_stats(
        self,
        plan: list[dict[str, Any]],
        errors: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """为校验失败的步骤构建阻塞状态的执行统计行。

        仅包含校验出错的步骤，正常步骤不在此处记录。
        """
        error_by_step: dict[str, dict[str, Any]] = {}
        for item in errors:
            step_id = str(item.get("step_id") or "")
            if step_id:
                error_by_step[step_id] = item

        stats_steps: list[dict[str, Any]] = []
        for step in plan:
            step_id = str(step.get("step_id") or "")
            item = error_by_step.get(step_id)
            if not item:
                continue
            timestamp = self._timestamp()
            stats_steps.append(
                {
                    "step_id": step_id,
                    "tool": step.get("tool"),
                    "depends_on": step.get("depends_on", []),
                    "status": "blocked",  # 步骤状态：被阻塞
                    "attempt": 0,  # 尝试次数
                    "error_code": item.get("code"),  # 错误码，如 "TOOL_NOT_REGISTERED"
                    "fallback_used": False,  # 是否使用了降级方案
                    "provider_used": None,  # 使用的服务提供者
                    "started_at": timestamp,
                    "ended_at": timestamp,
                    "duration_ms": 0,  # 执行耗时（毫秒）
                    "signature": self.step_signature(str(step.get("tool") or ""), dict(step.get("params", {}) or {})),
                }
            )
        return stats_steps

    def _build_plan_validation_tool_results(self, errors: list[dict[str, Any]]) -> dict[str, Any]:
        """为计划校验错误构建合成的工具结果载荷。

        当步骤因工具未注册而被阻塞时，生成一个错误性质的"工具结果"，
        以便下游流程能统一处理。
        """
        results: dict[str, Any] = {}
        for item in errors:
            step_id = str(item.get("step_id") or "")
            tool_name = str(item.get("tool") or "")
            code = str(item.get("code") or "PLAN_VALIDATION_ERROR")
            timestamp = self._timestamp()
            results[f"{step_id}:{tool_name}"] = self.validation_result_builder(
                tool_name=tool_name,
                code=code,
                message=str(item.get("message") or code),
                timestamp=timestamp,
            )
        return results

    def _normalize_plan(self, plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """【核心】规范化计划：统一 ID、填充默认值和重试设置。

        处理内容：
          - 为缺失 step_id 的步骤自动生成
          - 去重 step_id（追加索引后缀）
          - 填充 timeout_seconds、max_retries 等默认值
        """
        normalized: list[dict[str, Any]] = []
        used_step_ids: set[str] = set()
        for idx, raw in enumerate(plan, start=1):
            step_id = str(raw.get("step_id") or f"s{idx}")
            # 若 step_id 已存在，追加索引后缀避免重复
            if step_id in used_step_ids:
                step_id = f"{step_id}_{idx}"
            used_step_ids.add(step_id)
            normalized.append(
                {
                    "step": int(raw.get("step", idx)),  # 步骤序号
                    "step_id": step_id,  # 步骤唯一标识
                    "tool": raw.get("tool", ""),  # 工具名称
                    "params": raw.get("params", {}),  # 工具调用参数
                    "depends_on": list(raw.get("depends_on", [])),  # 依赖的前置步骤 ID 列表
                    "description": raw.get("description", ""),  # 步骤描述
                    "timeout_seconds": raw.get("timeout_seconds"),  # 超时时间（秒），None 表示使用默认值
                    "max_retries": raw.get("max_retries", self.runtime_config.default_tool_max_retries),  # 最大重试次数
                }
            )
        return normalized

    @staticmethod
    def _build_plan_explanation(intent: str, plan: list[dict[str, Any]]) -> str:
        """将生成的计划摘要为一条日志友好的说明字符串。

        旅行场景举例：
          "intent=itinerary, plan_steps=3, chain=s1:query_attractions -> s2:get_weather -> s3:plan_itinerary"
        """
        ## 这里就是遍历plan中的item，把item的step_id和tool工具拼接起来，然后用' -> '连接起来，然后不断拼接，直到把plan里面的item遍历完在返回拼接字符串
        if not plan:
            return f"intent={intent}, no tool plan required"
        steps = [f"{item['step_id']}:{item['tool']}" for item in plan]
        return f"intent={intent}, plan_steps={len(plan)}, chain={' -> '.join(steps)}"

__all__ = ["PlanningPipeline"]
