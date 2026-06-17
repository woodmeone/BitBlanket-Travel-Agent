"""
SQLAlchemy 引擎构建模块 —— 数据库后端的连接管理

【基础知识】
- SQLAlchemy Engine：SQLAlchemy 的核心对象，管理数据库连接池和 SQL 方言。
  通过 create_engine() 创建，支持 SQLite、PostgreSQL 等多种数据库。

- 连接池（Connection Pool）：预先创建一组数据库连接复用，避免频繁建连的开销。
  - pool_size：常驻连接数
  - max_overflow：超出 pool_size 后允许的额外连接数
  - pool_pre_ping：每次从池中取连接时先发 ping 检测，自动回收断开的连接

- SQLite 特殊处理：
  - check_same_thread=False：SQLite 默认只允许创建线程使用连接，此选项允许多线程共享
  - StaticPool：内存数据库（:memory:）使用静态池，确保所有请求共享同一个连接
"""

from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.pool import StaticPool

from .sql_tables import metadata


def normalize_database_url(database_url: str) -> str:
    """将配置的数据库 URL 标准化为 SQLAlchemy 驱动格式。

    例：postgresql://user:pass@host/db → postgresql+psycopg://user:pass@host/db
    psycopg 是 PostgreSQL 的新版 Python 驱动，SQLAlchemy 2.0+ 需要显式指定。
    """

    normalized = str(database_url or "").strip()
    if normalized.startswith("postgresql://"):
        return normalized.replace("postgresql://", "postgresql+psycopg://", 1)
    return normalized


def build_sync_engine(database_url: str, *, pool_min: int = 1, pool_max: int = 5) -> Engine:
    """【核心】创建同步 SQLAlchemy 引擎，供仓库适配器和脚本使用。

    根据数据库类型自动配置连接池参数：
    - SQLite：禁用同线程检查，内存数据库使用 StaticPool
    - PostgreSQL/MySQL：启用 pool_pre_ping，配置连接池大小
    """

    normalized = normalize_database_url(database_url)
    if not normalized:
        raise ValueError("database_url is required")

    engine_kwargs: dict[str, object] = {"future": True}  # 启用 SQLAlchemy 2.0 风格
    if normalized.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}  # SQLite 多线程共享连接
        if ":memory:" in normalized:
            engine_kwargs["poolclass"] = StaticPool  # 内存数据库使用静态池，共享单一连接
    else:
        engine_kwargs["pool_pre_ping"] = True  # 每次取连接前检测存活，自动回收断连
        engine_kwargs["pool_size"] = max(1, int(pool_min))  # 常驻连接数
        engine_kwargs["max_overflow"] = max(0, int(pool_max) - int(pool_min))  # 额外溢出连接数

    return create_engine(normalized, **engine_kwargs)


def ensure_schema(engine: Engine) -> None:
    """创建基线表（如果尚不存在）。

    使用 metadata.create_all() 根据 sql_tables.py 中定义的表结构自动建表，
    已存在的表不会被修改（非 ALTER 语义）。
    """

    metadata.create_all(engine)
