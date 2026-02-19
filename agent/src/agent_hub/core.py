"""
Agent 市场与共享平台

提供 Agent 发布、发现、评价和下载功能。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import logging
import uuid

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent 状态"""
    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    FEATURED = "featured"


@dataclass
class AgentMetadata:
    """Agent 元数据"""
    agent_id: str
    name: str
    description: str
    version: str
    author: str
    category: str
    tags: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    input_schema: Dict = field(default_factory=dict)
    output_schema: Dict = field(default_factory=dict)
    examples: List[Dict] = field(default_factory=list)
    ratings: List[int] = field(default_factory=list)
    downloads: int = 0
    status: AgentStatus = AgentStatus.DRAFT
    created_at: str = ""
    updated_at: str = ""


@dataclass
class AgentTemplate:
    """Agent 模板"""
    template_id: str
    name: str
    description: str
    category: str
    config: Dict = field(default_factory=dict)
    skills: List[str] = field(default_factory=list)


class AgentHub:
    """Agent 市场

    特性：
    - Agent 发布和管理
    - Agent 发现和搜索
    - Agent 评价和评分
    - Agent 模板支持
    - 下载和使用统计
    """

    # 内置 Agent 分类
    CATEGORIES = [
        "旅行规划",
        "城市推荐",
        "景点导览",
        "美食推荐",
        "住宿咨询",
        "交通指南",
        "预算规划",
        "行程安排",
        "综合助手"
    ]

    def __init__(self):
        self._agents: Dict[str, AgentMetadata] = {}
        self._templates: Dict[str, AgentTemplate] = {}
        self._usage_stats: Dict[str, Dict] = {}
        self._init_builtin_agents()
        logger.info("AgentHub initialized")

    def _init_builtin_agents(self):
        """初始化内置 Agent"""
        # 城市推荐专家
        self.register_template(
            template_id="city_expert",
            name="城市推荐专家",
            description="根据用户偏好推荐最合适的旅游城市",
            category="城市推荐",
            config={"max_recommendations": 5},
            skills=["city_recommendation", "preference_analysis"]
        )

        # 行程规划师
        self.register_template(
            template_id="trip_planner",
            name="智能行程规划师",
            description="为用户规划详细的旅行行程",
            category="行程安排",
            config={"default_days": 3},
            skills=["route_planning", "attraction_selection"]
        )

    def publish_agent(
        self,
        name: str,
        description: str,
        version: str,
        author: str,
        category: str,
        **kwargs
    ) -> str:
        """发布 Agent"""
        agent_id = f"agent_{uuid.uuid4().hex[:8]}"

        metadata = AgentMetadata(
            agent_id=agent_id,
            name=name,
            description=description,
            version=version,
            author=author,
            category=category,
            tags=kwargs.get("tags", []),
            capabilities=kwargs.get("capabilities", []),
            input_schema=kwargs.get("input_schema", {}),
            output_schema=kwargs.get("output_schema", {}),
            examples=kwargs.get("examples", []),
            status=AgentStatus.PUBLISHED,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )

        self._agents[agent_id] = metadata
        logger.info(f"Published agent: {name} ({agent_id})")
        return agent_id

    def discover_agents(self, query: str = "", category: str = None,
                       tags: List[str] = None, top_k: int = 10) -> List[AgentMetadata]:
        """发现 Agent"""
        results = []

        for agent in self._agents.values():
            if agent.status not in [AgentStatus.PUBLISHED, AgentStatus.FEATURED]:
                continue

            if category and agent.category != category:
                continue

            if tags and not any(t in agent.tags for t in tags):
                continue

            score = 0
            if query:
                query_lower = query.lower()
                if query_lower in agent.name.lower():
                    score += 10
                if query_lower in agent.description.lower():
                    score += 5
                if any(query_lower in tag.lower() for tag in agent.tags):
                    score += 3
                if score == 0:
                    continue

            results.append((agent, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in results[:top_k]]

    def rate_agent(self, agent_id: str, rating: int) -> bool:
        """评价 Agent"""
        if agent_id not in self._agents:
            return False
        if not 1 <= rating <= 5:
            return False

        agent = self._agents[agent_id]
        agent.ratings.append(rating)
        agent.updated_at = datetime.now().isoformat()
        return True

    def get_average_rating(self, agent_id: str) -> Optional[float]:
        """获取平均评分"""
        agent = self._agents.get(agent_id)
        if not agent or not agent.ratings:
            return None
        return sum(agent.ratings) / len(agent.ratings)

    def download_agent(self, agent_id: str) -> Optional[Dict]:
        """下载 Agent"""
        agent = self._agents.get(agent_id)
        if not agent:
            return None
        agent.downloads += 1
        return {
            "agent_id": agent.agent_id,
            "name": agent.name,
            "description": agent.description,
            "version": agent.version,
            "category": agent.category,
            "capabilities": agent.capabilities
        }

    def register_template(self, template_id: str, name: str, description: str,
                        category: str, config: Dict = None, skills: List[str] = None) -> str:
        """注册模板"""
        template = AgentTemplate(
            template_id=template_id,
            name=name,
            description=description,
            category=category,
            config=config or {},
            skills=skills or []
        )
        self._templates[template_id] = template
        return template_id

    def get_templates(self, category: str = None) -> List[AgentTemplate]:
        """获取模板列表"""
        if category:
            return [t for t in self._templates.values() if t.category == category]
        return list(self._templates.values())

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "total_agents": len(self._agents),
            "templates": len(self._templates),
            "categories": len(self.CATEGORIES)
        }


# 全局单例
agent_hub = AgentHub()
