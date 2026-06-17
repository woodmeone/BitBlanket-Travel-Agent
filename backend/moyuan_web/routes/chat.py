"""
聊天路由模块 —— 处理用户与 AI 的流式对话请求。

基础知识：
- 路由（Router）：FastAPI 中用于将 URL 路径映射到处理函数的机制。
  APIRouter 类似于 Flask 的 Blueprint，用于将路由分组注册到主应用。
- SSE（Server-Sent Events）：服务端推送技术，服务端可以持续向客户端发送
  事件流，客户端通过 EventSource API 接收。适用于 AI 对话的逐字输出场景，
  用户可以看到 AI 回复逐步生成，而非等待完整响应。
- StreamingResponse：FastAPI 提供的流式响应类，将生成器产出的数据
  以 text/event-stream 格式持续发送给客户端。
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from ..api.schemas.chat import ChatRequest
from .service_resolver import get_chat_service

router = APIRouter()  # 聊天路由分组，注册到主应用时添加前缀


@router.post("/chat/stream")
async def stream_chat(request: ChatRequest, fastapi_request: Request):
    """
    【核心】流式聊天接口 —— 将用户消息转发给 ChatService，以 SSE 流返回 AI 回复。

    处理流程：
    1. 从请求中提取用户消息、会话 ID、模式等参数
    2. 获取请求追踪 ID（request_id、trace_id）用于日志关联
    3. 调用 ChatService.stream_chat() 获取流式生成器
    4. 以 StreamingResponse 包装返回，客户端可逐字接收 AI 回复

    应用场景：用户在聊天界面输入"帮我规划北京三日游"，
    AI 逐步生成行程方案，前端实时展示每个字的出现。

    Args:
        request: 聊天请求体，包含 message、session_id、mode 等字段
        fastapi_request: FastAPI 原始请求对象，用于获取追踪信息
    """
    service = get_chat_service()
    request_id = getattr(fastapi_request.state, "request_id", None)  # 请求唯一标识，用于日志追踪
    trace_id = getattr(fastapi_request.state, "trace_id", None)  # 分布式追踪 ID，用于跨服务链路追踪

    return StreamingResponse(
        service.stream_chat(
            message=request.message,
            display_message=request.display_message,  # 展示给用户的消息（可能与实际消息不同）
            session_id=request.session_id,  # 会话 ID，关联对话上下文
            mode=request.mode,  # 对话模式，如普通聊天、行程规划等
            request_id=request_id,
            trace_id=trace_id,
        ),
        media_type="text/event-stream",  # SSE 标准媒体类型
        headers={
            "Cache-Control": "no-cache",  # 禁止缓存，确保实时接收
            "Connection": "keep-alive",  # 保持长连接
            "X-Accel-Buffering": "no",  # 禁止 Nginx 缓冲，确保 SSE 数据即时推送
            "X-Request-ID": request_id or "",  # 响应头回传请求 ID，便于排查问题
            "X-Trace-ID": trace_id or request_id or "",  # 响应头回传追踪 ID
        },
    )
