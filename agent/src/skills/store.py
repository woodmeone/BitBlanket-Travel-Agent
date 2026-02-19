"""
技能库管理

提供技能注册、发现、编排和复用功能。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum
import logging
import json

logger = logging.getLogger(__name__)


class SkillCategory(Enum):
    """技能分类"""
    TRAVEL = "travel"           # 旅游相关
    RECOMMENDATION = "recommendation"  # 推荐
    PLANNING = "planning"       # 规划
    QUERY = "query"            # 查询
    ANALYSIS = "analysis"       # 分析
    UTILITY = "utility"        # 工具类
    CUSTOM = "custom"          # 自定义


class SkillScope(Enum):
    """技能作用域"""
    GLOBAL = "global"          # 全局可用
    SESSION = "session"        # 会话级
    ONETIME = "onetime"        # 一次性


@dataclass
class SkillMetadata:
    """技能元数据"""
    skill_id: str
    name: str
    description: str
    category: SkillCategory
    version: str = "1.0.0"
    author: str = ""
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    input_schema: Dict = field(default_factory=dict)
    output_schema: Dict = field(default_factory=dict)
    examples: List[str] = field(default_factory=list)


@dataclass
class Skill:
    """技能实例"""
    metadata: SkillMetadata
    handler: Callable
    scope: SkillScope = SkillScope.GLOBAL


@dataclass
class SkillExecutionResult:
    """技能执行结果"""
    skill_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    duration: float = 0.0


class SkillStore:
    """技能库

    特性：
    - 技能注册和管理
    - 技能发现和搜索
    - 技能依赖管理
    - 技能编排
    - 技能执行
    """

    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._skill_chains: Dict[str, List[str]] = {}  # 技能链
        self._init_builtin_skills()
        logger.info("SkillStore initialized")

    def _init_builtin_skills(self):
        """初始化内置技能"""
        # 城市推荐技能
        self.register_skill(
            skill_id="city_recommend",
            name="城市推荐",
            description="根据用户偏好推荐旅游城市",
            category=SkillCategory.RECOMMENDATION,
            handler=self._default_handler,
            tags=["推荐", "城市", "目的地"]
        )

        # 景点查询技能
        self.register_skill(
            skill_id="attraction_query",
            name="景点查询",
            description="查询景点信息和门票",
            category=SkillCategory.QUERY,
            handler=self._default_handler,
            tags=["景点", "查询", "门票"]
        )

        # 路线规划技能
        self.register_skill(
            skill_id="route_plan",
            name="路线规划",
            description="规划旅行路线和日程",
            category=SkillCategory.PLANNING,
            handler=self._default_handler,
            tags=["规划", "路线", "日程"]
        )

        # 预算计算技能
        self.register_skill(
            skill_id="budget_calc",
            name="预算计算",
            description="计算旅行预算和费用",
            category=SkillCategory.ANALYSIS,
            handler=self._default_handler,
            tags=["预算", "费用", "计算"]
        )

        # 美食推荐技能
        self.register_skill(
            skill_id="food_recommend",
            name="美食推荐",
            description="推荐当地美食餐厅",
            category=SkillCategory.RECOMMENDATION,
            handler=self._default_handler,
            tags=["美食", "餐厅", "推荐"]
        )

    def _default_handler(self, *args, **kwargs):
        """默认处理器"""
        return {"status": "ok", "message": "Skill executed"}

    def register_skill(
        self,
        skill_id: str,
        name: str,
        description: str,
        category: SkillCategory,
        handler: Callable,
        tags: List[str] = None,
        version: str = "1.0.0",
        author: str = "",
        dependencies: List[str] = None,
        scope: SkillScope = SkillScope.GLOBAL,
        **kwargs
    ) -> str:
        """注册技能

        Args:
            skill_id: 技能 ID
            name: 技能名称
            description: 技能描述
            category: 技能分类
            handler: 处理函数
            tags: 标签
            version: 版本
            author: 作者
            dependencies: 依赖技能
            scope: 作用域

        Returns:
            skill_id
        """
        if skill_id in self._skills:
            logger.warning(f"Skill {skill_id} already registered, replacing")

        # 处理 category 参数
        if isinstance(category, str):
            try:
                category = SkillCategory(category)
            except ValueError:
                category = SkillCategory.CUSTOM

        metadata = SkillMetadata(
            skill_id=skill_id,
            name=name,
            description=description,
            category=category,
            version=version,
            author=author,
            tags=tags or [],
            dependencies=dependencies or [],
            input_schema=kwargs.get("input_schema", {}),
            output_schema=kwargs.get("output_schema", {})
        )

        self._skills[skill_id] = Skill(
            metadata=metadata,
            handler=handler,
            scope=scope
        )

        logger.info(f"Registered skill: {skill_id}")
        return skill_id

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """获取技能

        Args:
            skill_id: 技能 ID

        Returns:
            技能或 None
        """
        return self._skills.get(skill_id)

    def execute_skill(
        self,
        skill_id: str,
        *args,
        **kwargs
    ) -> SkillExecutionResult:
        """执行技能

        Args:
            skill_id: 技能 ID
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            执行结果
        """
        start_time = datetime.now()

        skill = self._skills.get(skill_id)
        if not skill:
            return SkillExecutionResult(
                skill_id=skill_id,
                success=False,
                error=f"Skill {skill_id} not found"
            )

        try:
            # 检查依赖
            for dep in skill.metadata.dependencies:
                if dep not in self._skills:
                    return SkillExecutionResult(
                        skill_id=skill_id,
                        success=False,
                        error=f"Dependency {dep} not found"
                    )

            # 执行技能
            result = skill.handler(*args, **kwargs)

            duration = (datetime.now() - start_time).total_seconds()

            return SkillExecutionResult(
                skill_id=skill_id,
                success=True,
                result=result,
                duration=duration
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"Skill execution error: {e}")
            return SkillExecutionResult(
                skill_id=skill_id,
                success=False,
                error=str(e),
                duration=duration
            )

    def discover_skills(
        self,
        query: str = "",
        category: SkillCategory = None,
        tags: List[str] = None,
        top_k: int = 10
    ) -> List[SkillMetadata]:
        """发现技能

        Args:
            query: 搜索关键词
            category: 分类过滤
            tags: 标签过滤
            top_k: 返回数量

        Returns:
            匹配的技能列表
        """
        results = []

        for skill in self._skills.values():
            metadata = skill.metadata

            # 分类过滤
            if category and metadata.category != category:
                continue

            # 标签过滤
            if tags and not any(t in metadata.tags for t in tags):
                continue

            # 关键词搜索
            score = 0
            if query:
                query_lower = query.lower()
                if query_lower in metadata.name.lower():
                    score += 10
                if query_lower in metadata.description.lower():
                    score += 5
                if any(query_lower in tag.lower() for tag in metadata.tags):
                    score += 3

                if score == 0:
                    continue

            results.append((metadata, score))

        # 排序
        results.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in results[:top_k]]

    def create_skill_chain(
        self,
        chain_id: str,
        skill_ids: List[str]
    ) -> bool:
        """创建技能链

        Args:
            chain_id: 技能链 ID
            skill_ids: 技能 ID 列表

        Returns:
            是否成功
        """
        # 验证所有技能存在
        for skill_id in skill_ids:
            if skill_id not in self._skills:
                logger.warning(f"Skill {skill_id} not found in chain")
                return False

        self._skill_chains[chain_id] = skill_ids
        logger.info(f"Created skill chain: {chain_id}")
        return True

    def execute_chain(
        self,
        chain_id: str,
        initial_input: Any,
        context: Dict = None
    ) -> List[SkillExecutionResult]:
        """执行技能链

        Args:
            chain_id: 技能链 ID
            initial_input: 初始输入
            context: 上下文

        Returns:
            执行结果列表
        """
        if chain_id not in self._skill_chains:
            logger.warning(f"Skill chain {chain_id} not found")
            return []

        results = []
        current_input = initial_input

        for skill_id in self._skill_chains[chain_id]:
            result = self.execute_skill(skill_id, current_input, context=context)
            results.append(result)

            if not result.success:
                logger.warning(f"Chain execution failed at {skill_id}")
                break

            # 将结果传递给下一个技能
            current_input = result.result

        return results

    def get_skills_by_category(self, category: SkillCategory) -> List[SkillMetadata]:
        """按分类获取技能

        Args:
            category: 技能分类

        Returns:
            技能列表
        """
        return [
            s.metadata for s in self._skills.values()
            if s.metadata.category == category
        ]

    def list_skills(self) -> List[SkillMetadata]:
        """列出所有技能

        Returns:
            技能列表
        """
        return [s.metadata for s in self._skills.values()]

    def get_stats(self) -> Dict:
        """获取统计信息"""
        category_count = {}
        for skill in self._skills.values():
            cat = skill.metadata.category.value
            category_count[cat] = category_count.get(cat, 0) + 1

        return {
            "total_skills": len(self._skills),
            "by_category": category_count,
            "skill_chains": len(self._skill_chains)
        }


# 全局单例
skill_store = SkillStore()
