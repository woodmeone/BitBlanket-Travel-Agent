"""
简单依赖注入容器及默认容器引导入口。

本模块实现了 IoC（控制反转）容器的核心逻辑，提供服务注册与解析能力，
并提供全局共享容器的获取与重置机制。

【基础知识：IoC 容器（Inversion of Control Container）】
IoC 容器是依赖注入的载体，负责两件事：
1. 注册（register）：将"服务名"与"创建函数"绑定
2. 解析（resolve）：根据"服务名"调用创建函数，返回服务实例

与手动 new 对象相比，IoC 容器的优势：
- 集中管理：所有依赖在一处注册，方便查看和替换
- 生命周期控制：自动实现单例（singleton）或多例（transient）
- 解耦：使用方只依赖接口名，不依赖具体实现类

【基础知识：服务定位器模式（Service Locator）】
本模块的 get_container() + container.resolve() 组合即为服务定位器模式：
通过全局入口获取容器，再通过名称解析服务。
与纯依赖注入的区别：服务定位器是"主动拉取"，依赖注入是"被动推送"。
在 FastAPI 中，通常通过 Depends() 机制将两者结合使用。
"""

from __future__ import annotations

from typing import Any, Callable


class Container:
    """依赖注入容器，通过名称注册和解析服务实例。

    支持两种生命周期：
    - 单例（singleton=True，默认）：首次 resolve 时创建实例并缓存，后续返回同一实例
    - 多例（singleton=False）：每次 resolve 都调用 provider 创建新实例
    """

    def __init__(self) -> None:
        """初始化提供者注册表和单例实例缓存。

        _providers: 服务名 → (创建函数, 是否单例) 的映射
        _instances: 服务名 → 已创建的单例实例 的缓存
        """
        self._providers: dict[str, tuple[Callable[[], Any], bool]] = {}
        self._instances: dict[str, Any] = {}

    def register(self, name: str, provider: Callable[[], Any], singleton: bool = True) -> None:
        """注册一个服务提供者。

        Args:
            name: 服务名称，后续通过此名称 resolve。例如 "ChatService"
            provider: 无参可调用对象，调用时返回服务实例。例如 provide_chat_service
            singleton: 是否为单例模式。True 表示全局只创建一次，False 表示每次都新建
        """
        self._providers[name] = (provider, singleton)

    def has_provider(self, name: str) -> bool:
        """检查容器中是否注册了指定名称的服务。"""
        return name in self._providers

    def resolve(self, name: str) -> Any:
        """【核心】根据服务名称解析并返回服务实例。

        解析逻辑：
        1. 查找注册表，未找到则抛出 ValueError
        2. 若为单例且已有缓存实例，直接返回
        3. 调用 provider() 创建新实例
        4. 若为单例，将实例存入缓存

        Args:
            name: 服务名称，如 "SessionService"、"TravelAgent"

        Raises:
            ValueError: 服务名称未注册时抛出

        应用场景：FastAPI 路由通过 Depends(get_xxx_service) 间接调用此方法，
        获取所需的服务实例来处理请求。
        """
        if name not in self._providers:
            raise ValueError(f"Dependency not found: {name}")

        provider, singleton = self._providers[name]
        # 单例模式：优先从缓存返回已有实例
        if singleton and name in self._instances:
            return self._instances[name]

        # 调用 provider 创建新实例
        instance = provider()
        # 单例模式：缓存实例供后续复用
        if singleton:
            self._instances[name] = instance
        return instance


# ── 全局共享容器 ──────────────────────────────────────────────
# 使用模块级变量实现全局唯一的默认容器，配合签名检测实现配置热更新。
_container: Container | None = None
# 容器签名：与 bootstrap_services 中的 _persistence_signature 类似，
# 用于检测数据库配置是否变更，变更时需重建容器
_container_signature: tuple[Any, ...] | None = None


def _current_container_signature() -> tuple[Any, ...] | None:
    """获取当前持久化相关配置的签名，用于判断是否需要重建容器。

    签名由数据库后端类型、连接串、连接池参数组成。
    当配置变更时（如从文件模式切换到 PostgreSQL），签名改变，
    get_container() 会重建整个容器，确保所有服务使用新配置。

    Returns:
        配置签名的元组，获取失败时返回 None
    """

    try:
        from ..config.runtime import get_server_config

        server_config = get_server_config()
        return (
            server_config.db_backend,
            server_config.postgres_dsn,
            server_config.db_pool_min,
            server_config.db_pool_max,
        )
    except Exception:
        return None


def build_default_container() -> Container:
    """构建预装了所有默认服务的依赖容器。

    创建空的 Container 实例后，调用 register_default_services()
    将所有服务提供者注册进去。

    Returns:
        已注册所有默认服务的 Container 实例
    """
    from ..bootstrap_services import register_default_services

    container = Container()
    register_default_services(container)
    return container


def get_container() -> Container:
    """【核心】获取全局共享的默认依赖容器。

    首次调用时创建容器并注册所有服务，后续调用直接返回已有实例。
    当数据库配置发生变更时（签名不同），自动重建容器。

    应用场景：FastAPI 的 Depends() 依赖注入函数内部调用此方法，
    获取容器后 resolve 出所需服务。例如：
        def get_chat_service():
            return get_container().resolve("ChatService")
    """
    global _container, _container_signature
    signature = _current_container_signature()
    # 容器不存在或配置已变更 → 重建容器
    if _container is None or _container_signature != signature:
        _container = build_default_container()
        _container_signature = signature
    return _container


def reset_container() -> None:
    """重置全局共享容器，用于测试和配置热重载场景。

    应用场景：
    1. 单元测试中，每个测试用例前调用此函数，确保测试间互不影响
    2. 运维修改数据库配置后，调用此函数强制重建容器
    """

    global _container, _container_signature
    _container = None
    _container_signature = None
