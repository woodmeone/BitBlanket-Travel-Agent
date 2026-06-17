"""
服务解析器模块 —— 路由层共享的服务实例获取工具。

基础知识：
- 依赖注入（Dependency Injection）：一种设计模式，将对象的创建和使用分离。
  本项目通过 IoC 容器（Container）管理所有服务实例的生命周期，
  路由层通过 resolve(name) 按名称获取服务，无需关心实例化细节。
- IoC 容器（Inversion of Control Container）：控制反转容器，
  负责注册和解析服务实例。所有服务在应用启动时注册到容器中，
  运行时通过名称查找获取。好处是解耦了路由层和服务实现层，
  方便替换实现和单元测试时 mock。
"""

from __future__ import annotations

from typing import Any

from ..dependencies.container import get_container
from ..services.artifact_service import ArtifactService
from ..services.chat_service import ChatService
from ..services.city_service import CityService
from ..services.map_service import MapService
from ..services.session_service import SessionService
from ..services.share_service import ShareService


def resolve_service(name: str) -> Any:
    """
    从共享 IoC 容器中解析指定名称的服务实例。

    Args:
        name: 服务注册名称，如 "ChatService"、"SessionService" 等
    """
    return get_container().resolve(name)


def get_chat_service() -> ChatService:
    """获取聊天服务实例，用于流式对话和消息查询。"""
    return resolve_service("ChatService")


def get_artifact_service() -> ArtifactService:
    """获取产物服务实例，用于行程方案的存取。"""
    return resolve_service("ArtifactService")


def get_city_service() -> CityService:
    """获取城市服务实例，用于城市信息查询。"""
    return resolve_service("CityService")


def get_map_service() -> MapService:
    """获取地图服务实例，用于路线预览。"""
    return resolve_service("MapService")


def get_session_service() -> SessionService:
    """获取会话服务实例，用于会话生命周期管理。"""
    return resolve_service("SessionService")


def get_share_service() -> ShareService:
    """获取分享服务实例，用于分享链接的生成。"""
    return resolve_service("ShareService")
