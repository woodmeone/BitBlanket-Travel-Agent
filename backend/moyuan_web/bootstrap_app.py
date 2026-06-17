"""【核心】应用组装模块 —— 将所有组件"拼装"成一个完整的 FastAPI 应用。

本模块是后端启动流程的核心，负责：
  1. 创建 FastAPI 实例
  2. 注册异常处理器（统一错误响应格式）
  3. 配置 CORS 跨域策略（允许前端访问后端 API）
  4. 挂载中间件（请求日志、限流、超时控制）
  5. 预热依赖（提前初始化配置管理器和依赖容器）
  6. 注册 API 路由（chat、session、health 等端点）
  7. 注册元数据路由（根路径、OpenAPI 文档）

基础知识：
  - CORS (Cross-Origin Resource Sharing): 浏览器安全策略，默认禁止跨域请求。
    前端运行在 localhost:33001，后端在 localhost:38000，端口不同即为跨域，
    需要后端显式允许前端域名才能正常通信。
  - 中间件 (Middleware): 请求/响应的"拦截器"，在路由处理前后执行通用逻辑
  - SSE (Server-Sent Events): 服务端推送协议，后端持续向前端发送事件流
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from contextlib import asynccontextmanager  # 异步上下文管理器装饰器
from typing import Any

from fastapi import FastAPI, Request  # FastAPI: Web 框架; Request: HTTP 请求对象
from fastapi.middleware.cors import CORSMiddleware  # CORS 中间件，处理跨域请求
from fastapi.responses import JSONResponse  # JSON 响应对象

from moyuan_web.app_meta import APP_NAME, APP_VERSION, build_metadata
from moyuan_web.bootstrap import ensure_project_paths
from moyuan_web.bootstrap_container import initialize_dependency_container
from moyuan_web.config.runtime import get_model_config_manager, get_server_config
from moyuan_web.error_handlers import register_exception_handlers
from moyuan_web.middleware import setup_middleware
from moyuan_web.routes import (
    api_docs_router,
    artifact_router,
    chat_router,
    city_router,
    health_router,
    map_router,
    metrics_endpoint,
    model_router,
    session_router,
    share_router,
)
from moyuan_web.startup_checks import maybe_fail_fast_on_startup

logger = logging.getLogger(__name__)

ensure_project_paths()  # 确保项目路径可导入，在模块加载时立即执行

# 默认允许的跨域来源（前端开发服务器地址）
DEFAULT_CORS_ORIGINS = (
    "http://localhost:33001",  # 前端开发服务器
    "http://localhost:38000",  # 后端自身（用于 API 文档页面）
)


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """应用生命周期管理器 —— 在启动时执行验证，在关闭时清理资源。

    基础知识：
      @asynccontextmanager + yield 是 Python 异步上下文管理器的标准写法。
      yield 之前的代码在应用启动时执行，yield 之后的代码在应用关闭时执行。
      类似于前端的 useEffect 中的 setup 和 cleanup 函数。

    应用场景举例：
      服务启动时，验证 LLM 配置是否可用、数据库是否可连接；
      如果配置了 fail_fast，验证失败则阻止启动。
    """
    app.state.readiness_snapshot = {  # 在 app.state 上存储就绪状态，供 /api/ready 端点读取
        "status": "starting",
        "validated_at": None,
        "checks": {},
    }
    await maybe_fail_fast_on_startup(app)  # 执行启动验证，可能抛出异常阻止启动
    yield  # 应用开始运行，等待关闭信号


def load_server_config_or_none() -> Any:
    """尝试加载服务器配置，失败时返回 None 而非抛异常（容错降级）。"""
    try:
        return get_server_config()
    except Exception as exc:
        logger.warning("Failed to read server config; using middleware defaults: %s", exc)
        return None


def resolve_allowed_origins(
    server_config: Any,
    *,
    env: Mapping[str, str] | None = None,
) -> list[str]:
    """解析允许的 CORS 来源，优先级：环境变量 > 配置文件 > 默认值。

    应用场景举例：
      开发环境: 使用默认值 ["http://localhost:33001", "http://localhost:38000"]
      生产环境: 通过环境变量 CORS_ORIGINS=https://app.example.com 指定
      配置文件: 在 server_config.yaml 的 cors_origins 字段指定

    基础知识：
      os.environ 是一个字典，存储所有环境变量。
      环境变量通常在部署时设置，不需要修改代码即可改变行为。
    """
    env_values = env or os.environ
    env_cors = [item.strip() for item in env_values.get("CORS_ORIGINS", "").split(",") if item.strip()]  # 逗号分隔的环境变量

    try:
        config_cors = list(server_config.cors_origins) if server_config else []
    except Exception as exc:
        logger.warning("Failed to read CORS config; using fallback origins: %s", exc)
        config_cors = []

    return env_cors or config_cors or list(DEFAULT_CORS_ORIGINS)  # 三级降级：环境变量 → 配置文件 → 默认值


def configure_cors(app: FastAPI, *, server_config: Any) -> None:
    """为应用添加 CORS 中间件。

    基础知识：
      CORS 中间件会在每个响应中添加 Access-Control-Allow-* 头部，
      浏览器根据这些头部决定是否允许前端 JavaScript 读取响应。
      allow_credentials=True 表示允许携带 Cookie（用于登录态）。
      allow_methods 指定允许的 HTTP 方法。
      allow_headers=["*"] 表示允许所有请求头。
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolve_allowed_origins(server_config),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # OPTIONS 是浏览器预检请求
        allow_headers=["*"],
    )


def warm_application_dependencies() -> None:
    """预热应用依赖 —— 提前初始化配置管理器和依赖容器，失败不影响启动。

    应用场景举例：
      首次请求到达时如果才初始化，会导致第一个请求响应很慢。
      预热可以确保第一个请求就能快速响应。
    """
    try:
        get_model_config_manager()  # 初始化 LLM 模型配置管理器
        logger.info("Model config manager initialized")
    except Exception as exc:
        logger.warning("Could not initialize model config manager: %s", exc)

    try:
        initialize_dependency_container()  # 初始化依赖注入容器
        logger.info("Dependency container initialized")
    except Exception as exc:
        logger.warning("Could not initialize dependency container: %s", exc)


def should_register_metrics_alias(server_config: Any) -> bool:
    """判断是否需要注册自定义指标路由别名。当配置了非默认路径时才注册。"""
    return bool(
        server_config
        and getattr(server_config, "metrics_enabled", False)
        and getattr(server_config, "metrics_path", None)
        and getattr(server_config, "metrics_path") != "/api/metrics"
    )


def register_api_routes(app: FastAPI, *, server_config: Any) -> None:
    """【核心】注册所有 API 路由 —— 将 URL 路径映射到对应的处理函数。

    每个路由都挂载在 /api 前缀下，例如：
      /api/health  → health_router（健康检查）
      /api/chat/stream → chat_router（聊天流式接口）
      /api/session/new → session_router（创建会话）

    基础知识：
      APIRouter 是 FastAPI 的路由分组机制，类似前端的 React Router 中的 Route 组件。
      prefix="/api" 表示所有路由都以 /api 开头。
      tags 用于 API 文档分组显示。
    """
    app.include_router(health_router, prefix="/api", tags=["health"])  # 健康检查端点
    app.include_router(session_router, prefix="/api", tags=["session"])  # 会话管理端点
    app.include_router(artifact_router, prefix="/api", tags=["artifact"])  # 制品查询端点
    app.include_router(chat_router, prefix="/api", tags=["chat"])  # 聊天流式端点
    app.include_router(model_router, prefix="/api", tags=["model"])  # 模型管理端点
    app.include_router(city_router, prefix="/api", tags=["city"])  # 城市查询端点
    app.include_router(map_router, prefix="/api", tags=["map"])  # 地图路由预览端点
    app.include_router(share_router, prefix="/api", tags=["share"])  # 分享链接端点
    app.include_router(api_docs_router)  # API 文档路由（/rapidoc 等）

    if should_register_metrics_alias(server_config):
        app.add_api_route(
            server_config.metrics_path,
            metrics_endpoint,
            methods=["GET"],
            include_in_schema=False,  # 不在 API 文档中显示
        )


def build_root_payload() -> dict[str, Any]:
    """构建根路径 / 的响应数据，包含应用名称、版本和文档链接。"""
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "build": build_metadata(),
        "docs": "/docs",  # Swagger UI 文档
        "rapidoc": "/rapidoc",  # RapiDoc 文档（更美观的 API 文档界面）
        "redoc": "/redoc",  # ReDoc 文档
        "openapi": "/openapi.json",  # OpenAPI 规范 JSON
    }


def build_openapi_response(app: FastAPI, request: Request) -> JSONResponse:
    """构建 OpenAPI 规范响应，动态注入当前请求的 base_url 作为服务器地址。"""
    openapi_schema = app.openapi()
    base_url = str(request.base_url).rstrip("/")
    openapi_schema["servers"] = [{"url": base_url, "description": "Current server"}]
    return JSONResponse(content=openapi_schema)


def register_metadata_routes(app: FastAPI) -> None:
    """注册元数据路由：根路径和 OpenAPI 规范端点。"""

    @app.get("/")
    async def root() -> dict[str, Any]:
        """根路径，返回应用元信息和文档链接。"""
        return build_root_payload()

    @app.get("/openapi.json", include_in_schema=False)
    async def get_openapi_spec(request: Request) -> JSONResponse:
        """返回 OpenAPI 规范 JSON，包含动态服务器地址。"""
        return build_openapi_response(app, request)


def create_web_application() -> FastAPI:
    """【核心】创建并配置完整的 FastAPI 应用实例。

    组装顺序（重要，顺序影响中间件和路由的执行）：
      1. 注册异常处理器 → 2. 配置 CORS → 3. 挂载中间件
      → 4. 预热依赖 → 5. 注册路由 → 6. 注册元数据路由
    """
    server_config = load_server_config_or_none()
    app = FastAPI(
        title=APP_NAME,
        description="AI Travel Assistant API with SSE streaming support.",
        version=APP_VERSION,
        docs_url=None,  # 禁用默认 Swagger UI（使用自定义 /rapidoc 代替）
        redoc_url=None,  # 禁用默认 ReDoc
        openapi_url="/openapi.json",
        lifespan=app_lifespan,  # 绑定生命周期管理器
    )

    register_exception_handlers(app)  # 注册统一异常处理器
    configure_cors(app, server_config=server_config)  # 配置 CORS 跨域
    setup_middleware(app)  # 挂载请求日志、限流、超时中间件
    warm_application_dependencies()  # 预热依赖（配置管理器、依赖容器）
    register_api_routes(app, server_config=server_config)  # 注册所有 API 路由
    register_metadata_routes(app)  # 注册根路径和 OpenAPI 端点
    return app


__all__ = [
    "DEFAULT_CORS_ORIGINS",
    "app_lifespan",
    "build_openapi_response",
    "build_root_payload",
    "configure_cors",
    "create_web_application",
    "load_server_config_or_none",
    "register_api_routes",
    "register_metadata_routes",
    "resolve_allowed_origins",
    "should_register_metrics_alias",
    "warm_application_dependencies",
]
