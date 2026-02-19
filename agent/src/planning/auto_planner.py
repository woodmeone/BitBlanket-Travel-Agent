"""
自主规划模块

提供自动任务分解、长期目标规划和执行能力。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)


class PlanStatus(Enum):
    """计划状态"""
    PENDING = "pending"       # 待执行
    IN_PROGRESS = "in_progress"  # 执行中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 失败
    PAUSED = "paused"         # 暂停


class TaskPriority(Enum):
    """任务优先级"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class PlanTask:
    """计划任务"""
    task_id: str
    name: str
    description: str
    priority: TaskPriority = TaskPriority.MEDIUM
    status: PlanStatus = PlanStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    subtasks: List['PlanTask'] = field(default_factory=list)
    result: Any = None
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class ExecutionPlan:
    """执行计划"""
    plan_id: str
    goal: str
    tasks: List[PlanTask] = field(default_factory=list)
    status: PlanStatus = PlanStatus.PENDING
    current_task: Optional[str] = None
    created_at: str = ""
    context: Dict = field(default_factory=dict)


class AutoPlanner:
    """自动规划器

    特性：
    - 目标分解
    - 任务排序
    - 依赖管理
    - LLM 增强规划
    """

    def __init__(self, llm_client: Any = None):
        """
        初始化自动规划器

        Args:
            llm_client: 可选的 LLM 客户端，用于增强规划
        """
        self._llm_client = llm_client
        self._plans: Dict[str, ExecutionPlan] = {}
        logger.info("AutoPlanner initialized")

    def set_llm_client(self, llm_client):
        """设置 LLM 客户端"""
        self._llm_client = llm_client

    async def create_plan(
        self,
        goal: str,
        context: Dict = None
    ) -> ExecutionPlan:
        """创建执行计划

        Args:
            goal: 目标描述
            context: 上下文信息

        Returns:
            执行计划
        """
        plan_id = f"plan_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 如果有 LLM，使用 LLM 进行规划
        if self._llm_client:
            return await self._create_plan_with_llm(plan_id, goal, context)

        # 回退到规则规划
        return self._create_plan_with_rules(plan_id, goal, context)

    async def _create_plan_with_llm(
        self,
        plan_id: str,
        goal: str,
        context: Dict
    ) -> ExecutionPlan:
        """使用 LLM 创建计划

        Args:
            plan_id: 计划 ID
            goal: 目标
            context: 上下文

        Returns:
            执行计划
        """
        try:
            context_str = json.dumps(context or {}, ensure_ascii=False)

            system_prompt = """你是一个专业的旅行规划专家。根据用户的目标，将其分解为具体的任务步骤。

分解原则：
1. 每个任务应该是具体的、可执行的
2. 考虑任务之间的依赖关系
3. 按照合理的顺序排列
4. 识别关键决策点"""

            user_prompt = f"""用户目标：{goal}
上下文：{context_str}

请以 JSON 格式返回任务列表：
{{
    "tasks": [
        {{
            "task_id": "task_1",
            "name": "任务名称",
            "description": "任务描述",
            "priority": "high/medium/low",
            "dependencies": ["task_id 或空列表"]
        }}
    ]
}}

只返回 JSON。"""

            result = self._llm_client.chat([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ], temperature=0.5)

            if result.get("success"):
                content = result.get("content", "")
                try:
                    data = json.loads(content)
                    tasks = []
                    for t in data.get("tasks", []):
                        tasks.append(PlanTask(
                            task_id=t.get("task_id", ""),
                            name=t.get("name", ""),
                            description=t.get("description", ""),
                            priority=TaskPriority(t.get("priority", "medium")),
                            dependencies=t.get("dependencies", []),
                            created_at=datetime.now().isoformat()
                        ))

                    return ExecutionPlan(
                        plan_id=plan_id,
                        goal=goal,
                        tasks=tasks,
                        created_at=datetime.now().isoformat(),
                        context=context or {}
                    )
                except json.JSONDecodeError:
                    logger.warning("Failed to parse LLM plan response")

        except Exception as e:
            logger.warning(f"LLM planning failed: {e}")

        # LLM 失败，回退到规则
        return self._create_plan_with_rules(plan_id, goal, context)

    def _create_plan_with_rules(
        self,
        plan_id: str,
        goal: str,
        context: Dict
    ) -> ExecutionPlan:
        """使用规则创建计划

        Args:
            plan_id: 计划 ID
            goal: 目标
            context: 上下文

        Returns:
            执行计划
        """
        # 简单的规则分解
        tasks = []

        # 检测目标类型
        if "旅游" in goal or "旅行" in goal:
            tasks.append(PlanTask(
                task_id="task_1",
                name="确定目的地",
                description="确定旅行目的地",
                priority=TaskPriority.HIGH,
                created_at=datetime.now().isoformat()
            ))

            tasks.append(PlanTask(
                task_id="task_2",
                name="查询景点",
                description="查询目的地景点信息",
                priority=TaskPriority.MEDIUM,
                dependencies=["task_1"],
                created_at=datetime.now().isoformat()
            ))

            tasks.append(PlanTask(
                task_id="task_3",
                name="规划路线",
                description="规划旅行路线",
                priority=TaskPriority.MEDIUM,
                dependencies=["task_2"],
                created_at=datetime.now().isoformat()
            ))

            tasks.append(PlanTask(
                task_id="task_4",
                name="预算计算",
                description="计算旅行预算",
                priority=TaskPriority.LOW,
                dependencies=["task_3"],
                created_at=datetime.now().isoformat()
            ))

        return ExecutionPlan(
            plan_id=plan_id,
            goal=goal,
            tasks=tasks,
            created_at=datetime.now().isoformat(),
            context=context or {}
        )

    def get_next_task(self, plan: ExecutionPlan) -> Optional[PlanTask]:
        """获取下一个可执行的任务

        Args:
            plan: 执行计划

        Returns:
            下一个任务或 None
        """
        for task in plan.tasks:
            if task.status != PlanStatus.PENDING:
                continue

            # 检查依赖是否满足
            deps_met = all(
                self._get_task_status(plan, dep) == PlanStatus.COMPLETED
                for dep in task.dependencies
            )

            if deps_met:
                return task

        return None

    def _get_task_status(self, plan: ExecutionPlan, task_id: str) -> PlanStatus:
        """获取任务状态"""
        for task in plan.tasks:
            if task.task_id == task_id:
                return task.status
        return PlanStatus.PENDING

    def execute_task(
        self,
        plan: ExecutionPlan,
        task_id: str,
        executor: Any = None
    ) -> bool:
        """执行任务

        Args:
            plan: 执行计划
            task_id: 任务 ID
            executor: 执行函数

        Returns:
            是否成功
        """
        task = None
        for t in plan.tasks:
            if t.task_id == task_id:
                task = t
                break

        if not task:
            return False

        # 更新状态
        task.status = PlanStatus.IN_PROGRESS
        task.started_at = datetime.now().isoformat()

        # 执行任务
        if executor:
            try:
                result = executor(task)
                task.result = result
                task.status = PlanStatus.COMPLETED
                task.completed_at = datetime.now().isoformat()
                return True
            except Exception as e:
                logger.error(f"Task execution failed: {e}")
                task.status = PlanStatus.FAILED
                return False
        else:
            # 默认直接完成
            task.status = PlanStatus.COMPLETED
            task.completed_at = datetime.now().isoformat()
            return True

    def get_plan_status(self, plan: ExecutionPlan) -> Dict:
        """获取计划状态

        Args:
            plan: 执行计划

        Returns:
            状态信息
        """
        total = len(plan.tasks)
        completed = sum(1 for t in plan.tasks if t.status == PlanStatus.COMPLETED)
        failed = sum(1 for t in plan.tasks if t.status == PlanStatus.FAILED)

        return {
            "plan_id": plan.plan_id,
            "goal": plan.goal,
            "total_tasks": total,
            "completed": completed,
            "failed": failed,
            "progress": f"{completed}/{total}",
            "status": plan.status.value
        }


# 全局单例
auto_planner = AutoPlanner()
