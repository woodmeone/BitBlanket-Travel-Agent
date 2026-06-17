"""SSE 序列化器，将规范化聊天载荷转换为公共 SSE 信封格式。

SSE 信封格式说明：
    SSE 标准格式为 "data: <JSON>\\n\\n"，每个事件以两个换行符结尾。
    客户端通过 EventSource API 的 onmessage 回调接收并解析 JSON 载荷。

    本模块在序列化前还会：
    1. 调用 validate_chat_stream_payload 校验和补充载荷字段
    2. 调用 record_sse_event 记录事件类型用于可观测性统计
"""

from __future__ import annotations

import json
from typing import Any, Iterable


class ChatStreamSSESerializer:
    """将规范化聊天载荷序列化为公共 SSE 信封。"""

    @classmethod
    def serialize_payload(cls, payload: dict[str, Any]) -> str:
        """将单个规范化载荷序列化为 SSE 信封。"""
        return cls.sse(payload)

    @classmethod
    def serialize_payloads(cls, payloads: Iterable[dict[str, Any]]) -> list[str]:
        """将批量规范化载荷序列化为 SSE 信封列表。"""
        return [cls.serialize_payload(payload) for payload in payloads]

    @staticmethod
    def sse(payload: dict[str, Any]) -> str:
        """【核心】将结构化载荷对象序列化为单行 SSE 信封。

        处理流程：
        1. 获取请求上下文（request_id, trace_id）
        2. 校验并补充载荷字段（如添加 request_id）
        3. 记录 SSE 事件类型用于可观测性统计
        4. 格式化为 "data: {JSON}\\n\\n" 格式
        """
        from ...api.events import validate_chat_stream_payload
        from ...observability import get_request_context, record_sse_event

        context = get_request_context()
        normalized_payload = validate_chat_stream_payload(
            payload,
            request_id=context.get("request_id"),
            trace_id=context.get("trace_id"),
        )
        record_sse_event(str(normalized_payload.get("type", "unknown")))
        return f"data: {json.dumps(normalized_payload, ensure_ascii=False)}\n\n"  # SSE 标准格式：data + JSON + 双换行
