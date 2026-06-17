"""
依赖提供者模块 —— 兼容性重新导出

【基础知识】
- 依赖注入（Dependency Injection）：FastAPI 通过 Depends() 机制实现依赖注入，
  路由函数声明所需的服务，框架自动从提供者获取实例。
  例：def chat(request: Request, service: ChatService = Depends(provide_chat_service))

- 本模块从 bootstrap_services 重新导出所有服务提供者函数，
  使路由代码可以通过 from moyuan_web.dependencies.providers import ... 获取，
  而无需直接依赖 bootstrap_services 的内部实现。

- 提供者函数列表：
  - provide_chat_service：聊天服务（核心业务逻辑）
  - provide_session_service：会话服务（会话管理）
  - provide_session_repository：会话仓库（数据持久化）
  - provide_share_service：分享服务（会话分享）
  - provide_share_repository：分享仓库（分享数据持久化）
  - provide_city_service：城市服务（城市信息查询）
  - provide_map_service：地图服务（路线规划）
  - provide_travel_agent：旅行代理（Agent 编排）
  - register_default_services：注册默认服务到依赖容器
"""

from __future__ import annotations

from ..bootstrap_services import (
    provide_chat_service,
    provide_city_service,
    provide_map_service,
    provide_session_repository,
    provide_session_service,
    provide_share_repository,
    provide_share_service,
    provide_travel_agent,
    register_default_services,
)

__all__ = [
    "provide_chat_service",
    "provide_city_service",
    "provide_map_service",
    "provide_session_repository",
    "provide_session_service",
    "provide_share_repository",
    "provide_share_service",
    "provide_travel_agent",
    "register_default_services",
]
