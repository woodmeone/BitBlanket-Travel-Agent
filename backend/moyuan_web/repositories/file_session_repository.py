"""
基于文件的会话仓库 —— 原子写入与备份恢复

【基础知识】
- 原子写入（Atomic Write）：先写入临时文件，再通过 os.replace 原子性地替换目标文件。
  这样即使写入过程中进程崩溃，目标文件要么是旧版本（完整），要么是新版本（完整），
  不会出现半写（corrupted）的情况。

- 备份恢复：每次保存时同时写入主文件和 .bak 备份文件。如果主文件损坏，
  加载时自动从备份文件恢复，保证数据可靠性。

- asyncio.Lock：异步锁，确保同一时刻只有一个协程在修改会话数据，
  防止并发写入导致数据竞争。

- asyncio.to_thread：将阻塞的文件 I/O 操作放到线程池中执行，
  避免阻塞事件循环影响其他请求的响应速度。
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Any

from .session_repository import SessionRepository


def _utc_now_iso() -> str:
    """返回当前 UTC 时间的 ISO-8601 格式字符串。"""

    return datetime.now(timezone.utc).isoformat()


def _parse_iso_as_utc(value: Any) -> datetime | None:
    """将 ISO 时间戳解析为带时区的 UTC datetime 对象。"""

    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_iso_to_timestamp(value: Any) -> float:
    """将 ISO 时间戳解析为 Unix 秒数，用于排序和过期检查。"""

    parsed = _parse_iso_as_utc(value)
    return parsed.timestamp() if parsed is not None else 0.0


class FileSessionRepository(SessionRepository):
    """基于文件的会话持久化仓库 —— 使用 JSON 快照 + .bak 备份文件存储会话数据。

    数据存储结构：单个 JSON 文件包含所有会话，key 为 session_id。
    适用于单实例部署场景，多实例部署需切换到数据库仓库。
    """

    BACKUP_SUFFIX = ".bak"

    def __init__(self, file_path: str = "data/sessions/sessions.json") -> None:
        """初始化文件仓库，创建数据目录并加载现有快照。"""

        os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
        self._file_path = file_path
        self._lock = asyncio.Lock()  # 异步锁，保证并发安全
        self._sessions: dict[str, dict[str, Any]] = self._load_from_file()  # 从文件加载会话数据到内存

    @classmethod
    def backup_path(cls, path: str) -> str:
        """返回主 JSON 文件对应的备份路径（添加 .bak 后缀）。"""

        return f"{path}{cls.BACKUP_SUFFIX}"

    @staticmethod
    def _load_json_file(path: str) -> dict[str, dict[str, Any]] | None:
        """加载 JSON 快照文件，文件不存在或格式错误时返回 None。"""

        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return None
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _fsync_directory(path: str) -> None:
        """尽力而为地同步目录的文件系统元数据，确保 os.replace 的结果在崩溃后仍可见。

        在 Linux 等系统上，os.replace 只是修改目录项，需要 fsync 目录才能保证持久化。
        """

        try:
            directory_fd = os.open(path, os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(directory_fd)
        except OSError:
            pass
        finally:
            os.close(directory_fd)

    def _atomic_write_json(self, path: str, payload: dict[str, dict[str, Any]]) -> None:
        """【核心】原子写入 JSON 数据：先写临时文件 → fsync → os.replace 替换目标文件。

        步骤：
        1. 在目标目录创建临时文件（.sessions.json.XXXXXX.tmp）
        2. 将 JSON 数据写入临时文件并 flush + fsync 确保落盘
        3. os.replace 原子性地将临时文件重命名为目标文件
        4. fsync 目录确保目录项更新持久化
        """

        target_dir = os.path.dirname(path) or "."
        os.makedirs(target_dir, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(
            prefix=f".{os.path.basename(path)}.",
            suffix=".tmp",
            dir=target_dir,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
                json.dump(payload, tmp_file, ensure_ascii=False, indent=2)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())  # 确保数据写入磁盘，而非停留在操作系统缓存
            os.replace(temp_path, path)  # 【核心】原子性替换：要么完全成功，要么完全不变
            self._fsync_directory(target_dir)  # 确保目录项更新持久化
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)  # 清理残留的临时文件（正常情况下已被 replace 移走）
                except OSError:
                    pass

    def _load_from_file(self) -> dict[str, dict[str, Any]]:
        """加载会话数据：优先读取主文件，损坏时从备份恢复。"""

        primary_payload = self._load_json_file(self._file_path)
        if primary_payload is not None:
            return primary_payload

        backup_payload = self._load_json_file(self.backup_path(self._file_path))
        if backup_payload is None:
            return {}  # 主文件和备份都不可用，返回空字典（全新状态）

        try:
            self._atomic_write_json(self._file_path, backup_payload)  # 用备份数据恢复主文件
        except OSError:
            pass
        return backup_payload

    def _save_to_file(self) -> None:
        """将内存中的会话数据持久化到主文件和备份文件。"""

        self._atomic_write_json(self._file_path, self._sessions)
        self._atomic_write_json(self.backup_path(self._file_path), self._sessions)

    async def create(self, session_data: dict[str, Any]) -> str:
        """创建一条新会话记录并持久化到文件快照。"""

        async with self._lock:
            session_id = str(session_data.get("session_id") or uuid.uuid4())
            now = _utc_now_iso()
            messages = list(session_data.get("messages", [])) if isinstance(session_data.get("messages"), list) else []
            self._sessions[session_id] = {
                "session_id": session_id,
                "created_at": str(session_data.get("created_at") or now),
                "last_active": str(session_data.get("last_active") or now),
                "message_count": int(session_data.get("message_count", len(messages))),
                "name": str(session_data.get("name") or ""),
                "model_id": str(session_data.get("model_id") or "gpt-4o-mini"),
                "messages": messages,
                "user_preferences": dict(session_data.get("user_preferences", {})),
            }
            await asyncio.to_thread(self._save_to_file)  # 在线程池中执行文件写入，避免阻塞事件循环
            return session_id

    async def get(self, session_id: str) -> dict[str, Any] | None:
        """根据 ID 返回一条会话记录，不存在则返回 None。"""

        async with self._lock:
            session = self._sessions.get(session_id)
            return dict(session) if isinstance(session, dict) else None

    async def update(self, session_id: str, session_data: dict[str, Any]) -> None:
        """更新一条现有会话记录（原地合并）并持久化。"""

        async with self._lock:
            existing = self._sessions.get(session_id)
            if not isinstance(existing, dict):
                return
            merged = dict(existing)
            merged.update(session_data)
            merged["session_id"] = session_id  # 确保 session_id 不被覆盖
            merged["created_at"] = existing.get("created_at")  # 创建时间不可变
            merged["last_active"] = _utc_now_iso()  # 更新最后活跃时间
            merged["message_count"] = int(merged.get("message_count", len(merged.get("messages", []))))
            self._sessions[session_id] = merged
            await asyncio.to_thread(self._save_to_file)  # 在线程池中执行文件写入，避免阻塞事件循环

    async def delete(self, session_id: str) -> bool:
        """删除一条会话记录，存在则删除并返回 True，不存在返回 False。"""

        async with self._lock:
            if session_id not in self._sessions:
                return False
            del self._sessions[session_id]
            await asyncio.to_thread(self._save_to_file)  # 在线程池中执行文件写入，避免阻塞事件循环
            return True

    async def list_all(self, include_empty: bool = False, limit: int = 100) -> list[dict[str, Any]]:
        """列出会话，按最后活跃时间降序排列。

        参数：
        - include_empty：是否包含空会话（消息数为0且超过1小时未活跃）
        - limit：返回的最大数量

        默认过滤逻辑：只返回有消息的会话，或1小时内活跃的会话。
        """

        async with self._lock:
            sessions = [dict(item) for item in self._sessions.values()]

        one_hour_ago = datetime.now(timezone.utc).timestamp() - 3600  # 1小时前的时间戳
        result: list[dict[str, Any]] = []
        for session_data in sessions:
            last_active = _parse_iso_to_timestamp(session_data.get("last_active"))
            if include_empty:
                result.append(session_data)
            elif session_data.get("message_count", 0) > 0 or last_active > one_hour_ago:  # 有消息或1小时内活跃
                result.append(session_data)

        result.sort(key=lambda item: _parse_iso_to_timestamp(item.get("last_active")), reverse=True)
        return result[:limit]

    async def cleanup_expired(self, max_age_seconds: int) -> int:
        """清理过期的会话记录，删除最后活跃时间超过阈值的会话。

        参数：
        - max_age_seconds：最大存活秒数，超过此时间的会话将被删除

        返回：被删除的会话数量
        """

        async with self._lock:
            current_time = datetime.now(timezone.utc)
            expired_ids = [
                session_id
                for session_id, data in self._sessions.items()
                if (
                    (last_active := _parse_iso_as_utc(data.get("last_active"))) is not None
                    and (current_time - last_active).total_seconds() > max_age_seconds
                )
            ]
            for session_id in expired_ids:
                del self._sessions[session_id]
            if expired_ids:
                await asyncio.to_thread(self._save_to_file)  # 在线程池中执行文件写入，避免阻塞事件循环
            return len(expired_ids)
