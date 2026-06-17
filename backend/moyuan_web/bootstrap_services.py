"""
Web 服务默认依赖容器引导模块。

本模块负责在应用启动时，将所有后端服务（会话、聊天、城市、地图、分享等）
注册到依赖注入容器中，供 FastAPI 路由按需获取。

【基础知识：依赖注入（Dependency Injection, DI）】
依赖注入是一种设计模式，核心思想是"不由使用方自己创建依赖，而由外部容器提供"。
例如：路由处理函数需要 SessionService，不自己 new，而是通过 container.resolve("SessionService") 获取。
好处：解耦、方便测试（可替换为 Mock）、统一管理生命周期（单例/多例）。

【基础知识：单例模式（Singleton）】
单例模式确保一个类在整个应用生命周期中只有一个实例。
本模块通过模块级全局变量（如 _repository、_session_service 等）实现单例：
首次调用 provide_xxx() 时创建实例，后续调用直接返回已有实例。
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from .bootstrap import PROJECT_ROOT, ensure_project_paths
from .config.runtime import get_server_config

# 【核心】确保项目根路径已加入 sys.path，使后续 import 能正确解析
ensure_project_paths()

if TYPE_CHECKING:
    from .dependencies.container import Container


# ── 模块级单例变量 ──────────────────────────────────────────────
# 每个变量对应一个服务的唯一实例，初始为 None，由 provide_xxx() 延迟创建。
# 延迟创建（懒加载）的好处：应用启动时不会加载所有服务，只在首次使用时才初始化，
# 从而加快启动速度并避免加载未使用的依赖。
_repository: Any | None = None           # 会话数据仓库实例
_share_repository: Any | None = None     # 分享链接仓库实例
_artifact_service: Any | None = None     # 产物（Artifact）服务实例
_session_service: Any | None = None      # 会话服务实例
_chat_service: Any | None = None         # 聊天服务实例
_city_service: Any | None = None         # 城市服务实例
_map_service: Any | None = None          # 地图服务实例
_share_service: Any | None = None        # 分享服务实例
# 持久化签名：记录当前数据库配置的元组，用于检测配置是否变更
# 例如：(db_backend, postgres_dsn, pool_min, pool_max)
_persistence_signature: tuple[Any, ...] | None = None


def _session_file_path() -> str:
    """返回基于文件的会话快照存储路径。

    当数据库后端为文件模式（非 postgres）时，会话数据序列化到此 JSON 文件中。
    典型路径：<项目根>/data/sessions/sessions.json
    """

    return os.path.join(str(PROJECT_ROOT), "data", "sessions", "sessions.json")


def _share_links_file_path() -> str:
    """返回基于文件的分享链接快照存储路径。

    当数据库后端为文件模式时，分享链接数据序列化到此 JSON 文件中。
    典型路径：<项目根>/data/share_links.json
    """

    return os.path.join(str(PROJECT_ROOT), "data", "share_links.json")


def _reset_persistence_singletons() -> None:
    """重置所有依赖持久化层的单例实例。

    应用场景：当数据库配置（如从文件模式切换到 PostgreSQL）发生变更时，
    已有的单例实例绑定了旧的数据库连接，必须全部清除并重新创建。
    例如：运维人员修改了 config.yaml 中的 database.backend 字段后，
    调用此函数可确保后续请求使用新的数据库连接。
    """

    global _repository, _share_repository
    global _artifact_service, _session_service, _chat_service, _share_service
    _repository = None
    _share_repository = None
    _artifact_service = None
    _session_service = None
    _chat_service = None
    _share_service = None


def _ensure_persistence_signature() -> Any:
    """【核心】检查数据库配置是否变更，若变更则重置所有持久化单例。

    实现原理：将当前数据库配置（后端类型、连接串、连接池参数）打包为一个元组（签名），
    与上次记录的签名对比。如果不同，说明配置已变更，需要清除旧实例。

    应用场景：开发环境中热修改配置文件后，无需重启服务即可切换数据库后端。
    例如：从 SQLite 文件模式切换到 PostgreSQL，签名从 ("file", None, 0, 0)
    变为 ("postgres", "postgresql://...", 2, 10)，触发单例重置。
    """

    global _persistence_signature
    server_config = get_server_config()
    # 将数据库关键配置组合为元组，作为"签名"用于变更检测
    signature = (
        server_config.db_backend,
        server_config.postgres_dsn,
        server_config.db_pool_min,
        server_config.db_pool_max,
    )
    if _persistence_signature != signature:
        _reset_persistence_singletons()
        _persistence_signature = signature
    return server_config


def provide_session_repository():
    """【核心】创建或复用会话数据仓库单例。

    根据配置的数据库后端类型，选择不同的仓库实现：
    - postgres：使用 PostgresSessionRepository，数据存储在 PostgreSQL 数据库
    - 其他（默认）：使用 FileSessionRepository，数据存储在本地 JSON 文件

    应用场景：用户创建新会话、查询历史会话列表时，路由层通过容器获取此仓库来读写数据。
    """
    _ensure_persistence_signature()
    global _repository
    if _repository is None:
        server_config = get_server_config()
        if server_config.db_backend == "postgres":
            from .repositories.session_repository_postgres import PostgresSessionRepository

            if not server_config.postgres_dsn:
                raise ValueError("database.backend=postgres requires database.postgres_dsn")
            _repository = PostgresSessionRepository(
                server_config.postgres_dsn,
                pool_min=server_config.db_pool_min,
                pool_max=server_config.db_pool_max,
            )
        else:
            from .repositories.file_session_repository import FileSessionRepository

            _repository = FileSessionRepository(_session_file_path())
    return _repository


def provide_share_repository():
    """创建或复用分享链接仓库单例。

    与 provide_session_repository 类似，根据数据库后端类型选择实现：
    - postgres：PostgresShareLinkRepository
    - 其他：FileShareLinkRepository

    应用场景：用户生成旅行方案分享链接、通过分享链接查看方案时使用。
    """

    _ensure_persistence_signature()
    global _share_repository
    if _share_repository is None:
        server_config = get_server_config()
        if server_config.db_backend == "postgres":
            from .repositories.postgres_share_link_repository import PostgresShareLinkRepository

            if not server_config.postgres_dsn:
                raise ValueError("database.backend=postgres requires database.postgres_dsn")
            _share_repository = PostgresShareLinkRepository(
                server_config.postgres_dsn,
                pool_min=server_config.db_pool_min,
                pool_max=server_config.db_pool_max,
            )
        else:
            from .repositories.file_share_link_repository import FileShareLinkRepository

            _share_repository = FileShareLinkRepository(_share_links_file_path())
    return _share_repository


def provide_session_service():
    """创建或复用会话服务单例。

    SessionService 封装了会话的业务逻辑（创建、查询、删除等），
    内部委托 SessionRepository 进行数据持久化。

    应用场景：用户打开应用时加载会话列表、新建对话、删除历史会话。
    """
    _ensure_persistence_signature()
    global _session_service
    if _session_service is None:
        from .services.session_service import SessionService

        _session_service = SessionService(provide_session_repository())
    return _session_service


def provide_artifact_service():
    """创建或复用产物（Artifact）服务单例。

    ArtifactService 管理旅行方案中的结构化产物（如行程表、酒店推荐列表等），
    同样委托 SessionRepository 进行持久化。

    应用场景：AI 生成旅行方案后，将行程、酒店等结构化数据保存为 Artifact，
    用户可在会话详情页查看和导出。
    """
    _ensure_persistence_signature()
    global _artifact_service
    if _artifact_service is None:
        from .services.artifact_service import ArtifactService

        _artifact_service = ArtifactService(provide_session_repository())
    return _artifact_service


def provide_chat_service():
    """创建或复用聊天服务单例。

    ChatService 负责处理用户与 AI 之间的对话交互，
    包括消息的发送、接收和流式响应等。

    应用场景：用户在聊天界面输入旅行需求，ChatService 协调 LLM 调用
    并将 AI 回复流式返回给前端。
    """
    _ensure_persistence_signature()
    global _chat_service
    if _chat_service is None:
        from .services.chat_service import ChatService

        _chat_service = ChatService(provide_session_repository())
    return _chat_service


def provide_city_service():
    """创建或复用城市服务单例。

    CityService 提供城市信息的查询功能（如城市列表、城市详情等），
    不依赖数据库持久化，因此无需检查持久化签名。

    应用场景：用户搜索目的地城市、前端展示热门城市推荐列表。
    """
    global _city_service
    if _city_service is None:
        from .services.city_service import CityService

        _city_service = CityService()
    return _city_service


def provide_map_service():
    """创建或复用地图服务单例。

    MapService 封装地图相关功能（如地理编码、路径规划等），
    不依赖数据库持久化。

    应用场景：在旅行方案中展示景点之间的路线地图、计算两地距离。
    """
    global _map_service
    if _map_service is None:
        from .services.map_service import MapService

        _map_service = MapService()
    return _map_service


def provide_share_service():
    """创建或复用分享服务单例。

    ShareService 负责管理旅行方案的分享功能，
    如生成分享链接、验证分享链接有效性等。

    应用场景：用户点击"分享"按钮后，系统生成一个可公开访问的链接，
    其他人通过该链接可查看旅行方案详情。
    """
    _ensure_persistence_signature()
    global _share_service
    if _share_service is None:
        from .services.share_service import ShareService

        _share_service = ShareService(repository=provide_share_repository())
    return _share_service


def provide_travel_agent():
    """【核心】构建旅行 Agent 实例，整合 LLM 和旅行工具。

    构建流程：
    1. 从 YAML 配置文件加载 LLM 适配器（支持 OpenAI、通义千问等）
    2. 获取旅行相关工具集（景点搜索、酒店查询、天气查询等）
    3. 通过 build_travel_agent 将 LLM 和工具组装为可执行的 Agent 图

    应用场景：用户发送旅行需求消息时，ChatService 调用此 Agent
    进行多步推理和工具调用，最终生成完整的旅行方案。
    注意：每次调用都创建新实例，因为 Agent 是有状态的对话图。
    """
    from .config.runtime import get_llm_config_path
    from agent.travel_agent.graph.builder import build_travel_agent
    from agent.travel_agent.llm.langchain_adapter import create_from_yaml_config
    from agent.travel_agent.tools.travel_tools import get_travel_tools

    config_path = get_llm_config_path()
    llm_adapter = create_from_yaml_config(config_path)  # 从 YAML 配置创建 LLM 适配器
    llm = llm_adapter.chat_model  # 获取 LangChain ChatModel 实例
    tools = get_travel_tools()  # 获取旅行工具列表
    return build_travel_agent(llm, tools)  # 构建 Agent 执行图


def register_default_services(container: "Container") -> None:
    """【核心】将所有默认服务提供者注册到依赖注入容器。

    注册后，其他模块可通过 container.resolve("服务名") 获取服务实例。
    例如：container.resolve("ChatService") 返回 ChatService 单例。

    注册的服务列表：
    - SessionRepository / ShareLinkRepository：数据持久化仓库
    - ArtifactService / SessionService / ChatService：业务服务
    - CityService / MapService / ShareService：领域服务
    - TravelAgent：旅行 Agent（非单例，每次 resolve 创建新实例）
    """
    container.register("SessionRepository", provide_session_repository)
    container.register("ShareLinkRepository", provide_share_repository)
    container.register("ArtifactService", provide_artifact_service)
    container.register("SessionService", provide_session_service)
    container.register("ChatService", provide_chat_service)
    container.register("CityService", provide_city_service)
    container.register("MapService", provide_map_service)
    container.register("ShareService", provide_share_service)
    container.register("TravelAgent", provide_travel_agent)
