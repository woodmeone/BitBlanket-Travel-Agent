"""
================================================================================
日志配置模块
================================================================================

提供统一的日志配置，支持：
- 控制台输出
- 文件输出
- 按模块分级
- 轮转日志

使用示例:
```python
from config.logging import setup_logging, get_logger

# 初始化日志
setup_logging()

# 获取日志器
logger = get_logger(__name__)
logger.info("信息日志")
logger.warning("警告日志")
logger.error("错误日志")
```

================================================================================
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


# 日志目录
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# 日志级别配置
LOG_LEVELS = {
    "uvicorn": logging.INFO,
    "uvicorn.access": logging.WARNING,
    "fastapi": logging.INFO,
    "agent": logging.INFO,
    "web": logging.INFO,
    "root": logging.INFO,
}

# 模块日志级别
MODULE_LOG_LEVELS = {
    "routes": logging.DEBUG,
    "services": logging.DEBUG,
    "repositories": logging.DEBUG,
    "storage": logging.DEBUG,
    "dependencies": logging.DEBUG,
    "llm": logging.DEBUG,
    "tools": logging.DEBUG,
    "graph": logging.DEBUG,
}


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""

    COLORS = {
        "DEBUG": "\033[36m",     # 青色
        "INFO": "\033[32m",      # 绿色
        "WARNING": "\033[33m",   # 黄色
        "ERROR": "\033[31m",     # 红色
        "CRITICAL": "\033[35m",  # 紫色
        "RESET": "\033[0m",
    }

    def format(self, record: logging.LogRecord) -> str:
        # 添加颜色
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
            )
        return super().format(record)


def get_log_filename(prefix: str = "app") -> str:
    """获取日志文件名（按日期）"""
    return f"{prefix}_{datetime.now().strftime('%Y%m%d')}.log"


def setup_logging(
    level: int = logging.INFO,
    log_to_file: bool = True,
    log_to_console: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> None:
    """
    设置日志配置

    Args:
        level: 默认日志级别
        log_to_file: 是否输出到文件
        log_to_console: 是否输出到控制台
        max_bytes: 单个日志文件最大字节数
        backup_count: 保留的日志文件数量
    """
    # 根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 清除现有处理器
    root_logger.handlers.clear()

    # 日志格式
    detailed_format = (
        "[%(asctime)s.%(msecs)03d] "
        "%(levelname)-8s | "
        "%(name)-30s | "
        "%(funcName)s:%(lineno)d | "
        "%(message)s"
    )
    simple_format = (
        "[%(asctime)s] %(levelname)-8s | %(name)s | %(message)s"
    )

    # 控制台处理器
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_formatter = ColoredFormatter(
            detailed_format,
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # 文件处理器
    if log_to_file:
        # 应用日志
        app_log_file = LOG_DIR / get_log_filename("app")
        app_handler = logging.handlers.RotatingFileHandler(
            app_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        app_handler.setLevel(logging.DEBUG)
        app_formatter = logging.Formatter(detailed_format, datefmt="%Y-%m-%d %H:%M:%S")
        app_handler.setFormatter(app_formatter)
        root_logger.addHandler(app_handler)

        # 错误日志
        error_log_file = LOG_DIR / get_log_filename("error")
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(app_formatter)
        root_logger.addHandler(error_handler)

        # 访问日志
        access_log_file = LOG_DIR / get_log_filename("access")
        access_handler = logging.handlers.RotatingFileHandler(
            access_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        access_handler.setLevel(logging.INFO)
        access_formatter = logging.Formatter(simple_format, datefmt="%Y-%m-%d %H:%M:%S")
        access_handler.setFormatter(access_formatter)

        # uvice 访问日志器
        access_logger = logging.getLogger("uvicorn.access")
        access_logger.handlers.clear()
        access_logger.addHandler(access_handler)
        access_logger.setLevel(logging.INFO)
        access_logger.propagate = False

    # 设置模块日志级别
    for module, module_level in MODULE_LOG_LEVELS.items():
        logger = logging.getLogger(module)
        logger.setLevel(module_level)

    # 设置第三方库日志级别
    for lib, lib_level in LOG_LEVELS.items():
        logger = logging.getLogger(lib)
        logger.setLevel(lib_level)


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    获取日志器

    Args:
        name: 日志器名称（通常使用 __name__）
        level: 可选的日志级别

    Returns:
        配置好的日志器
    """
    logger = logging.getLogger(name)
    if level is not None:
        logger.setLevel(level)
    return logger


def set_module_level(module: str, level: int) -> None:
    """设置模块日志级别"""
    logger = logging.getLogger(module)
    logger.setLevel(level)


# 便捷函数
debug = lambda msg, *args, **kwargs: logging.debug(msg, *args, **kwargs)
info = lambda msg, *args, **kwargs: logging.info(msg, *args, **kwargs)
warning = lambda msg, *args, **kwargs: logging.warning(msg, *args, **kwargs)
error = lambda msg, *args, **kwargs: logging.error(msg, *args, **kwargs)
critical = lambda msg, *args, **kwargs: logging.critical(msg, *args, **kwargs)


__all__ = [
    "setup_logging",
    "get_logger",
    "set_module_level",
    "LOG_DIR",
    "debug",
    "info",
    "warning",
    "error",
    "critical",
]
