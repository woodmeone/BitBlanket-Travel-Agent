"""持久化分享链接编排服务，负责旅行计划的分享功能。

分享链接说明：
    用户可以将生成的旅行计划通过分享链接分享给他人。分享记录包含：
    - 分享 ID（10位随机十六进制字符串）
    - 标题、纯文本内容、HTML 内容
    - 投递包（delivery_bundle，含完整旅行计划数据）
    - 创建时间

    分享数据持久化到 JSON 文件中，支持备份机制。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from ..repositories.file_share_link_repository import FileShareLinkRepository
from ..repositories.share_link_repository import ShareLinkRepository


def _utc_now_iso() -> str:
    """返回当前 UTC 时间的 ISO-8601 格式字符串。"""
    return datetime.now(timezone.utc).isoformat()


class ShareService:
    """使用配置的仓库创建和获取分享的旅行计划。"""

    BACKUP_SUFFIX = FileShareLinkRepository.BACKUP_SUFFIX

    def __init__(
        self,
        file_path: str = "data/share_links.json",
        repository: ShareLinkRepository | None = None,
    ) -> None:
        """使用文件支持的默认仓库初始化服务。

        Args:
            file_path: 分享链接 JSON 文件路径，默认 "data/share_links.json"
            repository: 可选的仓库实例，未提供时使用 FileShareLinkRepository
        """

        self._repository = repository or FileShareLinkRepository(file_path)

    @classmethod
    def _backup_path(cls, path: str) -> str:
        """返回主分享链接快照的备份文件路径。"""

        return FileShareLinkRepository.backup_path(path)

    async def create(
        self,
        *,
        title: str | None,
        content: str,
        html_content: str | None = None,
        delivery_bundle: dict[str, Any] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """创建分享记录并返回生成的分享 URL 元数据。

        Args:
            title: 分享标题（可选）
            content: 纯文本内容（必填，不能为空）
            html_content: HTML 格式内容（可选，用于富文本展示）
            delivery_bundle: 投递包，含完整旅行计划数据（可选）

        Returns:
            (share_id, record) 元组，share_id 为10位随机 ID

        Raises:
            ValueError: 当 content 为空时
        """
        if not content.strip():
            raise ValueError("content cannot be empty")

        share_id = uuid.uuid4().hex[:10]
        record = {
            "share_id": share_id,
            "title": title.strip() if title else "",
            "content": content.strip(),
            "html_content": html_content.strip() if html_content else "",
            "delivery_bundle": delivery_bundle,
            "created_at": _utc_now_iso(),
        }
        await self._repository.save(record)
        return share_id, record

    async def get(self, share_id: str) -> dict[str, Any] | None:
        """根据分享令牌返回一条分享记录。"""

        return await self._repository.get(share_id)
