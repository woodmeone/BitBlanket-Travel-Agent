"""
API 错误处理工具模块 —— 提供统一的错误响应格式和校验错误转换。

基础知识：
- HTTPException：FastAPI 内置的异常类，抛出后框架自动将其转为 HTTP 错误响应。
  构造参数包括 status_code（状态码）和 detail（错误详情）。
- 统一错误格式：本模块将所有 API 错误统一为 {"success": False, "error": "...", "code": "..."}
  的标准格式，前端可据此统一处理错误逻辑（如根据 code 显示不同提示）。
- RequestValidationError：FastAPI 在请求参数校验失败时自动抛出的异常，
  包含每个字段的校验错误详情。本模块将其转换为与业务错误一致的格式。
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError

from ..api.error_codes import ApiErrorCode


def error_detail(
    message: str,
    code: str | ApiErrorCode | None = None,
    *,
    details: dict[str, Any] | list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    构建标准化的 API 错误负载。

    Args:
        message: 错误描述信息，如 "Session not found"
        code: 业务错误码，如 ApiErrorCode.SESSION_NOT_FOUND
        details: 额外的错误详情，如字段校验错误列表

    Returns:
        标准错误字典，格式为 {"success": False, "error": "...", "code": "...", "details": ...}
    """
    detail: dict[str, Any] = {"success": False, "error": message}
    if code:
        detail["code"] = str(code)
    if details is not None:
        detail["details"] = details
    return detail


def validation_error_detail(exc: RequestValidationError) -> dict[str, Any]:
    """
    将 FastAPI 请求校验错误转换为统一的 API 错误格式。

    FastAPI 原始校验错误格式较为复杂，此函数将其简化为：
    [{"field": "session_id", "message": "...", "issueType": "...", "input": ...}]

    应用场景：用户提交表单时字段格式不正确（如 session_id 包含非法字符），
    前端根据返回的 field 和 message 在对应输入框旁显示错误提示。

    Args:
        exc: FastAPI 抛出的请求校验异常
    """

    issues: list[dict[str, Any]] = []
    for entry in exc.errors():
        # 将错误位置元组（如 ("body", "session_id")）转为点分路径（"body.session_id"）
        location = ".".join(str(part) for part in entry.get("loc", ()) if part != "__root__")
        issues.append(
            {
                "field": location or "request",  # 字段路径，无法定位时标记为 "request"
                "message": str(entry.get("msg") or "Invalid value"),  # 人类可读的错误描述
                "issueType": str(entry.get("type") or "value_error"),  # 错误类型，如 "value_error"、"type_error"
                "input": entry.get("input"),  # 用户实际输入的值，便于调试
            }
        )
    return error_detail(
        "Request validation failed.",
        ApiErrorCode.REQUEST_VALIDATION_FAILED,
        details=issues,
    )


def raise_api_error(
    status_code: int,
    message: str,
    code: str | ApiErrorCode | None = None,
    *,
    details: dict[str, Any] | list[dict[str, Any]] | None = None,
) -> None:
    """
    抛出带有统一错误格式的 HTTPException。

    封装了 error_detail() + HTTPException 的组合调用，
    确保所有路由抛出的错误格式一致。

    Args:
        status_code: HTTP 状态码，如 404、400
        message: 错误描述信息
        code: 业务错误码
        details: 额外错误详情
    """
    raise HTTPException(status_code=status_code, detail=error_detail(message=message, code=code, details=details))
