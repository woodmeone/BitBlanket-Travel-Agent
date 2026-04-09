# 07. 高频面试题库与参考答法

这一篇直接给面试准备使用的高频问答库。

最推荐的用法很简单：

1. 先读 [06-interview-highlights-and-system-evolution.md](06-interview-highlights-and-system-evolution.md)。
2. 再用这一篇做口头快答。
3. 每题都尽量落回真实代码锚点。

## 问题 1：这个项目最准确的一句话定义是什么？

答案：

`moyuan-travel-agent` 不是普通聊天 Demo，而是把旅行约束输入变成可流式解释、可验证、可继续操作、可回放的旅行决策系统。

这句话最好不要改得太花，因为它已经覆盖了：

1. 流式过程事件。
2. 可靠性闭环。
3. 结构化结果交付。
4. session / memory / checkpoint。

## 问题 2：这个项目和普通聊天页最大的不同是什么？

答案：

普通聊天页通常到“模型回一段文本”就结束了。

这个项目多做了 5 层工程化：

1. SSE 推过程事件，不只是最终文本。
2. 前端消费 artifact，而不只是正文。
3. Backend 负责 session 和持久化边界，不只是代理。
4. Agent 是状态机，不是线性 prompt。
5. 有 benchmark、golden eval、quality gate。

## 问题 3：整条主链应该怎么讲？

答案：

最稳的讲法是：

```text
用户输入
  -> ChatArea / useChatRuntime
  -> chatClient.ts
  -> /api/chat/stream
  -> ChatService
  -> AgentRuntime
  -> RuntimeDriver
  -> runtime_flow
  -> builder / nodes
  -> SSE 回推
  -> chatStreamParser.ts
  -> MessageList / TravelPlanToolkit
```

如果面试官只要一条链，你就讲这条。

## 问题 4：为什么这里选 SSE，而不是一次性 JSON？

答案：

因为前端要消费的是事件流，而不是单个结果对象。

当前至少会收到：

1. `session_id`
2. `stage`
3. `reasoning_*`
4. `tool_*`
5. `plan_preview`
6. `subagent_*`
7. `artifact_patch`
8. `metadata`
9. `done`

所以一次性 JSON 不适合表达这条链。

## 问题 5：为什么也不是 WebSocket？

答案：

因为当前主需求是服务端单向持续推送。

SSE 的优势是：

1. 直接基于 HTTP。
2. 代理和基础设施兼容性更好。
3. 实现复杂度更低。
4. 对当前 `stage / metadata / answer` 场景已经够用。

只有在复杂双向实时协作成为主需求时，WebSocket 才更值得切。

## 问题 6：为什么前端要区分 `streamingMessage` 和最终 `messages`？

答案：

因为它们不是同一种生命周期。

- `streamingMessage`
  是运行中的临时态。
- `messages`
  是收口后的持久态。

这样拆开的好处是：

1. 避免 UI 抖动。
2. 避免 stop 后留下半条正式消息。
3. 方便把 `metadata / artifact / reasoning` 在完成时一次性合并。

代码锚点：

- [useChatRuntime.ts](../../frontend/src/components/chat-area/useChatRuntime.ts)

## 问题 7：为什么 `TravelPlanToolkit` 很值得讲？

答案：

因为它最能证明这不是普通聊天页。

它的价值在于：

1. 消费结构化 artifact，而不是只依赖长文本。
2. 把结果继续做成预算、对比、冲突、分享、继续 refine。
3. 把“回答”升级成“可操作结果”。

代码锚点：

- [TravelPlanToolkit.tsx](../../frontend/src/components/TravelPlanToolkit.tsx)
- [useTravelPlanToolkitActions.ts](../../frontend/src/components/travel-plan-toolkit/useTravelPlanToolkitActions.ts)

## 问题 8：为什么 Backend 要做 `route -> service -> repository -> persistence` 分层？

答案：

因为这四层分别回答：

1. 请求怎么进。
2. 业务怎么编排。
3. 业务对象怎么读写。
4. 底层怎么存。

这能保证：

1. route 足够薄。
2. service 负责流程。
3. file / postgres 可替换。
4. session 和 chat 边界不容易混。

## 问题 9：`ChatService` 和 `SessionService` 为什么要分开？

答案：

因为聊天编排和会话生命周期不是一件事。

- `ChatService`
  负责一轮聊天运行。
- `SessionService`
  负责 session facade。
- `SessionLifecycleService`
  负责 session CRUD 和 memory 副作用。

这能避免 session 接口被流式逻辑污染。

## 问题 10：为什么当前项目同时保留 `file / postgres` 两条持久化基线？

答案：

因为它们服务不同场景：

1. file baseline 适合本地开发、轻量环境、快速启动。
2. postgres baseline 适合正式部署、共享环境和更稳定的数据管理。

更重要的是：

这说明系统从一开始就在为“存储可演进”做准备。

## 问题 11：为什么 Backend 不直接调用 LangGraph，而是通过 `AgentRuntime`？

答案：

因为应用层需要稳定的执行 contract。

`AgentRuntime` 的作用是：

1. 隔离 graph 细节。
2. 统一 stream、preview、tool diagnostics 接口。
3. 附加 subagent、artifact patch、execution receipt 等运行态能力。

所以应用层依赖的是 runtime seam，而不是具体图实现。

## 问题 12：为什么这里的 Agent 一定要做成状态机？

答案：

因为系统里存在：

1. 路由分叉。
2. 执行回环。
3. 验证回跳。
4. 终态自检。

这类流程如果用线性链表达，很快就会变成难维护的 if/else 串。

代码锚点：

- [builder.py](../../agent/travel_agent/graph/builder.py)
- [nodes.py](../../agent/travel_agent/graph/nodes.py)

## 问题 13：`direct / react / plan` 三种路径分别解决什么问题？

答案：

- `direct`
  简单问题，尽快给答复。
- `react`
  需要执行型链路，但更偏直接执行。
- `plan`
  显式先产出结构化计划预览。

当前实现更准确的说法是：

系统先判断要不要进入规划执行链路，再依据 `chat_mode` 走 `plan` 或 `react`。

## 问题 14：`verify` 和 `self_check` 的区别是什么？

答案：

这是高频追问题。

- `verify`
  看工具证据够不够，是否需要 retry。
- `self_check`
  看最终答案还有没有明显问题。

一句话记忆：

`verify` 面向证据，`self_check` 面向交付。

## 问题 15：`_meta / stale / fallback / refresh` 为什么重要？

答案：

因为工具结果不是天然可信的。

这几个机制分别在解决：

1. 来源和诊断可解释。
2. 数据新鲜度风险。
3. 主路径失败时的降级。
4. 结果陈旧时的刷新重试。

面试里把这一层讲出来，说明你理解的是“工具可靠性”，不是“工具调用次数”。

## 问题 16：`session / memory / checkpoint` 三者怎么区分？

答案：

按时间尺度记就行：

1. `session`
   当前产品会话和消息历史。
2. `memory`
   长期偏好、摘要、跨轮上下文。
3. `checkpoint`
   图执行恢复点和 replay 依据。

再补一句：

session 偏产品，memory 偏语义，checkpoint 偏执行。

## 问题 17：当前项目到底算不算多 Agent？

答案：

比较准确的说法是：

它已经具备 supervisor runtime、skill registry 和 subagent registry，但核心执行主链仍主要落在当前主图上。

所以更适合讲成：

这是一个正在向多 Agent 架构演进的 supervisor runtime，而不是完全解耦的多 Agent 平台。

代码锚点：

- [agent_runtime.py](../../agent/travel_agent/runtime/agent_runtime.py)
- [skills/registry.py](../../agent/travel_agent/skills/registry.py)
- [subagents/registry.py](../../agent/travel_agent/subagents/registry.py)

## 问题 18：这个项目里最容易被忽视，但很值得讲的一个点是什么？

答案：

是 artifact-first。

很多人会把注意力都放在“模型生成文本”，但当前项目更重要的是：

1. `plan_preview` 带 artifact。
2. 流式过程中会不断收到 `artifact_patch`。
3. `done` 和 `metadata` 里也能带最终 artifact。
4. 前端优先消费结构化结果。

这决定了系统交付的是“结果对象”，不是“结果文本”。

## 问题 19：如果面试官问“你们怎么做质量回归”，推荐怎么答？

答案：

推荐答法：

我们把质量回归分成分层验证和趋势验证两部分。分层上，SSE 契约由 `test_chat_stream_local.py` 保护，关键 API 和健康接口由 `test_api_smoke_local.py` 等 smoke 测试保护，runtime backup/restore/prune 和 checkpoint 维护由 `test_runtime_data_lifecycle_unit.py` 保护。趋势上，再通过 benchmark、golden eval 和 `agent_quality_gate.py` 检查成功率、hallucination rate、fallback steps 和相对 baseline 的回归幅度。这样不是只看“能不能跑”，而是看“行为有没有变差”。

## 问题 20：如果面试官问“出了问题你怎么排查”，推荐怎么答？

答案：

最稳的答法是按层排：

1. 先看症状落在哪层。
2. 再看请求或 SSE 事件有没有正确流动。
3. 再看状态有没有被正确消费或持久化。
4. 再看测试有没有覆盖这个边界。
5. 最后才怀疑 prompt 或模型。

这种答法比“我先看看日志”更强，因为它体现你知道系统边界。

## 问题 21：如果要加一个新字段，为什么通常不是小改动？

答案：

因为字段是契约的一部分。

新增字段通常会波及：

1. API schema。
2. service 编排。
3. repository 持久化。
4. SSE 事件或 metadata。
5. 前端状态消费。
6. 测试断言。

所以“加字段”在这种项目里往往是跨层联动。

## 问题 22：如果要加一个新工具，最推荐怎么讲改动路径？

答案：

最稳的说法是：

先把工具 contract 接进 tool registry，再让规划和执行层知道何时使用它，再看是否需要 `_meta`、freshness 和 verify 规则，最后补前后端相关展示和测试。如果这个工具会影响计划预览或结构化交付，还要考虑 artifact patch 和 `TravelPlanToolkit` 消费。

这能体现你理解的不是“注册一个函数”，而是“把工具接进完整系统”。

## 问题 23：如果要继续演进这个系统，你最先会补哪三类能力？

答案：

最推荐说这三类：

1. 更完整的 artifact 交付与分享能力。
2. 更强的 runtime 观测、回放和失败聚类。
3. 更成熟的 supervisor / subagent 协作与选择策略。

这样回答既贴近当前代码，也不会空泛。

## 问题 24：如果让我用一句话总结这个项目最能证明什么能力，我该怎么说？

答案：

这个项目最能证明的不是“我会调一个大模型接口”，而是“我能把一个 AI 场景做成有分层、有协议、有状态边界、有可靠性设计、有质量门禁的完整工程系统”。
