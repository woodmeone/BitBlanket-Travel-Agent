"""
API 错误码枚举 —— 校验、路由处理器、文档共享的标准化错误标识

【基础知识】
- 错误码（Error Code）：使用字符串枚举代替裸数字或魔法字符串，
  确保前后端对错误含义的理解一致。客户端可根据 code 做差异化处理，
  而非依赖 HTTP 状态码或错误消息文本。

- StrEnum：Python 3.11+ 的字符串枚举基类，枚举值本身就是字符串，
  序列化时直接输出字符串而非枚举对象，适合 API 响应。
"""

from __future__ import annotations

from enum import StrEnum


class ApiErrorCode(StrEnum):
    """稳定的 API 错误码，暴露给客户端和维护者文档。

    每个错误码对应一类具体的业务异常，前端可据此展示不同提示或执行不同逻辑。
    例：SESSION_NOT_FOUND → 提示"会话不存在"并引导创建新会话；
         RATE_LIMIT_EXCEEDED → 提示"请求过于频繁"并显示倒计时。
    """

    REQUEST_VALIDATION_FAILED = "REQUEST_VALIDATION_FAILED"  # 请求参数校验失败（如字段缺失、格式错误）
    INVALID_ARGUMENT = "INVALID_ARGUMENT"  # 无效参数（如传入不支持的聊天模式）
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"  # 会话不存在（如访问已删除的会话ID）
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"  # 模型不存在（如请求了未配置的 LLM 模型）
    CITY_NOT_FOUND = "CITY_NOT_FOUND"  # 城市不存在（如查询了系统未收录的城市）
    SHARE_INVALID = "SHARE_INVALID"  # 分享链接无效（如格式错误或已过期）
    SHARE_NOT_FOUND = "SHARE_NOT_FOUND"  # 分享链接不存在（如访问了未创建的分享ID）
    MAP_ROUTE_INVALID = "MAP_ROUTE_INVALID"  # 路线规划参数无效（如起点终点相同）
    MAP_ROUTE_ERROR = "MAP_ROUTE_ERROR"  # 路线规划计算失败（如地图服务不可用）
    METRICS_DISABLED = "METRICS_DISABLED"  # 指标端点已禁用（如配置中关闭了 metrics）
    HTTP_ERROR = "HTTP_ERROR"  # 通用 HTTP 错误（兜底错误码）
