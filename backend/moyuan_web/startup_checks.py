"""
启动校验与就绪快照构建模块

【基础知识】
- 就绪检查（Readiness Check）：Kubernetes 等容器编排系统通过就绪探针判断服务是否可以接收流量。
  本模块在应用启动时执行一系列校验（配置、数据目录、LLM、依赖容器、聊天运行时），
  生成就绪快照供 /api/ready 端点返回。

- 快速失败（Fail Fast）：当配置项 fail_fast_startup_validation=True 时，
  启动校验失败会直接抛出 RuntimeError 阻止应用启动，
  避免以不完整状态上线导致线上故障。
"""

from __future__ import annotations

import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from moyuan_web.bootstrap_container import initialize_dependency_container
from moyuan_web.bootstrap import PROJECT_ROOT
from moyuan_web.config.runtime import get_llm_config_path, get_model_config_manager, get_server_config
from moyuan_web.observability import emit_structured_log, set_readiness_state

logger = logging.getLogger(__name__)


def _check_ok(name: str, message: str, **details: Any) -> dict[str, Any]:
    """构建一条成功的就绪检查记录。"""
    return {
        "name": name,
        "status": "ok",
        "message": message,
        "details": details,
    }


def _check_not_ready(name: str, message: str, **details: Any) -> dict[str, Any]:
    """构建一条失败的就绪检查记录。"""
    return {
        "name": name,
        "status": "not_ready",
        "message": message,
        "details": details,
    }


async def build_startup_readiness_snapshot() -> dict[str, Any]:
    """【核心】执行启动校验并返回就绪快照。

    依次检查 5 个关键项：
    1. server_config —— 服务配置是否可解析
    2. data_dir —— 数据目录是否可写（会话、记忆、检查点等运行时数据）
    3. llm_config —— LLM 配置文件是否存在且包含可用模型
    4. container —— 依赖注入容器能否解析 SessionRepository 和 ChatService
    5. chat_runtime —— 聊天运行时是否初始化成功

    所有检查通过时 status="ready"，否则 status="not_ready"。
    """
    checks: dict[str, dict[str, Any]] = {}

    # 1) 服务配置：可回退到默认值，但需展示生效的配置信息
    try:
        server_config = get_server_config()
        config_path = Path(PROJECT_ROOT) / "config" / "server_config.yaml"
        checks["server_config"] = _check_ok(
            "server_config",
            "Server configuration resolved.",
            config_path=str(config_path),
            exists=config_path.exists(),
            web_host=server_config.web_host,
            web_port=server_config.web_port,
            frontend_port=server_config.frontend_port,
            metrics_enabled=server_config.metrics_enabled,
        )
    except Exception as exc:
        checks["server_config"] = _check_not_ready("server_config", f"Failed to resolve server config: {exc}")

    # 2) 数据目录：会话、记忆、检查点、回放输出都需要写入该目录
    data_dir = Path(PROJECT_ROOT) / "data"
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=data_dir, prefix=".startup-", delete=True):  # 尝试在数据目录创建临时文件以验证写入权限
            pass
        checks["data_dir"] = _check_ok("data_dir", "Runtime data directory is writable.", path=str(data_dir))
    except Exception as exc:
        checks["data_dir"] = _check_not_ready("data_dir", f"Runtime data directory is not writable: {exc}", path=str(data_dir))

    # 3) LLM 配置：需存在且至少包含一个活跃模型，否则无法处理聊天请求
    llm_path = Path(get_llm_config_path())
    if not llm_path.exists():
        checks["llm_config"] = _check_not_ready(
            "llm_config",
            "LLM configuration file is missing.",
            path=str(llm_path),
        )
    else:
        try:
            model_manager = get_model_config_manager()
            available_models = model_manager.get_available_models()
            if not available_models:
                checks["llm_config"] = _check_not_ready(
                    "llm_config",
                    "No active model configuration is available.",
                    path=str(llm_path),
                    default_model=model_manager.get_default_model_id(),
                )
            else:
                checks["llm_config"] = _check_ok(
                    "llm_config",
                    "LLM configuration loaded.",
                    path=str(llm_path),
                    default_model=model_manager.get_default_model_id(),
                    active_models=[item["model_id"] for item in available_models],
                )
        except Exception as exc:
            checks["llm_config"] = _check_not_ready(
                "llm_config",
                f"Failed to load model configuration: {exc}",
                path=str(llm_path),
            )

    # 4) 依赖注入容器：验证 SessionRepository 和 ChatService 能否正常解析
    try:
        container = initialize_dependency_container()
        _ = container.resolve("SessionRepository")
        chat_service = container.resolve("ChatService")
        checks["container"] = _check_ok(
            "container",
            "Dependency container resolved required services.",
            services=["SessionRepository", "ChatService"],
        )
    except Exception as exc:
        checks["container"] = _check_not_ready("container", f"Failed to resolve dependency container: {exc}")
        chat_service = None

    if checks["llm_config"]["status"] == "ok" and chat_service is not None:  # 仅在前置条件满足时初始化聊天运行时
        try:
            await chat_service.initialize()
            runtime_status = await chat_service.health_status()  # 获取运行时健康状态（工具数、记忆等）
            checks["chat_runtime"] = _check_ok(
                "chat_runtime",
                "Chat runtime initialized.",
                initialized=runtime_status.get("initialized", False),
                tools_count=runtime_status.get("tools_count", 0),
                memory_enabled=runtime_status.get("memory_enabled", False),
            )
        except Exception as exc:
            checks["chat_runtime"] = _check_not_ready("chat_runtime", f"Chat runtime initialization failed: {exc}")
    else:
        checks["chat_runtime"] = _check_not_ready(
            "chat_runtime",
            "Chat runtime skipped because prerequisites are not ready.",
        )

    mandatory_checks = ("server_config", "data_dir", "llm_config", "container", "chat_runtime")  # 所有5项均为必需检查
    ready = all(checks[name]["status"] == "ok" for name in mandatory_checks)
    snapshot = {
        "status": "ready" if ready else "not_ready",
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }
    set_readiness_state(ready)  # 更新 Prometheus 就绪状态指标
    emit_structured_log(  # 记录启动校验结果的结构化日志
        logger,
        "startup_validation",
        status=snapshot["status"],
        checks={name: item["status"] for name, item in checks.items()},
    )
    return snapshot


async def refresh_app_readiness_state(app: Any) -> dict[str, Any]:
    """刷新就绪快照并缓存到 FastAPI 应用对象上，供 /api/ready 端点读取。"""
    snapshot = await build_startup_readiness_snapshot()
    app.state.readiness_snapshot = snapshot
    return snapshot


def readiness_requires_fail_fast() -> bool:
    """判断启动校验是否需要快速失败（校验不通过则阻止应用启动）。"""
    try:
        server_config = get_server_config()
        return bool(server_config.fail_fast_startup_validation)
    except Exception:
        return False


async def maybe_fail_fast_on_startup(app: Any) -> dict[str, Any]:
    """刷新就绪快照，若配置了快速失败且校验不通过则抛出 RuntimeError。

    应用场景：生产环境中，如果 LLM 配置缺失或数据目录不可写，
    应阻止服务启动而非以降级状态上线，避免用户遇到不可预期的错误。
    """
    snapshot = await refresh_app_readiness_state(app)
    if snapshot.get("status") != "ready" and readiness_requires_fail_fast():
        failed = [name for name, item in snapshot.get("checks", {}).items() if item.get("status") != "ok"]
        raise RuntimeError(f"Startup validation failed: {', '.join(failed)}")
    return snapshot
