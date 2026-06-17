"""
应用级异常处理器 —— 统一 API 错误响应格式

【基础知识】
- 异常处理器（Exception Handler）：FastAPI 允许为特定异常类型注册全局处理函数，
  当路由抛出该类型异常时，由处理器统一生成响应，确保所有错误返回一致的 JSON 结构。

- RequestValidationError：Pydantic 请求模型校验失败时自动抛出，
  例如用户提交的 chat 请求缺少 message 字段，或 session_id 格式不合法。

- HTTPException：FastAPI 路由中主动抛出的 HTTP 错误（如 404、403），
  本模块将其 detail 统一转换为标准错误格式。
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .api.error_codes import ApiErrorCode
from .routes.errors import error_detail, validation_error_detail


def _normalize_http_exception_detail(detail: Any) -> dict[str, Any]:
    """将 HTTPException 的原始 detail 转换为统一的 API 错误格式。

    如果 detail 已经是标准格式（包含 success=False 和 error 字段），直接返回；
    否则将其包装为 {"message": ..., "code": "HTTP_ERROR"} 的标准形状。
    例：HTTPException(detail="Not Found") → {"message": "Not Found", "code": "HTTP_ERROR"}
    """

    if isinstance(detail, dict) and detail.get("success") is False and detail.get("error"):  # 已是标准格式则直接透传
        return detail
    return error_detail(message=str(detail), code=ApiErrorCode.HTTP_ERROR)


def register_exception_handlers(app: FastAPI) -> None:
    """【核心】向 FastAPI 应用注册全局异常处理器，统一错误响应格式。

    注册两类处理器：
    1. RequestValidationError → 422：请求参数校验失败（如字段缺失、格式错误）
    2. HTTPException → 对应状态码：路由主动抛出的 HTTP 错误
    """

    @app.exception_handler(RequestValidationError)
    async def _validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        """处理请求参数校验异常，返回 422 和标准化错误详情。"""
        return JSONResponse(status_code=422, content={"detail": validation_error_detail(exc)})

    @app.exception_handler(HTTPException)
    async def _http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        """处理 HTTP 异常，将 detail 标准化后返回对应状态码的响应。"""
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": _normalize_http_exception_detail(exc.detail)},
            headers=exc.headers,
        )
