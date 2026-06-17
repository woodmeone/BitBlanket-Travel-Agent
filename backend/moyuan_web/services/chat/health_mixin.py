"""聊天健康诊断 Mixin，提供运行时健康状态、SLO 监控和故障遥测。

SLO（Service Level Objective）说明：
    SLO 是服务等级目标，定义了服务可接受的性能阈值。本模块监控三个关键指标：
    - timeout_rate: 工具调用超时率
    - failure_rate: 请求失败率
    - fallback_rate: 降级回退率
    任一指标超过阈值时，健康状态从 "ok" 降级为 "degraded"。

滑动窗口说明：
    健康指标基于时间窗口（默认60分钟）计算，只统计窗口内的请求，
    过期数据自动清理，确保指标反映近期真实状态。

应用场景：
    运维人员通过 /health 端点查看服务是否正常，通过 /tools/health
    查看各工具的调用成功率和熔断状态，及时发现异常。
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ChatHealthMixin:
    """健康、遥测和 SLO 快照方法 Mixin。

    被 ChatService 通过多继承混入，提供运行时健康检查、SLO 监控、
    故障聚类分析和遥测数据写入等能力。
    """

    async def health_status(self) -> dict[str, Any]:
        """返回轻量级运行时就绪状态，供健康检查端点使用。"""
        return {
            "initialized": self._initialized,
            "llm_adapter": self._llm_adapter is not None,
            "tools_count": len(self._tools) if self._tools else 0,
            "memory_enabled": self._memory_manager is not None,
            "runtime_layer": "agent-runtime" if self._agent_runtime is not None else "graph-direct",
            "skills_count": len(self._agent_runtime.skill_registry) if self._agent_runtime is not None else 0,
            "subagents_count": len(self._agent_runtime.subagents) if self._agent_runtime is not None else 0,
        }

    async def tools_health_status(self) -> dict[str, Any]:
        """返回详细的工具健康诊断，含 SLO 计数器和熔断状态。

        熔断（Circuit Breaker）说明：当某个工具连续失败时，熔断器打开，
        后续请求直接跳过该工具，避免级联故障。
        """
        status = await self.health_status()
        diagnostics = self._agent_runtime.get_tool_health_diagnostics() if self._agent_runtime is not None else {}
        health_metrics = self._build_health_metrics_snapshot()
        return {
            "status": "ok" if status.get("initialized") else "not initialized",
            "initialized": status.get("initialized", False),
            "configured_tools_count": status.get("tools_count", 0),
            "circuit_open_count": diagnostics.get("open_circuit_count", 0),
            "slo": health_metrics.get("slo", {}),
            "intent_aggregate": health_metrics.get("intent_aggregate", {}),
            "window_minutes": self._health_window_minutes,
            "diagnostics": diagnostics,
        }

    async def tools_intents_health_status(self) -> dict[str, Any]:
        """返回意图级别的聚合健康指标，供监控仪表盘使用。

        按意图（如 hotel_search, weather_query）分组统计各指标，
        便于定位特定意图的性能问题。
        """
        status = await self.health_status()
        health_metrics = self._build_health_metrics_snapshot()
        slo = health_metrics.get("slo", {})
        return {
            "status": "ok" if status.get("initialized") else "not initialized",
            "window_minutes": self._health_window_minutes,
            "total_requests": int(slo.get("total_requests", 0) or 0),
            "intent_aggregate": health_metrics.get("intent_aggregate", {}),
        }

    @staticmethod
    def _extract_failure_clusters(execution_stats: dict[str, Any]) -> dict[str, int]:
        """从执行元数据中提取聚类故障模式，用于遥测分析。

        将错误码归类为四类：timeout（超时）、param_error（参数错误）、
        irrelevant_answer（无关回答）、tool_error（工具错误）。

        应用场景：某次请求执行了3步，其中1步超时、1步参数错误，
        返回 {"timeout": 1, "param_error": 1, "irrelevant_answer": 0, "tool_error": 0}
        """
        steps = list((execution_stats or {}).get("steps", []) or [])
        clusters = {"timeout": 0, "param_error": 0, "irrelevant_answer": 0, "tool_error": 0}
        for step in steps:
            code = str(step.get("error_code") or "")
            if code == "TOOL_TIMEOUT":
                clusters["timeout"] += 1
            elif code == "PARAM_VALIDATION_ERROR":
                clusters["param_error"] += 1
            elif code:
                clusters["tool_error"] += 1
        return clusters

    def _emit_failure_telemetry(
        self,
        session_id: str,
        run_id: str,
        mode: str,
        execution_stats: dict[str, Any],
        answer: str,
        hard_error: Optional[str] = None,
    ) -> None:
        """将故障摘要遥测数据写入服务健康指标缓冲区和本地 JSONL 文件。

        仅当存在实际故障（聚类计数>0 或硬错误）时才写入，
        避免无意义的空记录。写入失败不影响主流程。
        """
        clusters = self._extract_failure_clusters(execution_stats)
        if not answer.strip():
            clusters["irrelevant_answer"] += 1
        payload = {
            "ts": datetime.now().isoformat(),
            "session_id": session_id,
            "run_id": run_id,
            "mode": mode,
            "clusters": clusters,
            "hard_error": hard_error,
        }
        if not any(value > 0 for value in clusters.values()) and not hard_error:
            return  # 无实际故障，跳过写入

        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
        target = os.path.join(root, "data", "runtime_failure_clusters.jsonl")  # 故障聚类 JSONL 文件路径
        os.makedirs(os.path.dirname(target), exist_ok=True)
        try:
            with open(target, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.warning("Failed to write failure telemetry: %s", exc)

    @staticmethod
    def _parse_int_env(name: str, default: int, minimum: int) -> int:
        """解析整数环境变量，带回退和下限保护。"""
        raw = str(os.getenv(name, str(default))).strip()
        try:
            value = int(raw)
            if value < minimum:
                raise ValueError(f"{name} must be >= {minimum}")
            return value
        except Exception:
            return default

    @staticmethod
    def _parse_float_env(name: str, default: float) -> float:
        """解析浮点环境变量，带回退保护和 [0, 1] 范围校验。"""
        raw = str(os.getenv(name, str(default))).strip()
        try:
            value = float(raw)
            if value < 0.0 or value > 1.0:
                raise ValueError(f"{name} must be in [0, 1]")
            return value
        except Exception:
            return default

    def _record_run_metrics(self, intent: str, execution_stats: dict[str, Any], hard_error: bool) -> None:
        """【核心】记录单次运行指标到有界内存缓冲区，供 SLO 快照计算。

        每次聊天请求完成后调用，记录是否超时、失败、降级回退，
        并按意图分组统计。写入后自动清理窗口外的旧数据。
        """
        steps = list((execution_stats or {}).get("steps", []) or [])
        has_timeout = any(str(step.get("error_code") or "") == "TOOL_TIMEOUT" for step in steps)
        has_failure = hard_error or any(str(step.get("status") or "") in {"failed", "blocked"} for step in steps)
        has_fallback = any(bool(step.get("fallback_used")) for step in steps)
        record = {
            "timestamp": datetime.now(),
            "intent": str(intent or "unknown"),
            "has_timeout": has_timeout,
            "has_failure": has_failure,
            "has_fallback": has_fallback,
        }
        with self._health_metrics_lock:
            self._health_metrics.append(record)
            self._prune_old_metrics_locked()

    def _prune_old_metrics_locked(self) -> None:
        """在锁保护下清理超出健康窗口的旧指标数据。

        从 deque 左端弹出时间戳早于 cutoff 的记录，
        保证缓冲区只保留窗口内的数据。
        """
        if not self._health_metrics:
            return
        cutoff = datetime.now() - timedelta(minutes=self._health_window_minutes)
        while self._health_metrics and self._health_metrics[0]["timestamp"] < cutoff:
            self._health_metrics.popleft()

    def _build_health_metrics_snapshot(self) -> dict[str, Any]:
        """【核心】构建当前健康快照，包含 SLO 比率和意图聚合指标。

        计算逻辑：
        1. 统计窗口内总请求数、超时数、失败数、降级数
        2. 计算各比率并与 SLO 阈值比较，确定整体状态（ok/degraded）
        3. 按意图分组统计各意图的指标
        """
        with self._health_metrics_lock:
            self._prune_old_metrics_locked()
            records = list(self._health_metrics)

        total = len(records)
        timeout_count = sum(1 for item in records if bool(item.get("has_timeout")))
        failure_count = sum(1 for item in records if bool(item.get("has_failure")))
        fallback_count = sum(1 for item in records if bool(item.get("has_fallback")))
        timeout_rate = round(timeout_count / total, 4) if total else 0.0
        failure_rate = round(failure_count / total, 4) if total else 0.0
        fallback_rate = round(fallback_count / total, 4) if total else 0.0

        status = "ok"
        if (
            timeout_rate > float(self._slo_thresholds["timeout_rate"])
            or failure_rate > float(self._slo_thresholds["failure_rate"])
            or fallback_rate > float(self._slo_thresholds["fallback_rate"])
        ):
            status = "degraded"

        intent_aggregate: dict[str, dict[str, Any]] = {}
        grouped: dict[str, list[dict[str, Any]]] = {}
        for item in records:
            intent = str(item.get("intent") or "unknown")
            grouped.setdefault(intent, []).append(item)
        for intent, items in grouped.items():
            bucket_total = len(items)
            intent_aggregate[intent] = {
                "total": bucket_total,
                "timeout_rate": round(sum(1 for it in items if bool(it.get("has_timeout"))) / bucket_total, 4)
                if bucket_total
                else 0.0,
                "failure_rate": round(sum(1 for it in items if bool(it.get("has_failure"))) / bucket_total, 4)
                if bucket_total
                else 0.0,
                "fallback_rate": round(sum(1 for it in items if bool(it.get("has_fallback"))) / bucket_total, 4)
                if bucket_total
                else 0.0,
            }

        return {
            "slo": {
                "status": status,
                "timeout_rate": timeout_rate,
                "failure_rate": failure_rate,
                "fallback_rate": fallback_rate,
                "thresholds": dict(self._slo_thresholds),
                "total_requests": total,
            },
            "intent_aggregate": intent_aggregate,
        }
