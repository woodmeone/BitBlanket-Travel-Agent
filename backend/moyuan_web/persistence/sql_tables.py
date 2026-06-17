"""
SQLAlchemy 表定义模块 —— 兼容性优先的数据库基线表结构

【基础知识】
- SQLAlchemy Core Table：使用声明式表定义（非 ORM），直接映射数据库表结构。
  与 ORM 模型不同，Table 对象更轻量，适合简单查询和批量操作。

- JSON 类型适配：
  - SQLite/MySQL：使用通用 JSON 类型
  - PostgreSQL：使用 JSONB 类型（二进制存储，支持索引和高效查询）
  json_type 变量通过 with_variant 自动根据数据库方言选择合适类型。

- 本模块定义了 4 张表：
  1. sessions —— 会话主表
  2. session_messages —— 会话消息表（一对多）
  3. share_links —— 分享链接表
  4. memory_sessions —— 记忆会话表
"""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Index, Integer, MetaData, String, Table, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON


metadata = MetaData()
json_type = JSON().with_variant(JSONB(astext_type=Text()), "postgresql")  # PostgreSQL 用 JSONB，其他用 JSON

# ---- 会话主表 ----
# 存储每个会话的基本信息和消息列表
sessions_table = Table(
    "sessions",
    metadata,
    Column("session_id", String(128), primary_key=True),  # 会话ID，主键
    Column("created_at", String(64), nullable=False),  # 创建时间（ISO格式字符串）
    Column("last_active", String(64), nullable=False),  # 最后活跃时间
    Column("message_count", Integer, nullable=False, default=0),  # 消息计数
    Column("name", String(120), nullable=False),  # 会话名称
    Column("model_id", String(128), nullable=False),  # 使用的模型ID
    Column("messages", json_type, nullable=False),  # 消息列表（JSON数组）
    Column("user_preferences", json_type, nullable=False),  # 用户偏好（JSON对象）
)

Index("ix_sessions_last_active", sessions_table.c.last_active)  # 按最后活跃时间查询的索引

# ---- 会话消息表 ----
# 存储每条消息的详细内容，与 sessions 表一对多关系
session_messages_table = Table(
    "session_messages",
    metadata,
    Column("message_id", Integer, primary_key=True, autoincrement=True),  # 消息ID，自增主键
    Column("session_id", String(128), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False),  # 外键关联会话，级联删除
    Column("sequence", Integer, nullable=False),  # 消息序号（会话内递增）
    Column("role", String(32), nullable=False),  # 角色：user / assistant / system
    Column("content", Text, nullable=False),  # 消息正文
    Column("reasoning", Text, nullable=True),  # 推理过程（仅 assistant 消息）
    Column("model_content", Text, nullable=True),  # 模型原始输出
    Column("diagnostics", json_type, nullable=True),  # 诊断信息（JSON对象）
    Column("timestamp", String(64), nullable=False),  # 消息时间戳
)

Index(
    "ix_session_messages_session_sequence",
    session_messages_table.c.session_id,
    session_messages_table.c.sequence,
    unique=True,  # 唯一索引：同一会话内消息序号不重复
)

# ---- 分享链接表 ----
# 存储会话分享链接的内容
share_links_table = Table(
    "share_links",
    metadata,
    Column("share_id", String(32), primary_key=True),  # 分享ID，主键（10位十六进制）
    Column("title", String(100), nullable=False, default=""),  # 分享标题
    Column("content", Text, nullable=False),  # 分享内容（纯文本）
    Column("html_content", Text, nullable=False, default=""),  # 分享内容（HTML格式）
    Column("delivery_bundle", json_type, nullable=True),  # 完整交付包（JSON对象）
    Column("created_at", String(64), nullable=False),  # 创建时间
)

Index("ix_share_links_created_at", share_links_table.c.created_at)  # 按创建时间查询的索引

# ---- 记忆会话表 ----
# 存储会话的记忆摘要和用户画像，用于跨会话的个性化体验
memory_sessions_table = Table(
    "memory_sessions",
    metadata,
    Column("session_id", String(128), primary_key=True),  # 会话ID，主键
    Column("summary", Text, nullable=False),  # 会话摘要
    Column("profile", json_type, nullable=False),  # 用户画像（JSON对象，如偏好、习惯）
    Column("messages", json_type, nullable=False),  # 记忆消息列表（JSON数组）
    Column("updated_at", String(64), nullable=False),  # 更新时间
)

Index("ix_memory_sessions_updated_at", memory_sessions_table.c.updated_at)  # 按更新时间查询的索引
