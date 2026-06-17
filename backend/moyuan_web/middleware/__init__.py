"""
HTTP 中间件模块 —— 请求日志、限流、超时控制

【基础知识】
- 中间件（Middleware）：在 Web 框架中，中间件是介于请求入口和业务路由之间的一层处理逻辑。
  每个请求会依次经过中间件链，响应则反向返回。常用于横切关注点（如日志、鉴权、限流）。
  FastAPI/Starlette 通过 BaseHTTPMiddleware 实现中间件，dispatch() 方法包裹每个请求的生命周期。

- 限流（Rate Limiting）：限制单位时间内某个客户端的请求次数，防止恶意刷接口或服务过载。
  本模块采用"滑动窗口"算法：记录每个请求的时间戳，只统计窗口内的请求数。
  例：配置 max_requests=100, window=60 表示同一 IP 在 60 秒内最多 100 次请求。

- 超时控制（Timeout）：为请求设置最大处理时长，超时后返回 504 Gateway Timeout，
  防止慢请求占用连接资源导致服务不可用。
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from ..observability import (
    RequestMetricsTimer,
    bind_request_context,
    emit_structured_log,
    new_request_id,
    record_http_request,
    record_http_timeout,
    record_rate_limit_rejection,
    reset_request_context,
)

logger = logging.getLogger(__name__)


def _default_exclude_paths(metrics_path: str = "/api/metrics") -> list[str]:
    """返回不需要限流的请求路径列表。

    健康检查、文档页面、指标采集等路径不应被限流，
    否则 Kubernetes 探针或监控系统可能因限流而误判服务不可用。
    """
    paths = [
        "/",
        "/docs",
        "/redoc",
        "/rapidoc",
        "/openapi.json",
        "/api/health",
        "/api/health/llm",
        "/api/health/tools",
        "/api/health/tools/intents",
        "/api/ready",
        "/api/live",
        "/api/metrics",
    ]
    if metrics_path and metrics_path not in paths:
        paths.append(metrics_path)
    return paths


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件 —— 为每个请求附加 ID、记录结构化日志、采集延迟指标。

    【核心职责】
    1. 为每个请求生成/透传 request_id 和 trace_id，用于全链路追踪
    2. 记录请求方法、路径、状态码、耗时等结构化日志
    3. 将延迟数据上报到 Prometheus 指标
    4. 在响应头中返回处理耗时和请求 ID，方便客户端排查问题
    """

    def __init__(self, app: ASGIApp, logger_name: str = "web.request") -> None:
        """初始化中间件，指定用于记录请求事件的 logger 命名空间。"""
        super().__init__(app)
        self.logger = logging.getLogger(logger_name)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """【核心】包裹单个请求的完整生命周期：绑定上下文 → 调用下游 → 记录指标 → 写入响应头。"""
        request_id = request.headers.get("X-Request-ID") or new_request_id()  # 优先透传上游请求ID，否则生成新的
        trace_id = request.headers.get("X-Trace-ID") or request_id  # 追踪ID，用于跨服务链路追踪
        request.state.request_id = request_id  # 将ID挂到 request.state，供下游路由和中间件读取
        request.state.trace_id = trace_id
        context_tokens = bind_request_context(request_id, trace_id)  # 绑定上下文变量，使日志自动携带请求ID
        timer = RequestMetricsTimer()  # 启动计时器，同时增加"进行中请求"计数

        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"
        query_params = dict(request.query_params)

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            status_code = 500
            emit_structured_log(
                self.logger,
                "http_request_failed",
                level=logging.ERROR,
                method=method,
                path=path,
                client_ip=client_ip,
                query_params=query_params,
            )
            reset_request_context(context_tokens)
            raise
        finally:
            duration_seconds = timer.stop()  # 停止计时，同时减少"进行中请求"计数
            record_http_request(method, getattr(request.scope.get("route"), "path", path), status_code, duration_seconds)  # 【核心】上报 Prometheus 指标

        emit_structured_log(
            self.logger,
            "http_request",
            method=method,
            path=path,
            route=getattr(request.scope.get("route"), "path", path),
            status=status_code,
            duration_ms=round(duration_seconds * 1000, 2),
            client_ip=client_ip,
            query_params=query_params,
        )

        response.headers["X-Process-Time"] = f"{duration_seconds * 1000:.2f}ms"  # 响应头返回处理耗时，方便前端/客户端排查
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Trace-ID"] = trace_id
        reset_request_context(context_tokens)  # 重置上下文变量，防止协程间泄漏
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """限流中间件 —— 基于内存的滑动窗口限流。

    【基础知识 - 滑动窗口限流】
    与固定窗口（如"每分钟重置计数"）不同，滑动窗口记录每个请求的精确时间戳，
    只统计最近 window 秒内的请求数。这样避免了固定窗口在窗口边界处的突发问题。

    例：window=60, max_requests=100 时，如果用户在第 0~30 秒发了 100 个请求，
    第 31 秒再发请求会被拒绝，直到第 0 秒的请求时间戳滑出窗口。
    """

    def __init__(
        self,
        app: ASGIApp,
        max_requests: int = 100,  # 窗口内允许的最大请求数
        window: int = 60,  # 滑动窗口时长（秒）
        key_func: Callable[[Request], str] | None = None,  # 限流键提取函数，默认按客户端IP
        exclude_paths: list[str] | None = None,  # 排除限流的路径列表
    ) -> None:
        """初始化滑动窗口限流器及请求键策略。"""
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window
        self.key_func = key_func or self._default_key_func
        self.exclude_paths = exclude_paths or _default_exclude_paths()
        self._requests: dict[str, deque[float]] = defaultdict(deque)  # 每个限流键对应的请求时间戳队列

    def _default_key_func(self, request: Request) -> str:
        """默认限流键：使用客户端 IP 地址。"""
        return request.client.host if request.client else "unknown"

    def _clean_old_requests(self, key: str, current_time: float) -> None:
        """清理已滑出窗口的旧时间戳，保持队列只含窗口内请求。"""
        requests = self._requests[key]
        window_start = current_time - self.window
        while requests and requests[0] < window_start:  # 队首时间戳早于窗口起点则移除
            requests.popleft()
        if not requests:
            del self._requests[key]  # 队列为空时清理键，防止内存泄漏

    def _check_rate_limit(self, key: str) -> tuple[bool, int]:
        """【核心】判断当前请求是否被允许，并返回剩余配额。

        返回 (allowed, remaining)：
        - allowed=True 表示放行，remaining 为剩余可用次数
        - allowed=False 表示被限流，remaining 为 0
        """
        current_time = time.time()
        self._clean_old_requests(key, current_time)

        requests = self._requests[key]
        current_count = len(requests)
        remaining = self.max_requests - current_count
        if current_count >= self.max_requests:
            return False, 0  # 超出配额，拒绝请求
        requests.append(current_time)  # 放行请求，记录当前时间戳
        return True, remaining

    def _is_excluded(self, path: str) -> bool:
        """判断请求路径是否在限流排除列表中。"""
        for exclude in self.exclude_paths:
            if exclude == "/":
                if path == "/":
                    return True
                continue
            if path.startswith(exclude):
                return True
        return False

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """【核心】执行限流判断：排除路径直接放行，超限返回 429 并记录指标。"""
        if self._is_excluded(request.url.path):
            return await call_next(request)

        key = self.key_func(request)
        allowed, remaining = self._check_rate_limit(key)

        if not allowed:
            route_path = getattr(request.scope.get("route"), "path", request.url.path)
            record_rate_limit_rejection(route_path)  # 上报限流拒绝指标到 Prometheus
            emit_structured_log(
                logger,
                "http_request_rate_limited",
                level=logging.WARNING,
                method=request.method,
                path=request.url.path,
                route=route_path,
                key=key,
                max_requests=self.max_requests,
                window_seconds=self.window,
            )
            rate_limit_response = JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Rate limit exceeded. Maximum {self.max_requests} requests per {self.window} seconds.",
                        "details": {
                            "max_requests": self.max_requests,
                            "window_seconds": self.window,
                        },
                    }
                },
            )
            rate_limit_response.headers["X-RateLimit-Limit"] = str(self.max_requests)  # 窗口内总配额
            rate_limit_response.headers["X-RateLimit-Remaining"] = "0"  # 剩余配额
            rate_limit_response.headers["X-RateLimit-Reset"] = str(int(time.time() + self.window))  # 配额重置时间戳
            if hasattr(request.state, "request_id"):
                rate_limit_response.headers["X-Request-ID"] = request.state.request_id
            if hasattr(request.state, "trace_id"):
                rate_limit_response.headers["X-Trace-ID"] = request.state.trace_id
            return rate_limit_response

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)  # 正常响应也附带限流信息头
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + self.window))
        return response


class TimeoutMiddleware(BaseHTTPMiddleware):
    """超时中间件 —— 为请求设置最大处理时长，超时返回 504 并记录遥测数据。

    【应用场景】
    当 LLM 推理服务响应缓慢时，请求可能长时间挂起，占用服务器连接资源。
    设置超时（如 30 秒）后，超时请求会被中断并返回 504，
    同时记录到 Prometheus 指标，便于运维发现慢请求问题。
    """

    def __init__(self, app: ASGIApp, timeout: float = 30.0) -> None:
        """初始化超时中间件，timeout 为最大请求处理时长（秒）。"""
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """【核心】使用 asyncio.wait_for 包裹请求，超时则返回 504 并记录遥测。"""
        try:
            return await asyncio.wait_for(call_next(request), timeout=self.timeout)  # 【核心】带超时的请求执行
        except asyncio.TimeoutError:
            route_path = getattr(request.scope.get("route"), "path", request.url.path)
            record_http_timeout(route_path)  # 上报超时指标到 Prometheus
            emit_structured_log(
                logger,
                "http_request_timeout",
                level=logging.WARNING,
                method=request.method,
                path=request.url.path,
                route=route_path,
                timeout_seconds=self.timeout,
            )
            response = JSONResponse(
                status_code=504,
                content={
                    "error": {
                        "code": "GATEWAY_TIMEOUT",
                        "message": f"Request processing timeout after {self.timeout} seconds",
                    }
                },
            )
            if hasattr(request.state, "request_id"):
                response.headers["X-Request-ID"] = request.state.request_id
            if hasattr(request.state, "trace_id"):
                response.headers["X-Trace-ID"] = request.state.trace_id
            return response


def setup_middleware(app: FastAPI) -> None:
    """【核心】根据服务配置注册所有中间件。

    中间件注册顺序（从外到内执行）：Timeout → RateLimit → RequestLogging
    即：请求先经过超时控制 → 限流检查 → 日志记录 → 到达业务路由
    """
    try:
        from moyuan_web.config.runtime import get_server_config

        server_config = get_server_config()
        max_requests = server_config.rate_limit_max_requests
        window = server_config.rate_limit_window_seconds
        timeout = server_config.request_timeout_seconds
        metrics_path = str(server_config.metrics_path or "/api/metrics")
    except Exception:  # 配置加载失败时使用默认值，保证服务仍可启动
        max_requests = 100
        window = 60
        timeout = 30.0
        metrics_path = "/api/metrics"

    app.add_middleware(RequestLoggingMiddleware)  # 最内层：日志记录
    app.add_middleware(
        RateLimitMiddleware,
        max_requests=max_requests,
        window=window,
        exclude_paths=_default_exclude_paths(metrics_path),
    )  # 中间层：限流
    app.add_middleware(TimeoutMiddleware, timeout=timeout)  # 最外层：超时控制


__all__ = [
    "RequestLoggingMiddleware",
    "RateLimitMiddleware",
    "TimeoutMiddleware",
    "setup_middleware",
]
