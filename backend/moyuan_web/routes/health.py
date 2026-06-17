"""
健康检查路由模块 —— 提供应用健康状态、K8s 探针和监控指标接口。

基础知识：
- K8s 探针（Probe）：Kubernetes 用于检测容器健康状态的机制。
  - 存活探针（Liveness Probe）：检测容器是否仍在运行，失败则重启容器。
  - 就绪探针（Readiness Probe）：检测容器是否已准备好接收流量，失败则从 Service 摘除。
- Prometheus 指标：开源监控系统 Prometheus 采集的时序数据，
  通常以 /metrics 端点暴露，格式为 "metric_name value"。
- SLO（Service Level Objective）：服务等级目标，如"99.9% 的请求在 200ms 内完成"。
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response
from starlette.status import HTTP_200_OK, HTTP_503_SERVICE_UNAVAILABLE

from ..api.schemas.health import (
    HealthResponse,
    LLMHealthResponse,
    ReadinessResponse,
    SimpleStatusResponse,
    ToolHealthResponse,
    ToolIntentHealthResponse,
)
from ..api.error_codes import ApiErrorCode
from ..app_meta import APP_VERSION, build_metadata
from ..observability import metrics_response_payload
from ..config.runtime import get_server_config
from .errors import raise_api_error
from .service_resolver import get_chat_service

router = APIRouter()  # 健康检查路由分组


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    综合健康检查接口 —— 返回 API 健康状态及各依赖服务的初始化状态。

    返回信息包括：API 状态、版本号、时间戳、构建元数据、
    以及 LLM 适配器和会话服务的状态。
    """
    chat_status = await get_chat_service().health_status()

    return HealthResponse(
        status="healthy",
        version=APP_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
        build=build_metadata(),
        services={
            "api": "healthy",
            "llm": "initialized" if chat_status.get("initialized") else "not initialized",
            "sessions": "healthy",
        },
    )


@router.get("/health/llm", response_model=LLMHealthResponse)
async def llm_health_check():
    """
    LLM 健康检查接口 —— 返回 LLM 适配器和工具的就绪详情。

    包括：LLM 是否已初始化、适配器状态、可用工具数量、是否启用记忆功能。
    """
    chat_status = await get_chat_service().health_status()
    return LLMHealthResponse(
        status="ok" if chat_status.get("initialized") else "not initialized",
        llm_adapter=chat_status.get("llm_adapter", False),
        tools_count=chat_status.get("tools_count", 0),
        memory_enabled=chat_status.get("memory_enabled", False),
    )


@router.get("/health/tools", response_model=ToolHealthResponse)
async def tools_health_check():
    """
    工具健康检查接口 —— 返回工具诊断信息和聚合的 SLO 指标。

    用于监控各工具（如天气查询、地图导航等）的调用成功率和延迟。
    """
    status = await get_chat_service().tools_health_status()
    return ToolHealthResponse(**status)


@router.get("/health/tools/intents", response_model=ToolIntentHealthResponse)
async def tools_intents_health_check():
    """
    工具意图健康检查接口 —— 返回监控窗口内每个意图的请求指标。

    应用场景：运维人员查看"查天气"、"规划路线"等意图的调用频率和成功率，
    用于发现某个工具意图的异常情况。
    """
    status = await get_chat_service().tools_intents_health_status()
    return ToolIntentHealthResponse(**status)


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check(request: Request):
    """
    【核心】K8s 就绪探针接口 —— 基于真实启动校验状态判断服务是否就绪。

    从 app.state.readiness_snapshot 读取启动时保存的校验快照：
    - status == "ready" → 返回 200，K8s 将流量路由到该 Pod
    - status != "ready" → 返回 503，K8s 暂停向该 Pod 发送流量

    应用场景：服务启动时需要加载模型、初始化数据库连接等，
    在这些步骤完成前，不应接收用户请求，否则会返回错误。
    """
    snapshot = getattr(
        request.app.state,
        "readiness_snapshot",
        {"status": "starting", "validated_at": None, "checks": {}},
    )
    status_code = HTTP_200_OK if snapshot.get("status") == "ready" else HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        content=ReadinessResponse(**snapshot).model_dump(),
        status_code=status_code,
    )


@router.get("/live", response_model=SimpleStatusResponse)
async def liveness_check():
    """
    K8s 存活探针接口 —— 检测容器进程是否仍在运行。

    若此接口无响应，K8s 将重启该 Pod。只要进程还活着就返回 "alive"。
    """
    return SimpleStatusResponse(status="alive")


@router.get("/metrics", include_in_schema=False)  # 不在 OpenAPI 文档中展示
async def metrics_endpoint():
    """
    暴露 Prometheus 监控指标端点。

    返回后端 API 健康和 SSE 活动的 Prometheus 格式指标数据。
    可通过配置 metrics_enabled 开关控制是否启用此端点。
    """
    try:
        if not get_server_config().metrics_enabled:
            raise_api_error(status_code=404, message="Metrics endpoint is disabled", code=ApiErrorCode.METRICS_DISABLED)
    except HTTPException:
        raise
    except Exception:
        pass  # 配置加载异常时不阻止指标端点，容错处理
    payload, content_type = metrics_response_payload()
    return Response(content=payload, media_type=content_type)
