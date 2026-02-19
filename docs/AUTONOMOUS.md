# 自主决策设计文档 (v3.2.0)

## 概述

v3.2.0 引入了自主决策能力，包括自动规划、自我反思和经验学习功能。

## 模块架构

```
Autonomous Decision
├── planning/
│   └── AutoPlanner          # 自动任务规划
└── reflection/
    ├── SelfReflector        # 自我反思
    ├── ExperienceLearner    # 经验学习
    └── ReflectionScheduler # 反思调度
```

## 核心特性

### 1. 自动规划 (Planning)

| 类 | 功能 | LLM 支持 |
|-----|------|---------|
| AutoPlanner | 目标分解、任务排序、执行管理 | ✓ |
| ExecutionPlan | 执行计划数据结构 | - |
| PlanTask | 任务数据结构 | - |

**规划方法**:
- `create_plan()` - 创建执行计划
- `get_next_task()` - 获取下一个可执行任务
- `execute_task()` - 执行单个任务

### 2. 自我反思 (Reflection)

| 类 | 功能 | LLM 支持 |
|-----|------|---------|
| SelfReflector | 对话总结、经验提取 | ✓ |
| ExperienceLearner | 交互学习、模式识别 | ✓ |
| ReflectionScheduler | 定时/事件触发反思 | - |

**反思流程**:
1. 分析对话历史
2. 提取关键信息
3. 生成洞察和改进建议
4. 记录到历史记录

### 3. 经验学习

```python
from reflection import ExperienceLearner

learner = ExperienceLearner(llm_client=llm_client)

# 从交互中学习
result = await learner.learn_from_interaction(
    interaction={"intent": "book_hotel", "params": {...}},
    outcome="success"
)

# 获取学习到的模式
patterns = learner.get_patterns("book_hotel")
knowledge = learner.get_knowledge("user_preferences")
```

## 使用示例

### 自动规划

```python
from planning import AutoPlanner, TaskPriority

planner = AutoPlanner(llm_client=llm_client)

# 创建计划
plan = await planner.create_plan(
    goal="规划北京三日游",
    context={"budget": 5000, "travelers": 2}
)

# 执行计划
while True:
    task = planner.get_next_task(plan)
    if not task:
        break
    planner.execute_task(plan, task.task_id)

# 查看状态
status = planner.get_plan_status(plan)
print(f"完成: {status['completed']}/{status['total_tasks']}")
```

### 自我反思

```python
from reflection import SelfReflector

reflector = SelfReflector(llm_client=llm_client)

# 进行反思
result = await reflector.reflect(conversation_history)

print(f"总结: {result.summary}")
print(f"洞察: {result.insights}")
print(f"改进: {result.improvements}")
print(f"置信度: {result.confidence}")

# 记录反思历史
reflector.add_to_history(result)
```

## 任务状态管理

```
PlanStatus:
├── PENDING      # 待执行
├── IN_PROGRESS  # 执行中
├── COMPLETED    # 已完成
├── FAILED       # 失败
└── PAUSED      # 暂停

TaskPriority:
├── HIGH    # 高优先级
├── MEDIUM  # 中优先级
└── LOW     # 低优先级
```

## 版本信息

- **版本**: v3.2.0
- **发布日期**: 2024
- **依赖**: LLM Client (必须，用于智能规划)
