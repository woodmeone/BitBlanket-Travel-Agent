"""
================================================================================
中间件模块
================================================================================

提供 FastAPI 中间件，包括：
- 请求日志中间件
- 速率限制中间件
- 请求超时中间件

使用示例:
    from middleware import RequestLoggingMiddleware, RateLimitMiddleware

    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RateLimitMiddleware, max_requests=100, window=60)

================================================================================
"""

import time
import logging
from collections import defaultdict
from collections import deque
from typing import Callable, Deque, Dict, Optional
from typing import TypeVar

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..observability import (
    RequestMetricsTimer,
    bind_request_context,
    emit_structured_log,
    new_request_id,
    record_http_request,
    reset_request_context,
)

logger = logging.getLogger(__name__)

# 类型变量
F = TypeVar('F', bound=Callable)


# =============================================================================
# 请求日志中间件
# =============================================================================

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    请求日志中间件

    记录每个请求的以下信息：
    - 请求方法、路径
    - 客户端 IP
    - 响应状态码
    - 处理耗时
    """

    def __init__(self, app: ASGIApp, logger_name: str = "web.request"):
        """Initialize RequestLoggingMiddleware and prepare runtime dependencies.
        
        Purpose:
            Document service/API behavior, side effects, and integration expectations for maintainers.
        
        Args:
            app: FastAPI application instance where middleware is registered.
            logger_name: Logger namespace used to emit middleware diagnostics.
        
        Returns:
            Any: Runtime-dependent object returned to the calling layer.
        """
        super().__init__(app)
        self.logger = logging.getLogger(logger_name)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process one HTTP request through middleware and return response.
        
        Purpose:
            Document service/API behavior, side effects, and integration expectations for maintainers.
        
        Args:
            request: Incoming FastAPI request object for context/path/header access.
            call_next: ASGI callback that forwards request handling to next middleware.
        
        Returns:
            Response: HTTP response returned by middleware after processing.
        """
        request_id = request.headers.get("X-Request-ID") or new_request_id()
        trace_id = request.headers.get("X-Trace-ID") or request_id
        request.state.request_id = request_id
        request.state.trace_id = trace_id
        context_tokens = bind_request_context(request_id, trace_id)
        timer = RequestMetricsTimer()

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
            duration_seconds = timer.stop()
            record_http_request(method, getattr(request.scope.get("route"), "path", path), status_code, duration_seconds)

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

        response.headers["X-Process-Time"] = f"{duration_seconds * 1000:.2f}ms"
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Trace-ID"] = trace_id
        reset_request_context(context_tokens)
        return response


# =============================================================================
# 速率限制中间件
# =============================================================================

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    速率限制中间件

    基于滑动窗口算法实现请求速率限制。
    支持按 IP 或自定义键进行限制。

    配置参数:
        max_requests: 时间窗口内允许的最大请求数
        window: 时间窗口大小（秒）
        key_func: 自定义键函数，默认按 IP
        exclude_paths: 排除的路径列表
    """

    def __init__(
        self,
        app: ASGIApp,
        max_requests: int = 100,
        window: int = 60,
        key_func: Optional[Callable[[Request], str]] = None,
        exclude_paths: Optional[list] = None
    ):
        """Initialize RateLimitMiddleware and prepare runtime dependencies.
        
        Purpose:
            Document service/API behavior, side effects, and integration expectations for maintainers.
        
        Args:
            app: FastAPI application instance where middleware is registered.
            max_requests: Numeric control parameter `max_requests` used for bounds or pagination.
            window: Numeric control parameter `window` used for bounds or pagination.
            key_func: Callback that builds rate-limit key from incoming request.
            exclude_paths: Filesystem/resource path for `exclude_paths` resolution.
        
        Returns:
            Any: Runtime-dependent object returned to the calling layer.
        """
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window
        self.key_func = key_func or self._default_key_func
        self.exclude_paths = exclude_paths or [
            "/",
            "/docs",
            "/redoc",
            "/rapidoc",
            "/openapi.json",
            "/api/health"
        ]

        # 存储请求记录：{key: deque([timestamp1, timestamp2, ...])}
        self._requests: Dict[str, Deque[float]] = defaultdict(deque)

    def _default_key_func(self, request: Request) -> str:
        """默认键函数：使用客户端 IP"""
        return request.client.host if request.client else "unknown"

    def _clean_old_requests(self, key: str, current_time: float) -> None:
        """清理过期的请求记录"""
        requests = self._requests[key]
        window_start = current_time - self.window

        # 移除超过窗口期的请求记录
        while requests and requests[0] < window_start:
            requests.popleft()

        # 如果没有记录了，删除键
        if not requests:
            del self._requests[key]

    def _check_rate_limit(self, key: str) -> tuple[bool, int]:
        """
        检查速率限制

        Returns:
            (是否允许, 剩余请求数)
        """
        current_time = time.time()
        self._clean_old_requests(key, current_time)

        requests = self._requests[key]
        current_count = len(requests)
        remaining = self.max_requests - current_count

        if current_count >= self.max_requests:
            return False, 0

        # 记录本次请求
        requests.append(current_time)
        return True, remaining

    def _is_excluded(self, path: str) -> bool:
        """检查路径是否排除限流"""
        for exclude in self.exclude_paths:
            if path.startswith(exclude):
                return True
        return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 排除的路径直接通过
        """Process one HTTP request through middleware and return response.
        
        Purpose:
            Document service/API behavior, side effects, and integration expectations for maintainers.
        
        Args:
            request: Incoming FastAPI request object for context/path/header access.
            call_next: ASGI callback that forwards request handling to next middleware.
        
        Returns:
            Response: HTTP response returned by middleware after processing.
        """
        if self._is_excluded(request.url.path):
            return await call_next(request)

        # 获取限流键
        key = self.key_func(request)

        # 检查速率限制
        allowed, remaining = self._check_rate_limit(key)

        if not allowed:
            # 返回 429 响应
            response = JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Rate limit exceeded. Maximum {self.max_requests} requests per {self.window} seconds.",
                        "details": {
                            "max_requests": self.max_requests,
                            "window_seconds": self.window
                        }
                    }
                }
            )
            response.headers["X-RateLimit-Limit"] = str(self.max_requests)
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["X-RateLimit-Reset"] = str(int(time.time() + self.window))
            if hasattr(request.state, "request_id"):
                response.headers["X-Request-ID"] = request.state.request_id
            if hasattr(request.state, "trace_id"):
                response.headers["X-Trace-ID"] = request.state.trace_id
            return response

        # 处理请求
        response = await call_next(request)

        # 添加限流相关 headers
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + self.window))

        return response


# =============================================================================
# 请求超时中间件
# =============================================================================

class TimeoutMiddleware(BaseHTTPMiddleware):
    """
    请求超时中间件

    为请求设置最大处理时间限制。
    """

    def __init__(self, app: ASGIApp, timeout: float = 30.0):
        """Initialize TimeoutMiddleware and prepare runtime dependencies.
        
        Purpose:
            Document service/API behavior, side effects, and integration expectations for maintainers.
        
        Args:
            app: FastAPI application instance where middleware is registered.
            timeout: Numeric control parameter `timeout` used for bounds or pagination.
        
        Returns:
            Any: Runtime-dependent object returned to the calling layer.
        """
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process one HTTP request through middleware and return response.
        
        Purpose:
            Document service/API behavior, side effects, and integration expectations for maintainers.
        
        Args:
            request: Incoming FastAPI request object for context/path/header access.
            call_next: ASGI callback that forwards request handling to next middleware.
        
        Returns:
            Response: HTTP response returned by middleware after processing.
        """
        import asyncio

        try:
            response = await asyncio.wait_for(
                call_next(request),
                timeout=self.timeout
            )
            return response
        except asyncio.TimeoutError:
            emit_structured_log(
                logger,
                "http_request_timeout",
                level=logging.WARNING,
                method=request.method,
                path=request.url.path,
                timeout_seconds=self.timeout,
            )
            response = JSONResponse(
                status_code=504,
                content={
                    "error": {
                        "code": "GATEWAY_TIMEOUT",
                        "message": f"Request processing timeout after {self.timeout} seconds"
                    }
                }
            )
            if hasattr(request.state, "request_id"):
                response.headers["X-Request-ID"] = request.state.request_id
            if hasattr(request.state, "trace_id"):
                response.headers["X-Trace-ID"] = request.state.trace_id
            return response


# =============================================================================
# 便捷函数
# =============================================================================

def setup_middleware(app: FastAPI) -> None:
    """
    配置所有中间件

    Args:
        app: FastAPI 应用实例
    """
    # 添加请求日志中间件
    app.add_middleware(RequestLoggingMiddleware)

    # 添加速率限制中间件（100 请求/分钟）
    app.add_middleware(RateLimitMiddleware, max_requests=100, window=60)

    # 添加超时中间件（30 秒）
    app.add_middleware(TimeoutMiddleware, timeout=30.0)


__all__ = [
    "RequestLoggingMiddleware",
    "RateLimitMiddleware",
    "TimeoutMiddleware",
    "setup_middleware",
]
