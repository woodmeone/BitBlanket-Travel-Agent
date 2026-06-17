"""【核心】FastAPI 应用入口 —— 后端服务的启动点。

本模块是整个后端 Web 服务的入口文件，职责：
  1. 创建 FastAPI 应用实例（通过 bootstrap 辅助函数组装）
  2. 提供 CLI 启动方式（通过 uvicorn 运行 ASGI 服务器）

基础知识：
  - FastAPI: Python 的高性能 Web 框架，自动生成 OpenAPI 文档
  - uvicorn: ASGI 服务器，负责接收 HTTP 请求并转交给 FastAPI 处理
  - ASGI: 异步服务器网关接口，是 WSGI 的异步升级版

运行方式：
  命令行: python -m moyuan_web.main --host 0.0.0.0 --port 38000 --debug
  默认端口: 38000
"""

from __future__ import annotations

import argparse  # 命令行参数解析库，用于解析 --host, --port, --debug 等参数
import logging

import uvicorn  # ASGI 服务器，将 HTTP 请求转发给 FastAPI 应用处理

from moyuan_web.bootstrap_app import create_web_application  # 应用组装函数，负责创建完整的 FastAPI 实例
from moyuan_web.config.runtime import get_server_config  # 获取服务器配置（端口、主机等）

logger = logging.getLogger(__name__)

def create_app():
    """创建 FastAPI 应用实例。供 uvicorn 或测试框架调用。"""
    return create_web_application()


app = create_app()  # 模块级变量：FastAPI 应用实例。uvicorn 通过 "moyuan_web.main:app" 引用它


def main(host: str = "0.0.0.0", port: int = 38000, debug: bool = False) -> None:
    """启动 uvicorn 服务器。

    优先使用配置文件中的 host/port，CLI 参数仅在未指定时生效。
    debug 模式下启用热重载（文件修改后自动重启服务）。

    应用场景举例：
      开发环境: python -m moyuan_web.main --debug  → 代码修改后自动重启
      生产环境: python -m moyuan_web.main --port 38000  → 使用固定端口
    """
    try:
        server_config = get_server_config()  # 从 YAML 配置文件加载服务器配置

        # 仅在 CLI 使用默认值时才用配置文件覆盖，用户显式指定的参数优先
        if host == "0.0.0.0":
            host = server_config.web_host
        if port == 38000:
            port = server_config.web_port
    except Exception as exc:
        logger.warning("Failed to load server config; falling back to defaults: %s", exc)

    uvicorn.run(
        "moyuan_web.main:app",  # 告诉 uvicorn 去哪里找 FastAPI 实例（模块路径:变量名）
        host=host,
        port=port,
        reload=debug,  # debug=True 时启用热重载
        log_level="info",
        timeout_keep_alive=30,  # Keep-Alive 连接超时时间（秒）
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="moyuan-travel-agent Web Server")
    parser.add_argument("--host", default="0.0.0.0", help="Server host")
    parser.add_argument("--port", type=int, default=38000, help="Server port")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    args = parser.parse_args()
    main(args.host, args.port, args.debug)
