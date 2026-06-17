"""记忆持久化 —— 保存和恢复对话历史的磁盘存储层。

本模块负责将Agent的会话记忆（用户偏好、对话历史等）持久化到磁盘，
确保Agent重启后能恢复之前的对话上下文，实现"记住用户"的能力。

核心设计：
  - 主备双写（Primary + Hot-Backup）：同时写入主文件和备份文件，防止写入中断导致数据丢失
  - 尽力而为（Best-effort）：持久化失败不阻塞主流程，仅记录日志
  - 原子写入（Atomic Write）：先写临时文件再重命名，避免写入过程中崩溃导致文件损坏

典型场景（以"成都3日游"为例）：
  1. 用户第一次说"我想去成都玩3天"，Agent将偏好保存到磁盘
  2. 用户关闭对话后再次回来，Agent从磁盘恢复记忆
  3. Agent记住用户之前想去成都，主动询问"还想继续规划成都之旅吗？"

架构说明：
  MemoryPersistenceStore 是对外的高层接口，内部委托给 MemorySessionRepository 实现。
  当前默认使用 FileMemorySessionRepository（文件存储），可替换为其他存储实现。
"""

from __future__ import annotations

from typing import Any, Optional

from .file_memory_session_repository import FileMemorySessionRepository  # 文件存储实现
from .memory_session_repository import MemorySessionRepository           # 存储抽象接口


class MemoryPersistenceStore:
    """【核心】尽力而为的持久化存储，支持主备恢复和原子写入。

    职责：
      - 保存会话快照到磁盘（主文件 + 备份文件）
      - 加载最新的可用快照（主文件优先，备份文件兜底）
      - 从备份恢复主文件

    设计原则：
      - 持久化失败不应阻塞Agent主流程
      - 主文件损坏时可从备份文件恢复
      - 写入操作使用原子写入（先写临时文件再重命名）
    """

    def __init__(
        self,
        persist_path: Optional[str],
        *,
        backup_suffix: str = ".bak",
        repository: MemorySessionRepository | None = None,
    ) -> None:
        """创建持久化存储实例。

        若提供自定义 repository，则使用自定义实现；
        否则默认使用 FileMemorySessionRepository（文件存储）。

        Args:
            persist_path: 持久化文件路径，如 "data/memory/sessions/session_001.json"
            backup_suffix: 备份文件后缀，默认 ".bak"（生成 "session_001.json.bak"）
            repository: 自定义存储实现，若提供则忽略 persist_path
        """
        self._repository = repository or FileMemorySessionRepository(persist_path, backup_suffix=backup_suffix)

    @property
    def enabled(self) -> bool:
        """持久化是否已启用。

        当 persist_path 为 None 或存储后端不可用时，返回 False。
        """
        return bool(self._repository.enabled)

    @property
    def backup_path(self) -> Optional[str]:
        """返回备份文件路径（主文件路径 + 备份后缀）。

        用于诊断和手动恢复场景。
        """
        return self._repository.backup_path

    def load_snapshot(self) -> tuple[Optional[dict[str, Any]], bool]:
        """【核心】加载最新的可用快照。

        加载策略：
          1. 优先加载主文件
          2. 主文件损坏或不存在时，尝试加载备份文件
          3. 两者都不可用时返回 (None, False)

        Returns:
            (快照数据, 是否来自备份文件) 的元组
            - 快照数据：字典格式的会话记忆，None 表示无可用快照
            - 是否来自备份：True 表示从备份文件恢复
        """
        return self._repository.load_snapshot()

    def write_snapshot(self, payload: dict[str, Any]) -> None:
        """【核心】写入当前快照到主文件和备份文件。

        双写策略：同时写入主文件和备份文件，确保任一文件损坏时
        都可从另一个恢复。

        Args:
            payload: 要持久化的会话记忆数据（字典格式）
        """
        self._repository.write_snapshot(payload)

    def restore_primary(self, payload: dict[str, Any]) -> None:
        """从恢复的快照数据重写主文件。

        当主文件损坏，从备份文件恢复数据后，调用此方法
        将恢复的数据写回主文件，使下次加载时能直接使用主文件。

        Args:
            payload: 从备份恢复的快照数据
        """
        self._repository.restore_primary(payload)


__all__ = ["MemoryPersistenceStore"]
