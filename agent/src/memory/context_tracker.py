"""
上下文追踪器

提供跨轮次实体追踪、代词消歧、实体续接和上下文恢复功能。
支持基于规则的追踪和 LLM 增强的消歧。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class TrackedEntity:
    """追踪的实体"""
    id: str
    type: str           # city, attraction, hotel, etc.
    value: str          # 北京, 故宫
    mentions: int = 0   # 提及次数
    last_mentioned: str = ""  # 最后提及的时间
    turns_ago: int = 0  # 多少轮之前


@dataclass
class EntityReference:
    """实体引用"""
    text: str           # 引用的文本
    type: str          # 代词/指示词
    resolved_to: Optional[str] = None  # 解析到的实体ID


class ContextTracker:
    """上下文追踪器

    特性：
    - 跨轮次实体追踪
    - 代词消歧
    - 实体续接
    - 上下文恢复
    - LLM 增强的消歧
    """

    # 代词映射
    PRONOUN_MAPPING = {
        "它": "previously_mentioned",
        "这个": "previously_mentioned",
        "那个": "previously_mentioned",
        "那里": "location",
        "这里": "location",
        "这类": "category",
        "那种": "category"
    }

    def __init__(self, llm_client: Any = None, max_tracked: int = 50, max_turns: int = 10):
        """
        初始化上下文追踪器

        Args:
            llm_client: 可选的 LLM 客户端，用于智能消歧
            max_tracked: 最大追踪实体数
            max_turns: 最大追踪轮次数
        """
        self._tracked_entities: Dict[str, Dict[str, TrackedEntity]] = defaultdict(dict)
        self._references: Dict[str, List[EntityReference]] = defaultdict(list)
        self._turn_count: Dict[str, int] = defaultdict(int)
        self._max_tracked = max_tracked
        self._max_turns = max_turns
        self._llm_client = llm_client
        logger.info("ContextTracker initialized")

    def set_llm_client(self, llm_client):
        """设置 LLM 客户端"""
        self._llm_client = llm_client

    def next_turn(self, session_id: str):
        """进入下一轮"""
        self._turn_count[session_id] += 1

    def track_entity(
        self,
        session_id: str,
        entity_type: str,
        value: str,
        turn_id: Optional[int] = None
    ) -> str:
        """追踪实体

        Args:
            session_id: 会话ID
            entity_type: 实体类型
            value: 实体值
            turn_id: 轮次ID

        Returns:
            实体ID
        """
        entity_id = f"{entity_type}:{value}"

        current_turn = self._turn_count.get(session_id, 0)

        if entity_id not in self._tracked_entities[session_id]:
            # 检查是否超过最大追踪数
            if len(self._tracked_entities[session_id]) >= self._max_tracked:
                # 移除最老的实体
                self._evict_oldest_entity(session_id)

            self._tracked_entities[session_id][entity_id] = TrackedEntity(
                id=entity_id,
                type=entity_type,
                value=value
            )

        entity = self._tracked_entities[session_id][entity_id]
        entity.mentions += 1
        entity.last_mentioned = datetime.now().isoformat()

        if turn_id is not None:
            entity.turns_ago = current_turn - turn_id
        else:
            entity.turns_ago = 0

        return entity_id

    def track_entities_from_ner(
        self,
        session_id: str,
        entities: Dict[str, Any],
        turn_id: Optional[int] = None
    ) -> Dict[str, str]:
        """从NER结果追踪实体

        Args:
            session_id: 会话ID
            entities: NER识别的实体
            turn_id: 轮次ID

        Returns:
            {entity_type: entity_id}
        """
        entity_ids = {}

        for entity_type, value in entities.items():
            if isinstance(value, list):
                for v in value:
                    entity_id = self.track_entity(session_id, entity_type, str(v), turn_id)
                    entity_ids[entity_type] = entity_id
            else:
                entity_id = self.track_entity(session_id, entity_type, str(value), turn_id)
                entity_ids[entity_type] = entity_id

        return entity_ids

    def resolve_reference(
        self,
        session_id: str,
        reference: str,
        reference_type: str = "pronoun"
    ) -> Optional[TrackedEntity]:
        """消歧引用

        Args:
            session_id: 会话ID
            reference: 引用的文本 (它/这个)
            reference_type: 引用类型

        Returns:
            解析到的实体
        """
        # 如果有 LLM，使用 LLM 进行智能消歧
        if self._llm_client and reference_type == "pronoun":
            return self._resolve_with_llm(session_id, reference)

        # 回退到规则
        return self._resolve_with_rules(session_id, reference_type)

    def _resolve_with_llm(
        self,
        session_id: str,
        reference: str
    ) -> Optional[TrackedEntity]:
        """使用 LLM 进行消歧

        Args:
            session_id: 会话ID
            reference: 引用的文本

        Returns:
            解析到的实体
        """
        try:
            # 获取当前追踪的实体
            entities = self.get_active_entities(session_id, max_turns=10)
            if not entities:
                return None

            # 构建实体列表
            entities_info = [
                {"id": e.id, "type": e.type, "value": e.value, "mentions": e.mentions}
                for e in entities
            ]

            system_prompt = """你是一个实体消歧专家。根据用户的引用文本，解析出实际指的实体。"""

            user_prompt = f"""用户引用：{reference}

当前可用的实体：
{json.dumps(entities_info, ensure_ascii=False, indent=2)}

请以 JSON 格式返回解析结果：
{{
    "resolved_entity_id": "实体ID，如果无法解析则为空",
    "reason": "解析原因"
}}

只返回 JSON。"""

            result = self._llm_client.chat([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ], temperature=0.3)

            if result.get("success"):
                content = result.get("content", "")
                try:
                    data = json.loads(content)
                    entity_id = data.get("resolved_entity_id", "")
                    if entity_id and entity_id in self._tracked_entities[session_id]:
                        return self._tracked_entities[session_id][entity_id]
                except json.JSONDecodeError:
                    logger.warning("Failed to parse LLM resolution response")

        except Exception as e:
            logger.warning(f"LLM resolution failed: {e}")

        # LLM 失败，回退到规则
        return self._resolve_with_rules(session_id, "pronoun")

    def _resolve_with_rules(
        self,
        session_id: str,
        reference_type: str
    ) -> Optional[TrackedEntity]:
        """使用规则进行消歧

        Args:
            session_id: 会话ID
            reference_type: 引用类型

        Returns:
            解析到的实体
        """
        if session_id not in self._tracked_entities:
            return None

        entities = self._tracked_entities[session_id]

        if reference_type == "pronoun":
            # 返回最近提到的实体
            sorted_entities = sorted(
                entities.values(),
                key=lambda e: e.turns_ago
            )
            for entity in sorted_entities:
                if entity.turns_ago <= 2:  # 2轮以内
                    return entity

        return None

    def get_active_entities(
        self,
        session_id: str,
        entity_type: Optional[str] = None,
        max_turns: int = 5
    ) -> List[TrackedEntity]:
        """获取活跃实体

        Args:
            session_id: 会话ID
            entity_type: 实体类型过滤
            max_turns: 最多多少轮之前

        Returns:
            活跃实体列表
        """
        if session_id not in self._tracked_entities:
            return []

        entities = list(self._tracked_entities[session_id].values())

        # 过滤
        if entity_type:
            entities = [e for e in entities if e.type == entity_type]

        entities = [e for e in entities if e.turns_ago <= max_turns]

        # 按提及次数排序
        entities.sort(key=lambda e: (e.turns_ago, -e.mentions))

        return entities

    def get_entity_by_type(
        self,
        session_id: str,
        entity_type: str
    ) -> Optional[TrackedEntity]:
        """获取指定类型的最新实体

        Args:
            session_id: 会话ID
            entity_type: 实体类型

        Returns:
            实体或 None
        """
        entities = self.get_active_entities(session_id, entity_type=entity_type, max_turns=20)
        return entities[0] if entities else None

    def get_context_summary(self, session_id: str) -> Dict[str, Any]:
        """获取上下文摘要

        Args:
            session_id: 会话ID

        Returns:
            上下文摘要
        """
        entities = self.get_active_entities(session_id, max_turns=10)

        return {
            "session_id": session_id,
            "turn_count": self._turn_count.get(session_id, 0),
            "tracked_entities": len(entities),
            "entities": [
                {
                    "type": e.type,
                    "value": e.value,
                    "mentions": e.mentions,
                    "turns_ago": e.turns_ago
                }
                for e in entities
            ]
        }

    def clear_session(self, session_id: str):
        """清除会话追踪数据

        Args:
            session_id: 会话ID
        """
        if session_id in self._tracked_entities:
            del self._tracked_entities[session_id]
        if session_id in self._references:
            del self._references[session_id]
        if session_id in self._turn_count:
            del self._turn_count[session_id]

    def _evict_oldest_entity(self, session_id: str):
        """淘汰最老的实体

        Args:
            session_id: 会话ID
        """
        if session_id not in self._tracked_entities:
            return

        entities = list(self._tracked_entities[session_id].values())
        if not entities:
            return

        # 找出最老的实体
        oldest = min(entities, key=lambda e: (e.turns_ago, -e.mentions))
        del self._tracked_entities[session_id][oldest.id]


# 全局单例
context_tracker = ContextTracker()
