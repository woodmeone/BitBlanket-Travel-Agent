"""
可观测性模块 —— 请求上下文、结构化日志、Prometheus 指标

【基础知识】
- 可观测性（Observability）：通过日志（Logs）、指标（Metrics）、追踪（Traces）三大支柱，
  让运维人员能够理解系统内部状态。本模块覆盖日志和指标两部分。

- Prometheus 指标：Prometheus 是主流的开源监控系统，通过拉取（Pull）方式采集指标。
  常用指标类型：
  - Counter（计数器）：只增不减，如请求总数、限流拒绝数
  - Histogram（直方图）：统计分布，如请求延迟的 P50/P95/P99
  - Gauge（仪表盘）：可增可减，如当前进行中的请求数、就绪状态

- 结构化日志（Structured Logging）：将日志输出为 JSON 格式而非纯文本，
  便于日志平台（如 ELK、Loki）进行检索和聚合分析。
  每条日志自动携带 request_id 和 trace_id，实现全链路追踪。

- ContextVar：Python 3.7+ 的上下文变量，在异步环境中安全地传递请求级数据，
  无需显式传参即可在任意层级的日志中获取当前请求 ID。
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from contextvars import ContextVar, Token
from typing import Any

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

logger = logging.getLogger(__name__)

_request_id_var: ContextVar[str] = ContextVar("moyuan_request_id", default="")  # 请求级上下文变量：当前请求ID
_trace_id_var: ContextVar[str] = ContextVar("moyuan_trace_id", default="")  # 请求级上下文变量：当前追踪ID


def _structured_logging_enabled() -> bool:
    """延迟读取结构化日志开关，避免启动时循环导入。"""
    try:
        from config import server_config

        return bool(server_config.structured_logging)
    except Exception:
        return True

# ---- Prometheus 指标定义 ----
# 指标命名规范：moyuan_<子系统>_<指标名>，标签用于维度拆分

HTTP_REQUESTS_TOTAL = Counter(
    "moyuan_http_requests_total",
    "HTTP requests handled by the web API.",  # HTTP 请求总数（按方法、路径、状态码分组）
    ["method", "path", "status"],
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "moyuan_http_request_duration_seconds",
    "HTTP request duration in seconds.",  # HTTP 请求延迟分布（P50/P95/P99）
    ["method", "path"],
)
HTTP_IN_FLIGHT_REQUESTS = Gauge(
    "moyuan_http_in_flight_requests",
    "Current number of in-flight HTTP requests.",  # 当前处理中的请求数（可增可减）
)
CHAT_STREAM_REQUESTS_TOTAL = Counter(
    "moyuan_chat_stream_requests_total",
    "Chat stream requests grouped by mode and outcome.",  # 聊天流请求总数（按模式和结果分组）
    ["mode", "outcome"],
)
RATE_LIMIT_REJECTIONS_TOTAL = Counter(
    "moyuan_rate_limit_rejections_total",
    "Rate-limited HTTP requests grouped by route path.",  # 限流拒绝数（按路由路径分组）
    ["path"],
)
HTTP_TIMEOUTS_TOTAL = Counter(
    "moyuan_http_timeouts_total",
    "HTTP requests terminated by timeout middleware grouped by route path.",  # 超时终止数（按路由路径分组）
    ["path"],
)
SSE_EVENTS_TOTAL = Counter(
    "moyuan_sse_events_total",
    "SSE events emitted by chat streaming.",  # SSE 事件发送数（按事件类型分组）
    ["event_type"],
)
READINESS_STATE = Gauge(
    "moyuan_readiness_state",
    "Readiness state gauge. 1 means ready, 0 means not ready.",  # 就绪状态：1=就绪, 0=未就绪
)


def new_request_id(prefix: str = "req") -> str:
    """生成短请求标识符，格式如 req-a1b2c3d4e5f6g7h8，用于日志和响应头。"""
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


def bind_request_context(request_id: str, trace_id: str | None = None) -> tuple[Token[str], Token[str]]:
    """【核心】将请求级 ID 绑定到上下文变量，使后续日志和 SSE 自动携带。

    返回的 Token 用于请求结束后重置上下文，防止协程间数据泄漏。
    """
    effective_trace_id = trace_id or request_id
    return _request_id_var.set(request_id), _trace_id_var.set(effective_trace_id)


def reset_request_context(tokens: tuple[Token[str], Token[str]]) -> None:
    """请求处理完成后重置上下文变量，恢复到绑定前的状态。"""
    request_token, trace_token = tokens
    _request_id_var.reset(request_token)
    _trace_id_var.reset(trace_token)


def get_request_context() -> dict[str, str]:
    """获取当前请求的 request_id 和 trace_id，用于日志、指标、SSE 载荷。"""
    request_id = _request_id_var.get("")
    trace_id = _trace_id_var.get("")
    return {
        "request_id": request_id,
        "trace_id": trace_id or request_id,
    }


def emit_structured_log(
    target_logger: logging.Logger,
    event: str,
    level: int = logging.INFO,
    **fields: Any,
) -> None:
    """【核心】发射一条结构化日志，自动合并请求上下文。

    当结构化日志开启时，输出 JSON 格式（便于日志平台解析）；
    关闭时输出纯文本格式。
    例：emit_structured_log(logger, "chat_completed", mode="react", duration_ms=1200)
    输出：{"event": "chat_completed", "request_id": "req-xxx", "mode": "react", "duration_ms": 1200}
    """
    if not _structured_logging_enabled():
        target_logger.log(level, "%s %s", event, fields)
        return
    payload: dict[str, Any] = {
        "event": event,
        **get_request_context(),  # 自动注入 request_id 和 trace_id
        **fields,
    }
    target_logger.log(level, json.dumps(payload, ensure_ascii=False, default=str))  # ensure_ascii=False 保留中文


def record_http_request(method: str, path: str, status_code: int, duration_seconds: float) -> None:
    """记录一次 HTTP 请求的 Prometheus 指标（请求计数 + 延迟直方图）。"""
    status = str(status_code)
    HTTP_REQUESTS_TOTAL.labels(method=method, path=path, status=status).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(method=method, path=path).observe(duration_seconds)


def record_chat_stream(mode: str, outcome: str) -> None:
    """递增聊天流结果计数器，用于监控和告警。例：mode="react", outcome="success"。"""
    CHAT_STREAM_REQUESTS_TOTAL.labels(mode=mode, outcome=outcome).inc()


def record_rate_limit_rejection(path: str) -> None:
    """递增指定路径的限流拒绝计数器。"""
    RATE_LIMIT_REJECTIONS_TOTAL.labels(path=path or "unknown").inc()


def record_http_timeout(path: str) -> None:
    """递增指定路径的超时计数器。"""
    HTTP_TIMEOUTS_TOTAL.labels(path=path or "unknown").inc()


def record_sse_event(event_type: str) -> None:
    """递增 SSE 事件发送计数器。"""
    SSE_EVENTS_TOTAL.labels(event_type=event_type or "unknown").inc()


def set_readiness_state(is_ready: bool) -> None:
    """更新 Prometheus 就绪状态指标（1=就绪, 0=未就绪）。"""
    READINESS_STATE.set(1 if is_ready else 0)


def metrics_response_payload() -> tuple[bytes, str]:
    """返回 Prometheus 指标采集响应的字节内容和 Content-Type。"""
    return generate_latest(), CONTENT_TYPE_LATEST


class RequestMetricsTimer:
    """轻量级请求计时器 —— 跟踪进行中请求数和请求耗时。

    创建时自动递增 HTTP_IN_FLIGHT_REQUESTS 指标，
    调用 stop() 时递减该指标并返回耗时秒数。
    """

    def __init__(self) -> None:
        """启动计时器并立即递增"进行中请求"计数。"""
        self._started_at = time.perf_counter()
        HTTP_IN_FLIGHT_REQUESTS.inc()

    def stop(self) -> float:
        """停止计时器，递减"进行中请求"计数，返回耗时秒数。"""
        elapsed = time.perf_counter() - self._started_at
        HTTP_IN_FLIGHT_REQUESTS.dec()
        return elapsed
