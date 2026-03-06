"""Configuration module for ShuaiTravelAgent."""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

# 配置文件路径
SERVER_CONFIG_PATH = PROJECT_ROOT / "config" / "server_config.yaml"


class ServerConfig:
    """Server configuration loader.

    Reads from config/server_config.yaml and provides typed access.
    """

    _instance: Optional["ServerConfig"] = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        """Load configuration from YAML file."""
        if SERVER_CONFIG_PATH.exists():
            with open(SERVER_CONFIG_PATH, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
        else:
            self._config = {}

    def reload(self):
        """Reload configuration from file."""
        self._load()

    @property
    def web_host(self) -> str:
        return self._config.get("web", {}).get("host", "0.0.0.0")

    @property
    def web_port(self) -> int:
        return self._config.get("web", {}).get("port", 38000)

    @property
    def web_debug(self) -> bool:
        return self._config.get("web", {}).get("debug", True)

    @property
    def cors_origins(self) -> list:
        return self._config.get("web", {}).get("cors_origins", [])

    @property
    def frontend_port(self) -> int:
        return self._config.get("frontend", {}).get("port", 33001)

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value by dot-notation key, e.g. 'grpc.port'."""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value


# Singleton instance
server_config = ServerConfig()
