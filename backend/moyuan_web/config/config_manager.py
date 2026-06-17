"""
配置管理器模块 —— 负责加载和管理 LLM 及应用运行时配置。

基础知识：
- YAML 配置：一种以缩进表示层级关系的配置文件格式，常用于应用配置。
  本项目使用 llm_config.yaml 存放模型、Agent、Web 服务等所有运行时参数。
- 环境变量替换：YAML 文件中可使用 ${ENV_VAR} 占位符，运行时自动替换为
  操作系统环境变量的值。例如 api_key: ${OPENAI_API_KEY} 会在启动时
  被替换为实际的 API 密钥，避免将敏感信息硬编码在配置文件中。
- 单例模式：通过模块级变量 _config_manager 实现进程内全局唯一实例，
  避免重复加载配置文件。
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

import yaml

from ..bootstrap import PROJECT_ROOT, ensure_project_paths

ensure_project_paths()


class ConfigManager:
    """
    配置管理器 —— 加载 YAML/JSON 配置文件并提供模型、城市知识等查询接口。

    典型应用场景：
    - 启动时加载 llm_config.yaml，解析出可用模型列表
    - 根据用户选择的模型 ID 获取对应的 API 密钥和参数
    - 查询旅游知识库中某城市的详细信息
    """

    def __init__(self, config_path: str = "backend/config/llm_config.yaml"):
        """
        初始化配置管理器。

        Args:
            config_path: 配置文件路径，支持绝对路径或相对于项目根目录的相对路径。
                         默认为 backend/config/llm_config.yaml。
        """

        self.config_path = self._resolve_config_path(config_path)
        self.config: Dict[str, Any] = {}  # 完整的配置字典（解析后的原始数据）
        self.models_config: Dict[str, Dict[str, Any]] = {}  # 模型配置字典，key 为模型 ID
        self.default_model_id: str = "gpt-4o-mini"  # 默认模型 ID
        self.travel_knowledge: Dict[str, Any] = {}  # 旅游知识库配置（城市信息等）
        self._load_config()

    @staticmethod
    def _resolve_config_path(config_path: str) -> str:
        """
        解析配置文件路径。

        若传入相对路径，则拼接项目根目录；若已是绝对路径则直接返回。
        例如："backend/config/llm_config.yaml" → "/project/root/backend/config/llm_config.yaml"
        """

        if os.path.isabs(config_path):
            return config_path
        return str(os.path.join(str(PROJECT_ROOT), config_path))

    def _load_config(self) -> None:
        """
        【核心】加载配置文件到内存。

        流程：读取文件 → 替换环境变量占位符 → 按 YAML/JSON 解析 → 提取各子配置。
        """

        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file missing: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            content = f.read()

        content = self._replace_env_vars(content)  # 替换 ${ENV_VAR} 占位符

        if self.config_path.endswith((".yaml", ".yml")):
            self.config = yaml.safe_load(content)  # yaml.safe_load 安全加载，不会执行任意 Python 代码
        else:
            self.config = json.loads(content)

        self.config = self.config or {}
        self.models_config = self.config.get("models", {})  # 提取模型配置块
        self.default_model_id = self.config.get("default_model", "gpt-4o-mini")  # 提取默认模型 ID
        self.travel_knowledge = self.config.get("travel_knowledge", {})  # 提取旅游知识配置块

    @staticmethod
    def _replace_env_vars(content: str) -> str:
        """
        【核心】替换配置文本中的环境变量占位符。

        将 ${ENV_VAR} 形式的占位符替换为对应环境变量的值。
        若环境变量不存在，则保留原始占位符文本不变。

        示例：
          输入："api_key: ${OPENAI_API_KEY}"
          若环境变量 OPENAI_API_KEY=sk-xxx，则输出："api_key: sk-xxx"
          若环境变量不存在，则输出不变："api_key: ${OPENAI_API_KEY}"
        """

        pattern = r"\$\{([^}]+)\}"  # 匹配 ${...} 形式的占位符

        def replace(match):
            """替换单个占位符：从环境变量中取值，找不到则保留原样。"""

            var_name = match.group(1)
            env_value = os.environ.get(var_name, "")
            return env_value if env_value else match.group(0)  # 环境变量不存在时保留占位符

        return re.sub(pattern, replace, content)

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        通过点分键路径获取嵌套配置值。

        Args:
            key: 点分隔的配置键路径，如 "agent.max_turns" 对应 config["agent"]["max_turns"]
            default: 键不存在时的默认返回值

        示例：
          get_config("web.port") → 从 config["web"]["port"] 取值
          get_config("not.exist", 8080) → 键不存在，返回 8080
        """

        keys = key.split(".")
        value: Any = self.config

        for part in keys:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default

        return value

    def get_city_info(self, city_name: str) -> Optional[Dict[str, Any]]:
        """
        从旅游知识库中获取指定城市的信息。

        Args:
            city_name: 城市名称，如 "北京"、"上海"

        Returns:
            城市信息字典，包含景点、美食等数据；不存在则返回 None
        """

        return self.travel_knowledge.get("cities", {}).get(city_name)

    def get_all_cities(self) -> List[str]:
        """获取旅游知识库中所有已配置的城市名称列表。"""

        return list(self.travel_knowledge.get("cities", {}).keys())

    @staticmethod
    def _is_model_active(model_config: Dict[str, Any]) -> bool:
        """
        【核心】判断某个模型配置是否在运行时可用。

        判断逻辑：
        1. api_key 为空 → 不可用（未配置密钥）
        2. api_key 仍是 ${VAR} 占位符且对应环境变量不存在 → 不可用
        3. api_key 包含 "YOUR_" 等占位提示（如 "YOUR_API_KEY"）→ 不可用
        4. 其他情况 → 可用

        应用场景：用户在前端切换模型时，只展示已配置有效密钥的模型。
        """

        api_key = model_config.get("api_key", "")
        if not api_key:
            return False

        if api_key.startswith("${") and api_key.endswith("}"):  # 环境变量占位符未被替换
            var_name = api_key[2:-1]
            return bool(os.environ.get(var_name))  # 检查环境变量是否存在

        if "YOUR_" in api_key.upper():  # 模板占位符，如 "YOUR_API_KEY_HERE"
            return False

        return True

    def get_available_models(self) -> List[Dict[str, Any]]:
        """
        获取所有运行时可用的模型列表（已过滤掉未配置密钥的模型）。

        Returns:
            可用模型列表，每项包含 model_id、name、provider、model 字段。

        应用场景：前端"模型选择"下拉框的数据来源，只展示用户实际可用的模型。
        """

        models: List[Dict[str, Any]] = []
        for model_id, model_config in self.models_config.items():
            if not self._is_model_active(model_config):  # 跳过不可用的模型
                continue

            models.append(
                {
                    "model_id": model_id,
                    "name": model_config.get("name", model_id),
                    "provider": model_config.get("provider", "openai"),
                    "model": model_config.get("model", model_id),
                }
            )
        return models

    def get_model_config(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取指定模型的完整配置，未指定时返回默认模型配置。

        Args:
            model_id: 模型 ID，如 "gpt-4o-mini"。为 None 时使用默认模型。

        Raises:
            ValueError: 指定的模型 ID 在配置中不存在时抛出。
        """

        target = model_id or self.default_model_id
        if target not in self.models_config:
            raise ValueError(f"Model not found: {target}")
        return self.models_config[target]

    def get_default_model_id(self) -> str:
        """获取配置文件中设定的默认模型 ID。"""

        return self.default_model_id

    def get_default_model_config(self) -> Dict[str, Any]:
        """获取默认模型的完整配置。"""

        return self.get_model_config(self.default_model_id)

    @property
    def agent_config(self) -> Dict[str, Any]:
        """获取 agent 配置块（Agent 行为参数，如最大轮次、系统提示词等）。"""

        return self.config.get("agent", {})

    @property
    def web_config(self) -> Dict[str, Any]:
        """获取 web 配置块（Web 服务参数，如端口、CORS 设置等）。"""

        return self.config.get("web", {})

    @property
    def grpc_config(self) -> Dict[str, Any]:
        """获取 grpc 配置块（gRPC 通信参数，如服务地址、超时等）。"""

        return self.config.get("grpc", {})


_config_manager: Optional[ConfigManager] = None  # 进程级单例缓存


def get_config(config_path: str = "backend/config/llm_config.yaml") -> ConfigManager:
    """
    获取进程全局唯一的 ConfigManager 实例（单例模式）。

    首次调用时创建实例并缓存，后续调用直接返回缓存实例。
    这确保整个应用共享同一份配置，避免重复加载文件。

    Args:
        config_path: 配置文件路径，仅在首次创建时使用。
    """

    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_path)
    return _config_manager
