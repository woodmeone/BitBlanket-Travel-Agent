"""
工具注册中心

提供动态工具注册、发现、版本管理和分类标签功能。
支持基于关键词和 LLM 的语义搜索两种模式。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Union
from enum import Enum
import logging
import json

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """工具分类"""
    SEARCH = "search"           # 搜索
    RECOMMENDATION = "recommendation"  # 推荐
    PLANNING = "planning"       # 规划
    CALCULATION = "calculation" # 计算
    INFORMATION = "information" # 信息查询
    CUSTOM = "custom"          # 自定义


class ToolStatus(Enum):
    """工具状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"


@dataclass
class ToolMetadata:
    """工具元数据"""
    tool_id: str
    name: str
    description: str
    category: ToolCategory
    tags: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    author: str = ""
    parameters_schema: Dict = field(default_factory=dict)
    examples: List[str] = field(default_factory=list)
    status: ToolStatus = ToolStatus.ACTIVE


@dataclass
class ToolInfo:
    """工具信息"""
    metadata: ToolMetadata
    handler: Callable
    is_async: bool = False


class ToolRegistry:
    """工具注册中心

    特性：
    - 动态注册/注销工具
    - 工具发现和搜索（支持关键词和 LLM 语义搜索）
    - 版本管理
    - 分类和标签
    """

    def __init__(self, llm_client: Any = None):
        """
        初始化工具注册中心

        Args:
            llm_client: 可选的 LLM 客户端，用于语义搜索
        """
        self._tools: Dict[str, ToolInfo] = {}
        self._category_index: Dict[ToolCategory, List[str]] = {}
        self._tag_index: Dict[str, List[str]] = {}
        self._llm_client = llm_client
        self._use_llm_discovery = llm_client is not None
        logger.info(f"ToolRegistry initialized (LLM: {self._use_llm_discovery})")

    def set_llm_client(self, llm_client):
        """设置 LLM 客户端"""
        self._llm_client = llm_client
        self._use_llm_discovery = llm_client is not None
        logger.info(f"LLM client set, semantic discovery: {self._use_llm_discovery}")

    def register(
        self,
        tool_id: str,
        name: str,
        description: str,
        handler: Callable,
        category: ToolCategory = ToolCategory.CUSTOM,
        tags: Optional[List[str]] = None,
        is_async: bool = False,
        **metadata: Any
    ) -> str:
        """注册工具

        Args:
            tool_id: 工具唯一标识
            name: 工具名称
            description: 工具描述
            handler: 工具处理函数
            category: 工具分类
            tags: 标签列表
            is_async: 是否异步工具

        Returns:
            tool_id
        """
        if tool_id in self._tools:
            raise ValueError(f"Tool {tool_id} already registered")

        # 处理 category 参数（可能是字符串或枚举）
        if isinstance(category, str):
            try:
                category = ToolCategory(category)
            except ValueError:
                category = ToolCategory.CUSTOM

        metadata_obj = ToolMetadata(
            tool_id=tool_id,
            name=name,
            description=description,
            category=category,
            tags=tags or [],
            **metadata
        )

        self._tools[tool_id] = ToolInfo(
            metadata=metadata_obj,
            handler=handler,
            is_async=is_async
        )

        # 更新索引
        self._update_indices(tool_id, metadata_obj)

        logger.info(f"Registered tool: {tool_id}")
        return tool_id

    def unregister(self, tool_id: str) -> bool:
        """注销工具

        Args:
            tool_id: 工具ID

        Returns:
            是否成功
        """
        if tool_id not in self._tools:
            return False

        tool_info = self._tools[tool_id]
        metadata = tool_info.metadata

        # 从索引中移除
        if metadata.category in self._category_index:
            if tool_id in self._category_index[metadata.category]:
                self._category_index[metadata.category].remove(tool_id)

        for tag in metadata.tags:
            if tag in self._tag_index and tool_id in self._tag_index[tag]:
                self._tag_index[tag].remove(tool_id)

        del self._tools[tool_id]
        logger.info(f"Unregistered tool: {tool_id}")
        return True

    def get_tool(self, tool_id: str) -> Optional[ToolInfo]:
        """获取工具

        Args:
            tool_id: 工具ID

        Returns:
            工具信息或 None
        """
        return self._tools.get(tool_id)

    def get_handler(self, tool_id: str) -> Optional[Callable]:
        """获取工具处理器

        Args:
            tool_id: 工具ID

        Returns:
            处理器函数或 None
        """
        tool_info = self._tools.get(tool_id)
        return tool_info.handler if tool_info else None

    def discover(self, query: str, top_k: int = 5, use_llm: bool = None) -> List[ToolInfo]:
        """发现工具

        基于名称、描述、标签进行搜索。优先使用 LLM 语义搜索（如果可用）。

        Args:
            query: 查询关键词
            top_k: 返回数量
            use_llm: 是否使用 LLM 搜索（默认自动判断）

        Returns:
            匹配的工具列表
        """
        # 自动判断是否使用 LLM
        if use_llm is None:
            use_llm = self._use_llm_discovery

        # 如果有 LLM 且启用，使用 LLM 语义搜索
        if use_llm and self._llm_client:
            return self._discover_with_llm(query, top_k)

        # 回退到关键词搜索
        return self._discover_with_keywords(query, top_k)

    def _discover_with_llm(self, query: str, top_k: int) -> List[ToolInfo]:
        """使用 LLM 进行语义搜索

        Args:
            query: 查询关键词
            top_k: 返回数量

        Returns:
            匹配的工具列表
        """
        try:
            # 构建工具列表描述
            tools_description = []
            for tool_id, tool_info in self._tools.items():
                if tool_info.metadata.status == ToolStatus.ACTIVE:
                    tools_description.append({
                        "id": tool_id,
                        "name": tool_info.metadata.name,
                        "description": tool_info.metadata.description,
                        "category": tool_info.metadata.category.value,
                        "tags": tool_info.metadata.tags
                    })

            if not tools_description:
                return []

            # 构建 LLM prompt
            system_prompt = """你是一个智能工具推荐助手。根据用户的需求描述，从工具列表中选择最合适的工具。

分析用户需求的核心意图，选择匹配的工具。考虑：
1. 工具名称和描述是否与需求相关
2. 工具的分类和标签是否匹配
3. 工具能否满足用户的具体需求

请以 JSON 格式返回匹配的工具列表：
{
    "matched_tools": [
        {"tool_id": "工具ID", "match_reason": "匹配原因", "confidence": 0.95}
    ],
    "reasoning": "整体匹配分析"
}

confidence 为 0-1 之间的置信度。"""

            tools_json = json.dumps(tools_description, ensure_ascii=False)
            user_prompt = f"""用户需求：{query}

可用工具列表：
{tools_json}

请分析并返回最匹配的工具。"""

            result = self._llm_client.chat([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ], temperature=0.3)

            if result.get("success"):
                content = result.get("content", "")
                matched = self._extract_matched_tools(content)
                if matched:
                    # 按置信度排序
                    matched.sort(key=lambda x: x[1], reverse=True)
                    # 返回匹配的工具
                    result_tools = []
                    for tool_id, confidence in matched[:top_k]:
                        tool_info = self._tools.get(tool_id)
                        if tool_info:
                            result_tools.append(tool_info)
                    return result_tools

        except Exception as e:
            logger.warning(f"LLM 工具发现失败，回退到关键词搜索: {e}")

        # LLM 失败，回退到关键词
        return self._discover_with_keywords(query, top_k)

    def _extract_matched_tools(self, content: str) -> List[tuple]:
        """从 LLM 响应中提取匹配的工具

        Args:
            content: LLM 响应内容

        Returns:
            [(tool_id, confidence), ...]
        """
        matched = []
        try:
            # 尝试解析 JSON
            data = json.loads(content)
            matched_tools = data.get("matched_tools", [])
            for tool in matched_tools:
                tool_id = tool.get("tool_id", "")
                confidence = tool.get("confidence", 0.5)
                if tool_id:
                    matched.append((tool_id, confidence))
        except json.JSONDecodeError:
            # 尝试从文本中提取
            import re
            # 查找 tool_id 和 confidence
            pattern = r'tool_id["\s:]+([^"\\s]+).*?confidence["\s:]+0?\.?(\d+)'
            matches = re.findall(pattern, content, re.DOTALL)
            for tool_id, conf in matches:
                try:
                    confidence = float(f"0.{conf}") if conf else 0.5
                    matched.append((tool_id.strip(), confidence))
                except ValueError:
                    pass

        return matched

    def _discover_with_keywords(self, query: str, top_k: int) -> List[ToolInfo]:
        """使用关键词进行搜索

        Args:
            query: 查询关键词
            top_k: 返回数量

        Returns:
            匹配的工具列表
        """
        query_lower = query.lower()
        results = []

        for tool_id, tool_info in self._tools.items():
            metadata = tool_info.metadata
            score = 0

            # 跳过非活跃工具
            if metadata.status != ToolStatus.ACTIVE:
                continue

            # 名称匹配
            if query_lower in metadata.name.lower():
                score += 10

            # 描述匹配
            if query_lower in metadata.description.lower():
                score += 5

            # 标签匹配
            for tag in metadata.tags:
                if query_lower in tag.lower():
                    score += 3

            if score > 0:
                results.append((tool_id, tool_info, score))

        # 按分数排序
        results.sort(key=lambda x: x[2], reverse=True)
        return [r[1] for r in results[:top_k]]

    def list_tools(
        self,
        category: Optional[ToolCategory] = None,
        status: Optional[ToolStatus] = None,
        tags: Optional[List[str]] = None
    ) -> List[ToolInfo]:
        """列出工具

        Args:
            category: 分类过滤
            status: 状态过滤
            tags: 标签过滤

        Returns:
            工具列表
        """
        results = []

        for tool_info in self._tools.values():
            metadata = tool_info.metadata


            if category and metadata.category != category:
                continue

            # 状态过滤
            if status and metadata.status != status:
                continue

            # 标签过滤
            if tags and not any(t in metadata.tags for t in tags):
                continue

            results.append(tool_info)

        return results

    def get_stats(self) -> Dict:
        """获取统计信息

        Returns:
            统计信息字典
        """
        category_count = {}
        status_count = {}

        for tool_info in self._tools.values():
            cat = tool_info.metadata.category.value
            sta = tool_info.metadata.status.value

            category_count[cat] = category_count.get(cat, 0) + 1
            status_count[sta] = status_count.get(sta, 0) + 1

        return {
            "total_tools": len(self._tools),
            "by_category": category_count,
            "by_status": status_count
        }

    def _update_indices(self, tool_id: str, metadata: ToolMetadata):
        """更新索引"""
        # 分类索引
        if metadata.category not in self._category_index:
            self._category_index[metadata.category] = []
        if tool_id not in self._category_index[metadata.category]:
            self._category_index[metadata.category].append(tool_id)

        # 标签索引
        for tag in metadata.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = []
            if tool_id not in self._tag_index[tag]:
                self._tag_index[tag].append(tool_id)


# 全局单例
tool_registry = ToolRegistry()
