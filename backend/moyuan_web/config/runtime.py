"""
运行时配置访问器模块 —— 为 Web 应用提供统一的配置获取入口。

基础知识：
- lru_cache：Python 标准库提供的最近最少使用缓存装饰器。
  被 @lru_cache 装饰的函数在首次调用后会将返回值缓存，
  后续相同参数的调用直接返回缓存结果，避免重复创建对象。
  maxsize=1 表示只缓存最近一次调用的结果，适用于单例场景。
- 懒加载（Lazy Import）：在函数内部导入模块而非文件顶部，
  用于打破循环依赖。例如本模块的 get_server_config() 在函数内
  才导入 server_config，避免启动时因模块间相互引用导致报错。
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from moyuan_web.bootstrap import PROJECT_ROOT, ensure_project_paths
from moyuan_web.config.config_manager import ConfigManager

ensure_project_paths()


def get_llm_config_path() -> str:
    """
    获取 LLM 配置文件的标准路径。

    Returns:
        项目根目录下 backend/config/llm_config.yaml 的绝对路径字符串。
    """
    return str(Path(PROJECT_ROOT) / "backend" / "config" / "llm_config.yaml")


@lru_cache(maxsize=1)  # 缓存单例，整个进程只创建一次 ConfigManager
def get_model_config_manager() -> ConfigManager:
    """
    创建并缓存模型配置管理器实例，供路由处理函数使用。

    由于使用了 @lru_cache(maxsize=1)，无论调用多少次都返回同一个实例。
    """
    return ConfigManager(get_llm_config_path())


def get_server_config():
    """
    懒加载服务器配置，避免启动阶段的循环导入问题。

    在函数内部才 from config import server_config，
    确保此时所有模块已完成初始化，不会因相互依赖导致 ImportError。
    """
    from config import server_config

    return server_config
