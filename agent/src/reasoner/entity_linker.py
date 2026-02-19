"""
实体链接器

提供实体链接和消歧功能，支持知识库管理、实体搜索和 LLM 增强的消歧。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from collections import defaultdict
import logging
import json
import re

logger = logging.getLogger(__name__)


@dataclass
class LinkedEntity:
    """链接的实体"""
    entity_id: str
    name: str
    entity_type: str
    aliases: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    confidence: float = 1.0


class EntityLinker:
    """实体链接器

    特性：
    - 实体知识库管理
    - 实体搜索
    - 候选实体排序
    - LLM 增强的消歧
    """

    def __init__(self, llm_client: Any = None):
        """
        初始化实体链接器

        Args:
            llm_client: 可选的 LLM 客户端，用于智能消歧
        """
        self._entities: Dict[str, LinkedEntity] = {}
        self._name_index: Dict[str, List[str]] = defaultdict(list)  # name -> entity_ids
        self._alias_index: Dict[str, List[str]] = defaultdict(list)  # alias -> entity_ids
        self._type_index: Dict[str, List[str]] = defaultdict(list)  # type -> entity_ids
        self._llm_client = llm_client
        self._init_default_entities()
        logger.info("EntityLinker initialized")

    def set_llm_client(self, llm_client):
        """设置 LLM 客户端"""
        self._llm_client = llm_client

    def _init_default_entities(self):
        """初始化默认实体（常见旅游城市）"""
        default_cities = [
            ("beijing", "北京", "city", ["京城", "北平", "首都"], {"population": 21000000, "region": "华北"}),
            ("shanghai", "上海", "city", ["沪上", "申城", "魔都"], {"population": 24000000, "region": "华东"}),
            ("hangzhou", "杭州", "city", ["西湖", "临安"], {"population": 12000000, "region": "华东"}),
            ("chengdu", "成都", "city", ["天府", "蓉城"], {"population": 21000000, "region": "西南"}),
            ("xian", "西安", "city", ["长安", "雁塔"], {"population": 13000000, "region": "西北"}),
            ("guangzhou", "广州", "city", ["羊城", "穗城"], {"population": 15000000, "region": "华南"}),
            ("shenzhen", "深圳", "city", ["鹏城"], {"population": 17000000, "region": "华南"}),
            ("chongqing", "重庆", "city", ["山城", "雾都"], {"population": 32000000, "region": "西南"}),
        ]

        for entity_id, name, entity_type, aliases, attrs in default_cities:
            self.add_entity(entity_id, name, entity_type, aliases, attrs)

    def add_entity(
        self,
        entity_id: str,
        name: str,
        entity_type: str,
        aliases: List[str] = None,
        attributes: Dict[str, Any] = None,
        description: str = ""
    ):
        """添加实体到知识库

        Args:
            entity_id: 实体ID
            name: 实体名称
            entity_type: 实体类型
            aliases: 别名列表
            attributes: 属性字典
            description: 描述
        """
        entity = LinkedEntity(
            entity_id=entity_id,
            name=name,
            entity_type=entity_type,
            aliases=aliases or [],
            attributes=attributes or {},
            description=description
        )

        self._entities[entity_id] = entity

        # 更新索引
        self._name_index[name.lower()].append(entity_id)
        for alias in (aliases or []):
            self._alias_index[alias.lower()].append(entity_id)
        self._type_index[entity_type].append(entity_id)

        logger.debug(f"Added entity: {entity_id} - {name}")

    def link(
        self,
        text: str,
        entity_type: Optional[str] = None,
        context: Dict = None
    ) -> List[LinkedEntity]:
        """链接文本中的实体

        Args:
            text: 输入文本
            entity_type: 实体类型过滤
            context: 上下文信息

        Returns:
            链接的实体列表
        """
        # 优先使用 LLM 进行消歧
        if self._llm_client:
            return self._link_with_llm(text, entity_type, context)

        # 回退到规则匹配
        return self._link_with_rules(text, entity_type)

    def _link_with_llm(
        self,
        text: str,
        entity_type: Optional[str],
        context: Optional[Dict]
    ) -> List[LinkedEntity]:
        """使用 LLM 进行实体链接

        Args:
            text: 输入文本
            entity_type: 实体类型过滤
            context: 上下文信息

        Returns:
            链接的实体列表
        """
        try:
            # 获取候选实体
            candidates = self._get_candidates(text, entity_type)
            if not candidates:
                return []

            # 构建候选列表
            candidates_info = [
                {
                    "entity_id": e.entity_id,
                    "name": e.name,
                    "type": e.entity_type,
                    "aliases": e.aliases,
                    "description": e.description
                }
                for e in candidates
            ]

            context_str = json.dumps(context or {}, ensure_ascii=False)

            system_prompt = """你是一个实体链接专家。从给定的候选实体中，找出文本中提到的实体。"""

            user_prompt = f"""文本：{text}
上下文：{context_str}

候选实体：
{json.dumps(candidates_info, ensure_ascii=False, indent=2)}

请以 JSON 格式返回链接的实体：
{{
    "linked_entities": [
        {{
            "entity_id": "实体ID",
            "matched_text": "匹配的文本",
            "confidence": 0.0-1.0
        }}
    ]
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
                    linked = []
                    for link in data.get("linked_entities", []):
                        entity_id = link.get("entity_id", "")
                        if entity_id in self._entities:
                            entity = self._entities[entity_id]
                            entity.confidence = link.get("confidence", 0.5)
                            linked.append(entity)
                    return linked
                except json.JSONDecodeError:
                    logger.warning("Failed to parse LLM link response")

        except Exception as e:
            logger.warning(f"LLM entity linking failed: {e}")

        # LLM 失败，回退到规则
        return self._link_with_rules(text, entity_type)

    def _link_with_rules(
        self,
        text: str,
        entity_type: Optional[str]
    ) -> List[LinkedEntity]:
        """使用规则进行实体链接

        Args:
            text: 输入文本
            entity_type: 实体类型过滤

        Returns:
            链接的实体列表
        """
        linked = []
        matched_ids = set()

        # 1. 精确匹配名称
        text_lower = text.lower()
        for name, entity_ids in self._name_index.items():
            if name in text_lower:
                for entity_id in entity_ids:
                    if entity_id not in matched_ids:
                        entity = self._entities.get(entity_id)
                        if entity and (entity_type is None or entity.entity_type == entity_type):
                            linked.append(entity)
                            matched_ids.add(entity_id)

        # 2. 匹配别名
        for alias, entity_ids in self._alias_index.items():
            if alias in text_lower:
                for entity_id in entity_ids:
                    if entity_id not in matched_ids:
                        entity = self._entities.get(entity_id)
                        if entity and (entity_type is None or entity.entity_type == entity_type):
                            entity.confidence = 0.8  # 别名匹配置信度较低
                            linked.append(entity)
                            matched_ids.add(entity_id)

        return linked

    def _get_candidates(
        self,
        text: str,
        entity_type: Optional[str]
    ) -> List[LinkedEntity]:
        """获取候选实体

        Args:
            text: 输入文本
            entity_type: 实体类型过滤

        Returns:
            候选实体列表
        """
        candidates = []
        text_lower = text.lower()

        # 收集所有相关实体
        for entity_id, entity in self._entities.items():
            if entity_type and entity.entity_type != entity_type:
                continue

            # 检查名称或别名是否在文本中
            if entity.name.lower() in text_lower:
                candidates.append(entity)
                continue

            for alias in entity.aliases:
                if alias.lower() in text_lower:
                    candidates.append(entity)
                    break

        return candidates

    def search(
        self,
        query: str,
        entity_type: Optional[str] = None,
        limit: int = 10
    ) -> List[LinkedEntity]:
        """搜索实体

        Args:
            query: 查询关键词
            entity_type: 实体类型过滤
            limit: 返回数量

        Returns:
            匹配的实体列表
        """
        results = []
        query_lower = query.lower()

        for entity_id, entity in self._entities.items():
            if entity_type and entity.entity_type != entity_type:
                continue

            score = 0

            # 名称匹配
            if query_lower in entity.name.lower():
                score += 10

            # 别名匹配
            for alias in entity.aliases:
                if query_lower in alias.lower():
                    score += 5

            # 描述匹配
            if query_lower in entity.description.lower():
                score += 3

            # 属性匹配
            for key, value in entity.attributes.items():
                if query_lower in str(value).lower():
                    score += 2

            if score > 0:
                entity.confidence = min(score / 15.0, 1.0)
                results.append((entity_id, entity, score))

        # 按分数排序
        results.sort(key=lambda x: x[2], reverse=True)
        return [r[1] for r in results[:limit]]

    def get_entity(self, entity_id: str) -> Optional[LinkedEntity]:
        """获取实体

        Args:
            entity_id: 实体ID

        Returns:
            实体或 None
        """
        return self._entities.get(entity_id)

    def list_entities(self, entity_type: Optional[str] = None) -> List[LinkedEntity]:
        """列出实体

        Args:
            entity_type: 实体类型过滤

        Returns:
            实体列表
        """
        if entity_type:
            return [self._entities[eid] for eid in self._type_index.get(entity_type, [])]
        return list(self._entities.values())

    def get_stats(self) -> Dict:
        """获取统计信息"""
        type_count = defaultdict(int)
        for entity in self._entities.values():
            type_count[entity.entity_type] += 1

        return {
            "total_entities": len(self._entities),
            "by_type": dict(type_count)
        }


# 全局单例
entity_linker = EntityLinker()
