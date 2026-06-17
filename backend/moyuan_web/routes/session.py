"""
会话管理路由模块 —— 提供聊天会话的增删改查及模型绑定功能。

基础知识：
- 会话（Session）：一次完整的对话上下文，包含多条消息。
  用户可以创建多个会话，每个会话独立维护对话历史。
- 路径参数校验：FastAPI 通过 Annotated[type, Path(...)] 对 URL 路径参数
  进行类型和格式校验。例如 SessionIdParam 限制 session_id 长度和格式。
- Annotated 类型注解：Python 3.9+ 引入的语法，将元数据附加到类型提示上，
  FastAPI 利用它实现参数校验和文档生成。
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query

from ..api.error_codes import ApiErrorCode
from ..api.schemas.session import SetModelRequest, UpdateNameRequest
from ..api.validation import NON_BLANK_TEXT_PATTERN, SESSION_ID_PATTERN
from ..config.runtime import get_model_config_manager
from .errors import raise_api_error
from .service_resolver import get_chat_service, get_session_service

router = APIRouter()  # 会话路由分组


def _raise_not_found(message: str) -> None:
    """
    抛出标准的"会话未找到"错误响应。

    统一使用 ApiErrorCode.SESSION_NOT_FOUND 错误码和 404 状态码，
    确保所有会话相关接口返回一致的错误格式。
    """
    raise_api_error(status_code=404, message=message, code=ApiErrorCode.SESSION_NOT_FOUND)


# 会话 ID 路径参数：长度 1~128，必须匹配 SESSION_ID_PATTERN 正则
SessionIdParam = Annotated[str, Path(min_length=1, max_length=128, pattern=SESSION_ID_PATTERN)]
# 可选的会话名称查询参数：长度 1~120，必须匹配非空白文本正则
OptionalSessionNameQuery = Annotated[str | None, Query(min_length=1, max_length=120, pattern=NON_BLANK_TEXT_PATTERN)]


@router.post("/session/new")
async def create_session(name: OptionalSessionNameQuery = None):
    """
    创建新的聊天会话。

    Args:
        name: 可选的会话名称，如"北京三日游规划"。不传则使用默认名称。
    """
    service = get_session_service()
    return await service.create_session(name=name)


@router.get("/sessions")
async def list_sessions(include_empty: bool = False):
    """
    获取会话列表。

    Args:
        include_empty: 是否包含空会话（无消息的会话），默认不包含。
    """
    service = get_session_service()
    return await service.list_sessions(include_empty=include_empty)


@router.delete("/session/{session_id}")
async def delete_session(session_id: SessionIdParam):
    """
    删除指定会话及其所有关联消息。

    Args:
        session_id: 要删除的会话 ID
    """
    service = get_session_service()
    result = await service.delete_session(session_id)
    if not result.get("success"):
        _raise_not_found(result.get("error", "Session not found"))
    return result


@router.put("/session/{session_id}/name")
async def update_session_name(session_id: SessionIdParam, request: UpdateNameRequest):
    """
    更新会话的显示名称。

    应用场景：用户将会话从默认名称重命名为有意义的名称，
    如将"新对话"改为"上海美食攻略"。

    Args:
        session_id: 会话 ID
        request: 包含新名称的请求体
    """
    service = get_session_service()
    result = await service.update_session_name(session_id, request.name)
    if not result.get("success"):
        _raise_not_found(result.get("error", "Session not found"))
    return result


@router.put("/session/{session_id}/model")
async def set_session_model(session_id: SessionIdParam, request: SetModelRequest):
    """
    【核心】为会话绑定指定的 AI 模型。

    应用场景：用户在对话中切换模型，例如从 GPT-4o 切换到 Claude，
    后续该会话的 AI 回复将使用新绑定的模型。

    处理逻辑：
    1. 校验请求的 model_id 是否在可用模型列表中
    2. 调用 SessionService 更新会话的模型绑定

    Args:
        session_id: 会话 ID
        request: 包含 model_id 的请求体
    """
    model_id = request.model_id
    # 从配置管理器获取所有可用模型 ID，校验请求的模型是否合法
    known_model_ids = {str(item["model_id"]) for item in get_model_config_manager().get_available_models()}
    if model_id not in known_model_ids:
        raise_api_error(
            status_code=404,
            message=f"Model not found: {model_id}",
            code=ApiErrorCode.MODEL_NOT_FOUND,
            details={"model_id": model_id},
        )

    service = get_session_service()
    result = await service.update_session_model(session_id, model_id)
    if not result.get("success"):
        _raise_not_found(result.get("error", "Session not found"))
    return result


@router.get("/session/{session_id}/model")
async def get_session_model(session_id: SessionIdParam):
    """
    获取会话当前绑定的模型信息。

    Args:
        session_id: 会话 ID
    """
    service = get_session_service()
    result = await service.get_session_model(session_id)
    if not result.get("success"):
        _raise_not_found(result.get("error", "Session not found"))
    return result


@router.get("/session/{session_id}/messages")
async def get_session_messages(session_id: SessionIdParam):
    """
    获取指定会话的消息历史记录。

    Args:
        session_id: 会话 ID
    """
    service = get_chat_service()
    result = await service.get_messages(session_id)
    if not result.get("success"):
        _raise_not_found(result.get("error", "Session not found"))
    return result


@router.post("/clear/{session_id}")
async def clear_chat(session_id: SessionIdParam):
    """
    清空指定会话的所有消息（会话本身保留）。

    应用场景：用户想重新开始对话，但保留当前会话的模型绑定等设置。

    Args:
        session_id: 会话 ID
    """
    service = get_session_service()
    result = await service.clear_chat(session_id)
    if not result.get("success"):
        _raise_not_found(result.get("error", "Session not found"))
    return result
