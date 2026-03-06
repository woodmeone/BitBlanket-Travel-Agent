"""健康检查API路由模块

提供服务健康状态检查的RESTful API接口。

API端点:
- GET /health - 详细健康检查
- GET /ready - 就绪检查
- GET /live - 存活检查
- GET /health/llm - LLM 服务状态
"""

from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

# 全局状态 (从 chat_langchain 导入)
try:
    from .chat_langchain import _llm_adapter, _tools, _sessions
except ImportError:
    _llm_adapter = None
    _tools = None
    _sessions = {}


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str
    version: str
    timestamp: str
    services: dict


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    详细健康检查端点

    返回完整的健康状态信息：
    - 服务总体状态
    - 应用版本
    - 各服务状态
    """
    return HealthResponse(
        status="healthy",
        version="3.2.0",
        timestamp=datetime.now().isoformat(),
        services={
            "api": "healthy",
            "llm": "initialized" if _llm_adapter else "not initialized",
            "sessions": "healthy"
        }
    )


@router.get("/health/llm")
async def llm_health_check():
    """LLM 服务健康检查"""
    return {
        "status": "ok" if _llm_adapter else "not initialized",
        "llm_adapter": _llm_adapter is not None,
        "tools_count": len(_tools) if _tools else 0,
        "sessions_count": len(_sessions) if _sessions else 0
    }


@router.get("/ready")
async def readiness_check():
    """就绪检查端点 - 判断服务是否准备好接收流量"""
    return {"status": "ready"}


@router.get("/live")
async def liveness_check():
    """存活检查端点 - 判断服务是否正在运行"""
    return {"status": "alive"}
