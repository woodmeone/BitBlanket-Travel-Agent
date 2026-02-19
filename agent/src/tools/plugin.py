"""
插件系统

提供插件化工具扩展机制，支持动态加载/卸载、钩子管理和配置管理。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import importlib.util
import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class PluginState(Enum):
    """插件状态"""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class PluginMetadata:
    """插件元数据"""
    plugin_id: str
    name: str
    version: str
    author: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    entry_point: str = "main"
    config_schema: Dict = field(default_factory=dict)


@dataclass
class Plugin:
    """插件实例"""
    metadata: PluginMetadata
    state: PluginState
    module: Any = None
    config: Dict = field(default_factory=dict)
    error: Optional[str] = None


class PluginManager:
    """插件管理器

    特性：
    - 插件加载/卸载
    - 依赖管理
    - 配置管理
    - 热重载
    """

    def __init__(self, plugin_dir: str = "plugins"):
        self._plugins: Dict[str, Plugin] = {}
        self._plugin_dir = Path(plugin_dir)
        self._hooks: Dict[str, List[Callable]] = {
            "before_tool_call": [],
            "after_tool_call": [],
            "on_error": [],
            "on_load": [],
            "on_unload": []
        }
        logger.info(f"PluginManager initialized with dir: {plugin_dir}")

    def load_plugin(self, plugin_path: str) -> Plugin:
        """加载插件

        Args:
            plugin_path: 插件路径 (.py 文件或目录)

        Returns:
            插件实例
        """
        path = Path(plugin_path)

        if not path.exists():
            raise FileNotFoundError(f"Plugin not found: {plugin_path}")

        # 加载模块
        spec = importlib.util.spec_from_file_location(
            path.stem, path
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[path.stem] = module

        try:
            spec.loader.exec_module(module)
        except Exception as e:
            logger.error(f"Failed to load plugin from {plugin_path}: {e}")
            raise

        # 获取插件类
        plugin_class = getattr(module, "Plugin", None)
        if not plugin_class:
            raise ValueError(f"Plugin class not found in {plugin_path}")

        # 实例化
        plugin_instance = plugin_class()
        plugin_id = getattr(plugin_instance, "plugin_id", path.stem)

        # 检查是否已加载
        if plugin_id in self._plugins:
            logger.warning(f"Plugin {plugin_id} already loaded, skipping")
            return self._plugins[plugin_id]

        metadata = PluginMetadata(
            plugin_id=plugin_id,
            name=getattr(plugin_instance, "name", path.stem),
            version=getattr(plugin_instance, "version", "1.0.0"),
            author=getattr(plugin_instance, "author", ""),
            description=getattr(plugin_instance, "description", "")
        )

        plugin = Plugin(
            metadata=metadata,
            state=PluginState.LOADED,
            module=plugin_instance
        )

        self._plugins[plugin_id] = plugin

        # 执行加载钩子
        self._execute_hooks("on_load", plugin_id)

        logger.info(f"Loaded plugin: {plugin_id}")
        return plugin

    def unload_plugin(self, plugin_id: str) -> bool:
        """卸载插件

        Args:
            plugin_id: 插件ID

        Returns:
            是否成功
        """
        if plugin_id not in self._plugins:
            return False

        plugin = self._plugins[plugin_id]

        # 调用插件的 unload 方法
        if hasattr(plugin.module, "unload"):
            try:
                plugin.module.unload()
            except Exception as e:
                logger.warning(f"Error calling unload on plugin {plugin_id}: {e}")

        # 执行卸载钩子
        self._execute_hooks("on_unload", plugin_id)

        # 移除
        del self._plugins[plugin_id]

        logger.info(f"Unloaded plugin: {plugin_id}")
        return True

    def reload_plugin(self, plugin_id: str) -> Plugin:
        """重新加载插件

        Args:
            plugin_id: 插件ID

        Returns:
            重新加载的插件实例
        """
        if plugin_id not in self._plugins:
            raise ValueError(f"Plugin {plugin_id} not loaded")

        plugin = self._plugins[plugin_id]
        # 获取原始路径（简化处理）
        path = Path(plugin.module.__file__)

        # 卸载
        self.unload_plugin(plugin_id)

        # 重新加载
        return self.load_plugin(str(path))

    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """获取插件

        Args:
            plugin_id: 插件ID

        Returns:
            插件实例或 None
        """
        return self._plugins.get(plugin_id)

    def list_plugins(
        self,
        state: Optional[PluginState] = None
    ) -> List[Plugin]:
        """列出插件

        Args:
            state: 状态过滤

        Returns:
            插件列表
        """
        if state:
            return [p for p in self._plugins.values() if p.state == state]
        return list(self._plugins.values())

    def register_hook(self, hook_name: str, callback: Callable):
        """注册钩子

        Args:
            hook_name: 钩子名称
            callback: 回调函数
        """
        if hook_name not in self._hooks:
            raise ValueError(f"Unknown hook: {hook_name}")

        self._hooks[hook_name].append(callback)
        logger.info(f"Registered hook: {hook_name}")

    def unregister_hook(self, hook_name: str, callback: Callable) -> bool:
        """注销钩子

        Args:
            hook_name: 钩子名称
            callback: 回调函数

        Returns:
            是否成功
        """
        if hook_name not in self._hooks:
            return False

        try:
            self._hooks[hook_name].remove(callback)
            return True
        except ValueError:
            return False

    def execute_hook(self, hook_name: str, *args, **kwargs):
        """执行钩子

        Args:
            hook_name: 钩子名称
            *args: 位置参数
            **kwargs: 关键字参数
        """
        if hook_name in self._hooks:
            for callback in self._hooks[hook_name]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Hook {hook_name} error: {e}")

    def _execute_hooks(self, hook_name: str, *args, **kwargs):
        """执行钩子 (内部)

        Args:
            hook_name: 钩子名称
            *args: 位置参数
            **kwargs: 关键字参数
        """
        self.execute_hook(hook_name, *args, **kwargs)

    def get_plugin_config(self, plugin_id: str) -> Optional[Dict]:
        """获取插件配置

        Args:
            plugin_id: 插件ID

        Returns:
            配置字典或 None
        """
        plugin = self._plugins.get(plugin_id)
        return plugin.config if plugin else None

    def set_plugin_config(self, plugin_id: str, config: Dict) -> bool:
        """设置插件配置

        Args:
            plugin_id: 插件ID
            config: 配置字典

        Returns:
            是否成功
        """
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False

        plugin.config = config
        logger.info(f"Updated config for plugin: {plugin_id}")
        return True


# 全局单例
plugin_manager = PluginManager()
