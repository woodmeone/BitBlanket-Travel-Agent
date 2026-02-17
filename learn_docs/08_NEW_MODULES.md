# 新模块学习指南

本文档帮助你快速理解和学习新增加的模块。

---

## 工具生态 (v2.8.0)

### 学习路径

```
1. tools/registry.py    → 理解工具注册机制
2. tools/learning.py    → 理解工具学习
3. tools/plugin.py      → 理解插件系统
```

### 核心概念

#### ToolRegistry - 工具注册中心

```python
from tools.registry import tool_registry, ToolCategory

# 注册工具
tool_registry.register(
    tool_id="weather",
    name="天气查询",
    description="查询目的地天气",
    handler=weather_function,
    category=ToolCategory.INFORMATION
)

# 发现工具
tools = tool_registry.discover("天气")

# 列出工具
all_tools = tool_registry.list_tools(category=ToolCategory.SEARCH)
```

#### ToolLearning - 工具学习

```python
from tools.learning import tool_learning

# 记录使用
tool_learning.record_usage(
    tool_id="search",
    success=True,
    context={"query": "北京景点"},
    user_id="user123"
)

# 推荐工具
recommendations = tool_learning.recommend_tools(
    context={"query": "酒店推荐"},
    user_id="user123",
    top_k=3
)
```

#### PluginSystem - 插件系统

```python
from tools.plugin import plugin_manager

# 加载插件
plugin = plugin_manager.load_plugin("plugins/weather.py")

# 注册钩子
plugin_manager.register_hook("before_tool_call", my_hook)
```

---

## 对话增强 (v2.9.0)

### 学习路径

```
1. core/dialogue_policy.py    → 理解对话策略
2. memory/context_tracker.py  → 理解上下文追踪
3. reasoner/entity_linker.py   → 理解实体链接
```

### 核心概念

#### DialoguePolicy - 对话策略

```python
from core.dialogue_policy import dialogue_policy, DialogueAction

# 获取对话上下文
context = dialogue_policy.get_context("session_123")

# 选择对话动作
action = dialogue_policy.select_action(
    context=context,
    intent="plan_trip",
    entities={"city": "北京"}
)

if action == DialogueAction.CLARIFY:
    # 需要澄清
    clarifications = dialogue_policy.should_clarify("plan_trip", entities)
```

#### ContextTracker - 上下文追踪

```python
from memory.context_tracker import context_tracker

# 追踪实体
entity_id = context_tracker.track_entity(
    session_id="session_123",
    entity_type="city",
    value="北京"
)

# 追踪多个实体
context_tracker.track_entities_from_ner(
    session_id="session_123",
    entities={"city": "北京", "date": "春节"}
)

# 获取活跃实体
active = context_tracker.get_active_entities(
    session_id="session_123",
    max_turns=5
)
```

#### EntityLinker - 实体链接

```python
from reasoner.entity_linker import entity_linker

# 添加实体到知识库
entity_linker.add_entity(
    entity_id="beijing_001",
    name="北京",
    entity_type="city",
    aliases=["京城", "北平"],
    attributes={"population": 21000000}
)

# 链接实体
results = entity_linker.link("去北京旅游", entity_type="city")

# 搜索实体
candidates = entity_linker.search("北京", entity_type="city")
```

---

## 模块关系图

```
                    TravelAgent
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   Memory           Core             Tools
        │                │                │
   manager ←──── context_tracker → dialogue_policy
        │
   orchestrator
        │
   importance_scorer
   eviction_manager
   summarizer
   ...

Tools System:
   registry ←→ learning ←→ plugin
```

---

## 快速入门

### 1. 注册新工具

```python
from tools.registry import tool_registry, ToolCategory

def my_tool(query):
    return {"result": "..."}

tool_registry.register(
    tool_id="my_tool",
    name="我的工具",
    description="这是一个测试工具",
    handler=my_tool,
    category=ToolCategory.CUSTOM
)
```

### 2. 使用对话策略

```python
# 在 process 中集成
context = dialogue_policy.get_context(session_id)
action = dialogue_policy.select_action(context, intent, entities)

if action == DialogueAction.CLARIFY:
    return {"clarify": "请提供更多信息"}
```

### 3. 追踪用户意图

```python
# 追踪实体
entities = extract_entities(user_input)
context_tracker.track_entities_from_ner(session_id, entities)

# 在下一轮使用
active = context_tracker.get_active_entities(session_id)
```

---

## 常见问题

### Q: 如何选择使用哪个模块?

- 需要动态管理工具 → 使用 `ToolRegistry`
- 需要学习用户偏好 → 使用 `ToolLearning`
- 需要插件扩展 → 使用 `PluginSystem`
- 需要对话策略 → 使用 `DialoguePolicy`
- 需要跨轮次记忆 → 使用 `ContextTracker`
- 需要实体消歧 → 使用 `EntityLinker`

### Q: 模块之间的依赖?

```
DialoguePolicy → ContextTracker → MemoryManager
EntityLinker → ContextTracker
ToolLearning → ToolRegistry
```

---

## 相关文档

- [工具生态设计](../docs/TOOL_ECOSYSTEM_v2.8.md)
- [对话增强设计](../docs/DIALOGUE_ENHANCEMENT_v2.9.md)
- [演进路线图](../docs/ROADMAP.md)
