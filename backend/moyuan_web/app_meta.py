"""
应用元数据模块 —— 版本号、构建信息等全局共享数据

【基础知识】
- 应用元数据（App Metadata）：包括版本号、构建 commit SHA、构建时间等信息，
  通过健康检查端点和根路由暴露给运维和监控系统。
- 版本号优先从环境变量 APP_VERSION 读取（CI/CD 构建时注入），未设置时使用默认值。
- 构建信息（APP_BUILD_SHA、APP_BUILD_CREATED_AT）同理，便于追溯当前运行的代码版本。
"""

from __future__ import annotations

import os
from typing import Any


APP_NAME = "BitBlanket-Travel-Agent API"  # 应用名称
DEFAULT_APP_VERSION = "3.3.0"  # 默认版本号，CI/CD 构建时通过 APP_VERSION 环境变量覆盖
APP_VERSION = str(os.getenv("APP_VERSION", DEFAULT_APP_VERSION)).strip() or DEFAULT_APP_VERSION  # 优先使用环境变量
APP_BUILD_SHA = str(os.getenv("APP_BUILD_SHA", "local")).strip() or "local"  # 构建 commit SHA，默认 "local" 表示本地开发
APP_BUILD_CREATED_AT = str(os.getenv("APP_BUILD_CREATED_AT", "")).strip()  # 构建时间戳


def build_metadata() -> dict[str, Any]:
    """返回构建元数据字典，供健康检查端点和发布制品使用。"""
    return {
        "version": APP_VERSION,
        "sha": APP_BUILD_SHA,
        "created_at": APP_BUILD_CREATED_AT,
    }
