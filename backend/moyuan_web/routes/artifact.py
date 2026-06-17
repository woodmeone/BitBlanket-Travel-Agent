"""
产物（Artifact）检索路由模块 —— 提供行程方案的查询和历史版本接口。

基础知识：
- Artifact（产物）：AI 生成的结构化成果，如行程方案、景点推荐列表等。
  每次对话中 AI 可能生成新的行程方案，系统会持久化保存每个版本。
- 最新产物 vs 历史产物：latest 获取最近一次生成的方案，
  history 获取所有历史版本（按时间倒序），支持用户回溯和比较。
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query

from ..api.error_codes import ApiErrorCode
from ..api.schemas import ArtifactHistoryResponse, LatestArtifactResponse
from ..api.validation import SESSION_ID_PATTERN
from .errors import raise_api_error
from .service_resolver import get_artifact_service

router = APIRouter()  # 产物路由分组

# 会话 ID 路径参数：长度 1~128，必须匹配 SESSION_ID_PATTERN 正则
SessionIdParam = Annotated[str, Path(min_length=1, max_length=128, pattern=SESSION_ID_PATTERN)]


@router.get("/artifacts/{session_id}/latest", response_model=LatestArtifactResponse)
async def get_latest_artifact(session_id: SessionIdParam):
    """
    获取指定会话的最新行程方案产物。

    应用场景：用户打开某个会话时，前端调用此接口获取最新生成的行程方案，
    无需加载完整历史记录。

    Args:
        session_id: 会话 ID
    """
    service = get_artifact_service()
    result = await service.get_latest_artifact(session_id)
    if not result.get("success"):
        raise_api_error(status_code=404, message=result.get("error", "Session not found"), code=ApiErrorCode.SESSION_NOT_FOUND)
    return result


@router.get("/artifacts/{session_id}/history", response_model=ArtifactHistoryResponse)
async def get_artifact_history(session_id: SessionIdParam, limit: int = Query(default=10, ge=1, le=50)):
    """
    获取指定会话的行程方案历史版本列表（按时间倒序）。

    应用场景：用户想查看之前的行程方案版本，对比不同版本的差异，
    或恢复到之前的某个方案。

    Args:
        session_id: 会话 ID
        limit: 返回的最大版本数量，默认 10，范围 1~50
    """
    service = get_artifact_service()
    result = await service.get_artifact_history(session_id, limit=limit)
    if not result.get("success"):
        raise_api_error(status_code=404, message=result.get("error", "Session not found"), code=ApiErrorCode.SESSION_NOT_FOUND)
    return result
