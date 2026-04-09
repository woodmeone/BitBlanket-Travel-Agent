# 04. Agent 核心、Tools、Memory、Checkpoint 面试问答

这一篇只讲 Agent 层最值得面试时讲清楚的问题。

## 问题 1：这个项目里的 Agent 为什么不是普通的“prompt + tools”？

答案：

因为它解决的不是一次性问答，而是带约束、带证据、带验证的旅行决策问题。

当前 Agent 显式包含：

1. 状态机。
2. 工具执行。
3. 证据校验。
4. 自检闭环。
5. memory 注入。
6. checkpoint 恢复。
7. artifact-first 输出。

所以更准确的说法是：

这是一个有执行状态、有验证回环、有恢复能力的 Agent runtime。

## 问题 2：为什么 Backend 不直接调用 `builder.py`，而是先走 `AgentRuntime`？

答案：

因为 [AgentRuntime](../../agent/travel_agent/runtime/agent_runtime.py) 是面向应用层的稳定执行面。

它的价值有 3 个：

1. 把 graph 细节藏在 runtime seam 后面。
2. 把 skills、subagents、artifact patch、execution receipt 一起挂到输出上。
3. 让 Backend 依赖稳定 contract，而不是耦合具体图实现。

这也是当前代码里非常值得讲的一点：

Backend 接的是 runtime seam，不是直接接 LangGraph 内核。

## 问题 3：当前 Agent 的真实主链应该怎么讲？

答案：

最稳的讲法是：

```text
ChatService
  -> AgentRuntime.stream_with_memory(...)
  -> DefaultRuntimeDriver.stream_with_memory(...)
  -> stream_supervisor_run(...)
  -> build_supervisor_streaming_source(...)
  -> build_memory_graph_source(...)
  -> build_travel_agent(...)
  -> LangGraph nodes
  -> runtime events
```

对应代码锚点：

- [agent_runtime.py](../../agent/travel_agent/runtime/agent_runtime.py)
- [runtime_driver.py](../../agent/travel_agent/runtime/runtime_driver.py)
- [runtime_flow.py](../../agent/travel_agent/graph/runtime_flow.py)
- [runtime_sources.py](../../agent/travel_agent/runtime_sources.py)

## 问题 4：为什么这里必须是状态机，而不是线性链？

答案：

因为旅行规划这种问题天然有分叉和回环。

当前图里最关键的结构是：

1. `strategy` 后会路由到 `direct` 或“需要规划执行”的分支。
2. `execute` 可能循环多轮。
3. `verify` 失败时会回跳 `execute`。
4. `answer` 之后还有 `self_check`。

只要系统里出现“分支 + 重试 + 回跳 + 终态检查”，状态机就比线性链更合适。

## 问题 5：`builder.py` 最值得记住什么？

答案：

[builder.py](../../agent/travel_agent/graph/builder.py) 最重要的不是某个函数细节，而是它把图结构显式写出来了。

最值得记住的是这些节点和边：

1. `intent -> strategy`
2. `strategy -> plan / react / direct_answer`
3. `plan / react -> execute`
4. `execute -> execute / verify`
5. `verify -> execute / answer`
6. `answer / direct_answer -> self_check -> END`

面试里如果能把这张图讲顺，说明你不是只会背术语。

## 问题 6：`direct / react / plan` 在当前实现里到底怎么理解？

答案：

最稳的说法不是把它们讲成 3 个完全独立系统，而是 3 种策略入口。

- `direct`
  问题简单，直接回答，不走重工具链。
- `plan`
  前端显式选择计划模式，要先给结构化预览。
- `react`
  也属于需要规划和执行的请求，但更偏直接执行链，而不是只展示计划。

从 [nodes.py](../../agent/travel_agent/graph/nodes.py) 和 [builder.py](../../agent/travel_agent/graph/builder.py) 看，当前实现更准确的说法是：

系统先判断“要不要走计划/执行型链路”；如果需要，再根据 `chat_mode` 走 `plan` 还是 `react` 分支。

## 问题 7：`intent_node` 和 `strategy_node` 分别在解决什么问题？

答案：

- `intent_node`
  解决“用户大概在问什么”。
- `strategy_node`
  解决“这个问题应该怎么处理”。

也就是：

1. 先做语义理解。
2. 再做执行策略选择。

这是很多 Agent 面试里容易答浅的地方。很多人只会说“先识别意图”，但真正工程上更关键的是“识别完后怎么决定路径”。

## 问题 8：为什么 `execute -> verify -> execute` 这个回环很重要？

答案：

因为工具跑过，不等于证据够了。

当前实现里：

1. `execute_node(...)` 负责真正调工具、聚合结果、统计执行状态。
2. `verify_node(...)` 负责判断证据是否充分、是否陈旧、是否需要 retry。
3. `verify_decision(...)` 决定回跳 `execute` 还是进入 `answer`。

这比“工具一跑完就直接生成答案”更像真实工程系统。

## 问题 9：`execute_node` 最值得讲的工程点是什么？

答案：

最值得讲的是它不只是“for 循环调工具”。

从 [nodes.py](../../agent/travel_agent/graph/nodes.py) 可以看到它还处理了：

1. 依赖步骤。
2. 执行轮次。
3. 并行度。
4. budget。
5. 失败和 blocked 状态。
6. execution trace。
7. refresh retry。
8. 早停条件。

这说明当前执行层已经有一套比较完整的 orchestration 语义。

## 问题 10：`verify` 和 `self_check` 的区别是什么？

答案：

这是最容易被混淆的一组词。

- `verify`
  检查的是执行证据够不够，重点在工具结果。
- `self_check`
  检查的是最终答案成稿后还有没有明显质量问题。

所以：

1. `verify` 更像证据审查。
2. `self_check` 更像交付前自检。

面试里如果把这两个混成一件事，通常会被继续追问。

## 问题 11：工具层为什么要强调 `_meta / stale / fallback / refresh`？

答案：

因为工具结果不是天然可靠的。

这几个词分别在保护不同风险：

| 术语 | 工程意义 |
| --- | --- |
| `_meta` | 给工具结果附带来源、状态、新鲜度、诊断信息 |
| stale | 结果可能过期 |
| fallback | 主路径失败时的降级结果 |
| refresh | 对陈旧结果做刷新重试 |

面试里可以直接把这点讲成：

这个项目不是“调用工具”，而是“管理工具证据质量”。

## 问题 12：memory、session、checkpoint 三者到底怎么区分？

答案：

最稳的记法是按时间尺度区分：

| 概念 | 主要作用 |
| --- | --- |
| session | 当前产品会话和消息历史 |
| memory | 长期偏好、摘要、跨轮上下文 |
| checkpoint | 图运行恢复点和 replay 依据 |

如果要再补一句：

session 偏产品层，memory 偏语义层，checkpoint 偏执行层。

## 问题 13：memory 在当前实现里是怎么进入主链的？

答案：

memory 不是在 answer 阶段临时拼进去的，而是一开始就进入运行源。

在 [runtime_sources.py](../../agent/travel_agent/runtime_sources.py) 里：

1. `build_memory_graph_source(...)` 会构造 memory-aware 初始状态。
2. `build_memory_plan_preview_source(...)` 会给 plan preview 注入同样的 memory 语义。
3. [memory_integration.py](../../agent/travel_agent/graph/memory_integration.py) 负责摘要、画像、历史写入与读取。

所以 memory 是 runtime 入口的一部分，不是后处理插件。

## 问题 14：checkpoint 在当前实现里为什么值得讲？

答案：

因为它不是一个写死的 SQLite 细节，而是已经抽象成 backend 可切换的工厂。

在 [runtime_sources.py](../../agent/travel_agent/runtime_sources.py) 里：

1. `resolve_checkpointer_config(...)`
   统一解析 sqlite / postgres 配置。
2. `create_checkpointer(...)`
   构造具体 saver。
3. `create_default_checkpointer()`
   做缓存和 fallback。

这说明 checkpoint 已经从“本地开发辅助”升级成了运行时基础设施。

## 问题 15：当前 checkpointer 为什么要支持 `sqlite / postgres` 双基线？

答案：

因为两者服务的环境不同：

1. sqlite 适合本地开发和轻量环境。
2. postgres 更适合共享环境、持久化和统一运维。

更重要的是，双基线说明系统设计时已经把恢复能力当成正式能力，而不是临时 debug 技巧。

代码锚点：

- [runtime_sources.py](../../agent/travel_agent/runtime_sources.py)
- [persistent_checkpointer.py](../../agent/travel_agent/graph/persistent_checkpointer.py)

## 问题 16：当前为什么还要引入 `SkillRegistry` 和 `SubagentRegistry`？

答案：

因为系统在向 supervisor + subagent 架构演进，但又不想一次性把核心主链彻底打散。

- [skills/registry.py](../../agent/travel_agent/skills/registry.py)
  负责 skill contract。
- [subagents/registry.py](../../agent/travel_agent/subagents/registry.py)
  负责 subagent 与 skills/tool/stage 的映射。
- [agent_runtime.py](../../agent/travel_agent/runtime/agent_runtime.py)
  会在 runtime 事件里补充 subagent 视角和 artifact patch。

所以当前更准确的说法是：

这不是完全解耦的多 Agent 平台，而是一个已经具备 subagent registry 的 supervisor runtime。

## 问题 17：为什么 `AgentRuntime` 还要负责 artifact patch 和 execution receipt？

答案：

因为这个系统最终交付的不是一段文字，而是结构化结果和可解释执行记录。

在 [agent_runtime.py](../../agent/travel_agent/runtime/agent_runtime.py) 里可以看到：

1. `done` 事件会被补上 `artifact`。
2. subagent 会额外产出 `artifact_patch`。
3. 最终还会生成 `execution_receipt`。

这和前端的 `artifact-first` 是一条链上的设计，不是孤立实现。

## 问题 18：如果面试官问“你们这个 Agent 最大的工程价值是什么”，怎么答？

答案：

最稳的答法是：

它把大模型调用从“黑盒输出”提升成了“可路由、可验证、可恢复、可结构化交付”的运行系统。具体上，应用层通过 `AgentRuntime` 接稳定 seam，图内部用 LangGraph 表达状态机，执行阶段有工具证据链和 verify 回环，长期上下文由 memory 管理，运行恢复由 checkpoint 支撑，最终结果还能产出 artifact 和 execution receipt，方便前端继续做产品化消费。

## 问题 19：如果我要排查 Agent 层问题，最推荐按什么顺序？

答案：

最推荐顺序是：

1. 先看 runtime seam 是否正常产出事件。
2. 再看 `runtime_sources.py` 是否构造了正确的 source。
3. 再看 `builder.py` 的图边和 thread config。
4. 再看 `nodes.py` 中具体是 `intent / strategy / execute / verify / answer` 哪一步异常。
5. 最后再看 tool、memory、checkpoint 配置。

不要一开始就盲改 prompt。

## 问题 20：如果让我用 1 分钟讲清楚 Agent 这层，我该怎么讲？

答案：

我会这样讲：

这个项目的 Agent 不是普通的 prompt 链，而是一个通过 `AgentRuntime` 对外暴露稳定 seam 的状态机系统。内部用 LangGraph 把 `intent -> strategy -> execute -> verify -> answer -> self_check` 组织成可分叉、可回环的执行图，工具结果会经过 `_meta`、stale、fallback、refresh 这些可靠性机制，长期偏好由 memory 管理，执行恢复由 sqlite 或 postgres checkpointer 管理，最终还会产出 artifact patch 和 execution receipt，方便前端做结构化消费和问题回放。
