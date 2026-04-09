# 06. 面试速通、追问与系统演进问答

这一篇专门解决三件事：

1. 怎么用 30 秒到 5 分钟讲清这个项目。
2. 面试官最常追问什么，推荐怎么答。
3. 如果继续演进系统，最合理的下一步是什么。

## 问题 1：如果面试官只给我 30 秒，我该怎么介绍这个项目？

答案：

可以直接用这一版：

`moyuan-travel-agent` 不是普通聊天 Demo，而是把旅行约束输入变成可流式解释、可验证、可继续操作、可回放的旅行决策系统。前端负责 SSE 消费和结构化结果产品化，Backend 负责 `/api/chat/stream`、session 和持久化边界，Agent 负责状态机、工具执行、验证、自检、memory 和 checkpoint。

如果只能记一句，就记这句。

## 问题 2：如果面试官愿意听 2 分钟，我该怎么讲？

答案：

可以直接用这一版：

这个项目的目标不是生成一段旅游建议，而是把预算、天数、偏好、路线约束变成一个可解释的旅行决策过程。系统拆成三层：前端用 Next.js 负责输入、SSE 消费和 `TravelPlanToolkit` 结果产品化；Backend 用 FastAPI 提供 `/api/chat/stream`、session 和健康检查等接口，负责请求上下文、SSE 编排和持久化边界；Agent 层通过 `AgentRuntime` 和 LangGraph 把 `intent -> strategy -> execute -> verify -> answer -> self_check` 组织成状态机。之所以选 SSE，是因为系统不仅要返回最终文本，还要实时推送 `stage`、`tool`、`plan_preview`、`artifact_patch`、`metadata` 和 `done`。为了让结果更可靠，系统还补了 `_meta`、stale / fallback / refresh、memory、checkpoint、benchmark、golden eval 和 quality gate。

## 问题 3：如果面试官继续追问 5 分钟，最推荐按什么顺序展开？

答案：

最稳的顺序是：

1. 先讲业务目标。
2. 再讲 `frontend / backend / agent` 三层分工。
3. 再讲一条真实聊天主链。
4. 再讲为什么要 SSE、为什么要状态机、为什么要 artifact-first。
5. 最后讲可靠性和演进方向。

这样讲的好处是：

你先让对方知道这不是 demo，再把技术取舍放回真实业务约束里。

## 问题 4：这个项目最值得面试时强调的 5 个亮点是什么？

答案：

最值得强调的是这 5 个：

1. 不是普通聊天页，而是旅行决策系统。
2. SSE 不只推 token，还推过程事件和结构化补充信息。
3. 前端不是只展示文本，而是 `artifact-first` 的结果消费层。
4. Backend 分层清楚，能承接 session 和 `file / postgres` 双基线。
5. Agent 有 runtime seam、状态机、验证回环、memory 和 checkpoint。

如果还想再补两点：

1. 已经有 skill / subagent registry，具备 supervisor 演进方向。
2. 有 benchmark、golden eval、quality gate，不只是手工联调。

## 问题 5：如果面试官问“这个项目为什么有工程深度”，推荐怎么答？

答案：

可以直接答：

因为它解决的不只是“大模型生成一段文本”，而是“系统怎样把复杂决策过程工程化”。具体体现在三点：第一，协议层有 SSE 事件流和 request/trace/run 级诊断；第二，执行层不是线性 prompt，而是有路由、执行、验证、自检、恢复的状态机；第三，结果交付不是只回一段话，而是持续产出 `plan_preview`、`artifact_patch`、`metadata` 和最终 artifact，前端还能把这些结果继续做成可操作工具台。

## 问题 6：如果面试官问“为什么要拆成三层”，推荐怎么答？

答案：

最稳的答法是：

因为这三个问题本来就不应该混在一起。

1. `frontend`
   解决交互、SSE 消费和结果产品化。
2. `backend`
   解决 HTTP / SSE 协议、session 和持久化边界。
3. `agent`
   解决策略路由、工具执行、验证、自检、memory 和 checkpoint。

如果都塞进一个服务里，短期看省事，长期会在可维护性、可测试性和演进能力上一起失血。

## 问题 7：如果面试官问“为什么是 SSE，不是 WebSocket”，推荐怎么答？

答案：

推荐答法：

当前主需求是服务端单向持续推送，而不是复杂双工协作。系统需要把 `stage / reasoning / tool / plan_preview / artifact_patch / metadata / done` 这些过程事件持续推给前端，SSE 已经足够覆盖，而且实现和运维成本更低、对现有 HTTP 设施更友好。只有在多人协作编辑、前端持续反向发控制信号、或者需要更复杂实时协议时，WebSocket 才会明显更优。

代码锚点：

- [chat.py](../../backend/moyuan_web/routes/chat.py)
- [chatClient.ts](../../frontend/src/services/api/chatClient.ts)
- [chatStreamParser.ts](../../frontend/src/services/api/chatStreamParser.ts)

## 问题 8：如果面试官问“为什么前端不是只渲染文本”，推荐怎么答？

答案：

推荐答法：

因为这个项目最终交付的不是一段旅游文案，而是一个可以继续操作的旅行方案。前端除了显示最终文本，还要消费 `plan_preview`、`artifact_patch`、`metadata` 和最终 `artifact`，并把这些结构化结果继续做成 `TravelPlanToolkit` 里的预算、对比、冲突、分享和继续 refine 入口。所以前端在这里是运行态解释层和结果产品化层，而不是普通消息展示层。

代码锚点：

- [useChatRuntime.ts](../../frontend/src/components/chat-area/useChatRuntime.ts)
- [TravelPlanToolkit.tsx](../../frontend/src/components/TravelPlanToolkit.tsx)

## 问题 9：如果面试官问“为什么 Backend 不直接调 graph”，推荐怎么答？

答案：

推荐答法：

因为应用层需要依赖稳定的 runtime seam，而不是直接依赖图内部实现。当前 Backend 通过 `ChatService -> AgentRuntime -> RuntimeDriver -> runtime_flow` 调 Agent，这样既能把 graph 细节隔离出去，也能在 runtime 层统一挂技能、subagent、artifact patch、execution receipt 和后续演进能力。换句话说，Backend 接的是执行 contract，不是底层图实现。

代码锚点：

- [chat_service.py](../../backend/moyuan_web/services/chat_service.py)
- [agent_runtime.py](../../agent/travel_agent/runtime/agent_runtime.py)
- [runtime_driver.py](../../agent/travel_agent/runtime/runtime_driver.py)

## 问题 10：如果面试官问“为什么 Agent 要做成状态机”，推荐怎么答？

答案：

推荐答法：

因为当前任务有明显的分叉和回环。系统先要判断问题是 `direct` 还是需要执行型链路，再决定走 `plan` 或 `react`，执行过程中还可能因为证据不足或结果陈旧在 `verify` 后回跳 `execute`，最终答案成稿后还要走 `self_check`。这类流程如果用线性链表达，会很快变得混乱，而状态机更适合表达条件边、重试和终态。

代码锚点：

- [builder.py](../../agent/travel_agent/graph/builder.py)
- [nodes.py](../../agent/travel_agent/graph/nodes.py)

## 问题 11：如果面试官问“你们怎么保证答案可靠”，推荐怎么答？

答案：

推荐答法：

我们不是单纯依赖 prompt，而是做了多层可靠性设计。工具结果会附带 `_meta`、stale、fallback、refresh 这类证据质量语义，执行后会进入 `verify` 阶段检查证据是否充分、是否需要重试，最终答案成稿后还有 `self_check` 做交付前自检。运行态上还有 request/trace/run 级标识、session、memory、checkpoint、benchmark、golden eval 和 quality gate，尽量把“看起来能跑”升级成“行为可解释、可回放、可度量”。

## 问题 12：如果面试官问“这个项目里最难的地方是什么”，推荐怎么答？

答案：

最推荐的答法不是说“prompt 很难调”，而是说：

最难的是把多层状态边界讲清楚并维护住。这个系统同时有前端流式临时态、后端 session 生命周期、Agent 的状态机状态、memory 的长期上下文和 checkpoint 的执行恢复点。如果这些边界混了，问题会非常难排查。当前实现通过 `useChatRuntime`、`ChatService`、`SessionLifecycleService`、`AgentRuntime`、`memory_integration.py` 和 `runtime_sources.py` 把这些边界分开，这是工程上最难也最重要的部分。

## 问题 13：如果面试官问“这个项目未来先演进哪三件事”，推荐怎么答？

答案：

最稳的三件事是：

1. 把结构化交付继续做深。
   让 artifact、share、history、compare 更像正式交付物，而不只是聊天附属品。
2. 把 runtime 观测和回放继续做强。
   让 trace、execution receipt、checkpoint、replay、失败聚类更闭环。
3. 把 supervisor / subagent 演进做实。
   当前已有 skill registry 和 subagent registry，下一步可以继续增强真正的分工和调度能力。

## 问题 14：如果面试官问“现在最大的技术债是什么”，推荐怎么答？

答案：

比较稳的答法是：

当前最大的技术债不是单点 bug，而是一些能力已经进入“过渡阶段”。例如 runtime seam 已经稳定，但真正的 supervisor / subagent 执行还没有完全独立；`file / postgres`、`sqlite / postgres` 双基线已经具备，但还需要继续统一运维和观测口径；前端已经是 artifact-first，但结构化交付和分享页能力还有继续产品化的空间。这种答法既承认现实，也体现你知道系统正处在哪个阶段。

## 问题 15：如果面试官要我讲一条完整主链，最推荐怎么说？

答案：

直接顺着这条链讲：

```text
用户输入
  -> ChatArea / useChatRuntime
  -> chatClient.ts 发起 SSE
  -> /api/chat/stream
  -> ChatService
  -> AgentRuntime
  -> RuntimeDriver
  -> runtime_flow
  -> builder / nodes
  -> SSE 事件回推
  -> chatStreamParser.ts
  -> MessageList / TravelPlanToolkit
```

然后补一句：

这条链上最关键的不是“请求经过了很多文件”，而是每层都在把结果继续加工成更适合下一层消费的 contract。

## 问题 16：如果面试官要我讲“详细版项目答法”，最推荐怎么组织？

答案：

最推荐按这个模板展开：

1. 背景：
   为什么旅行规划问题不适合做成普通问答。
2. 分层：
   前端、Backend、Agent 各自负责什么。
3. 主链：
   一次请求怎么跨三层流动。
4. 关键取舍：
   为什么 SSE、为什么 runtime seam、为什么状态机、为什么 artifact-first。
5. 可靠性：
   verify、自检、memory、checkpoint、quality gate。
6. 演进：
   现在已经做到哪一步，下一步怎么扩展。

这个模板的好处是：

你不会把项目讲成流水账，而是会讲成一个有约束、有取舍、有演进的工程案例。

## 问题 17：如果面试官让我说“这项目最想证明你什么能力”，推荐怎么答？

答案：

推荐答法：

这个项目最能证明的不是某一个框架会不会用，而是我能不能把一个 AI 场景做成完整工程系统。包括分层设计、协议设计、流式前端、运行态状态边界、Agent 可靠性、持久化与恢复、以及质量门禁和回归策略。也就是说，它更像一个系统工程能力样本，而不是一个单点算法样本。

## 问题 18：如果面试前只能背 10 个代码锚点，最值得背哪 10 个？

答案：

最值得背这 10 个：

1. [useChatRuntime.ts](../../frontend/src/components/chat-area/useChatRuntime.ts)
2. [chatClient.ts](../../frontend/src/services/api/chatClient.ts)
3. [chatStreamParser.ts](../../frontend/src/services/api/chatStreamParser.ts)
4. [TravelPlanToolkit.tsx](../../frontend/src/components/TravelPlanToolkit.tsx)
5. [chat.py](../../backend/moyuan_web/routes/chat.py)
6. [chat_service.py](../../backend/moyuan_web/services/chat_service.py)
7. [lifecycle_service.py](../../backend/moyuan_web/services/session/lifecycle_service.py)
8. [agent_runtime.py](../../agent/travel_agent/runtime/agent_runtime.py)
9. [builder.py](../../agent/travel_agent/graph/builder.py)
10. [nodes.py](../../agent/travel_agent/graph/nodes.py)

如果还能再补 3 个：

1. [runtime_sources.py](../../agent/travel_agent/runtime_sources.py)
2. [memory_integration.py](../../agent/travel_agent/graph/memory_integration.py)
3. [test_chat_stream_local.py](../../tests/test_chat_stream_local.py)

## 问题 19：面试里最不该犯的 5 个错误是什么？

答案：

最常见的失分点是：

1. 把项目讲成“前端发请求，后端调模型，返回结果”。
2. 把 `session / memory / checkpoint` 混成一套。
3. 把 `verify` 和 `self_check` 讲成同一个阶段。
4. 只会说“用了 LangGraph”，但讲不出图边和状态。
5. 只会讲功能，不会讲质量门禁和演进路线。

## 问题 20：如果我现在就要临场复习，这一篇最该回看什么？

答案：

优先回看这 6 个问题：

1. 问题 1：30 秒讲法
2. 问题 2：2 分钟讲法
3. 问题 7：为什么是 SSE
4. 问题 9：为什么要 runtime seam
5. 问题 10：为什么要状态机
6. 问题 13：未来怎么演进

这 6 个问题基本能覆盖一轮像样的项目面试。
