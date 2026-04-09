# 01. 总规划与学习方法面试问答

这一篇不再讲“怎么上课”，只回答最值得先统一的面试基础问题。

## 问题 1：这个项目到底是什么？

答案：

`moyuan-travel-agent` 不是一个普通聊天 Demo，而是一个把旅行约束输入变成可执行旅行决策流程的 AI 工程样例。

它同时覆盖：

1. 用户输入预算、天数、偏好、路线等约束。
2. 系统识别意图和风险。
3. Agent 选择 `direct / react / plan` 路径。
4. 工具执行、验证、自检、memory、checkpoint。
5. 前端用流式事件和结构化结果把答案继续做成产品功能。

一句话讲法：

这个项目把“AI 对话”做成了“可流式解释、可验证、可继续操作、可回放”的旅行决策系统。

## 问题 2：它和普通聊天 Demo 最大的区别是什么？

答案：

普通聊天 Demo 通常到“模型返回一段话”就结束了。

这个项目显式多做了 5 层工程化：

1. 用 SSE 持续推送过程事件，而不是只返回最终文本。
2. 前端不仅展示答案，还把结果加工成 `TravelPlanToolkit`。
3. Backend API 不只是代理模型，而是负责 session、SSE 编排和持久化边界。
4. Agent 不是线性 prompt，而是状态机。
5. 系统有 memory、checkpoint、benchmark、golden eval、quality gate。

## 问题 3：项目的三层结构应该怎么讲？

答案：

最稳的讲法是：

- `frontend`
  负责交互、SSE 消费、消息渲染和结构化结果产品化。
- `backend`
  负责 HTTP / SSE 协议、业务编排、session、repository、persistence。
- `agent`
  负责状态机、工具执行、验证、自检、memory、checkpoint 和 runtime seam。

可以直接配这张图讲：

```text
frontend/
  page.tsx / ChatArea.tsx / MessageList.tsx / TravelPlanToolkit.tsx

backend/
  routes/chat.py / services/chat_service.py / services/session/lifecycle_service.py

agent/
  runtime/agent_runtime.py / runtime/runtime_driver.py / graph/runtime_flow.py / graph/nodes.py
```

## 问题 4：整个项目最重要的黄金主链是什么？

答案：

```text
页面输入
  -> ChatArea
  -> useChatRuntime
  -> chatClient.ts 发起 SSE
  -> FastAPI /api/chat/stream
  -> chat_service.py
  -> agent_runtime.py
  -> runtime_driver.py
  -> runtime_flow.py
  -> chatStreamParser.ts
  -> MessageList / TravelPlanToolkit
```

如果你面试时只能讲一条链，就讲这条。

## 问题 5：第一次读源码，最推荐按什么顺序看？

答案：

最推荐顺序不是按目录树，而是按主链和复杂度递进：

1. 先读前端主链：
   [02-chat-mainline-and-frontend.md](02-chat-mainline-and-frontend.md)
2. 再读 Backend API 分层：
   [03-backend-api-session-and-persistence.md](03-backend-api-session-and-persistence.md)
3. 再读 Agent runtime 和状态机：
   [04-agent-core-tools-memory-checkpoint.md](04-agent-core-tools-memory-checkpoint.md)
4. 最后补测试、排障和质量门禁：
   [05-testing-debugging-and-change-practice.md](05-testing-debugging-and-change-practice.md)

原因很简单：

- 先读前端，你知道请求从哪里开始。
- 再读 backend，你知道请求怎样被编排。
- 再读 agent，你才知道最难的决策和验证是怎么发生的。

## 问题 6：如果我只有 12 个关键文件时间，最值得看哪 12 个？

答案：

最推荐这 12 个：

1. [page.tsx](../../frontend/src/app/page.tsx)
2. [ChatArea.tsx](../../frontend/src/components/ChatArea.tsx)
3. [useChatRuntime.ts](../../frontend/src/components/chat-area/useChatRuntime.ts)
4. [chatClient.ts](../../frontend/src/services/api/chatClient.ts)
5. [chatStreamParser.ts](../../frontend/src/services/api/chatStreamParser.ts)
6. [chat.py](../../backend/moyuan_web/routes/chat.py)
7. [chat_service.py](../../backend/moyuan_web/services/chat_service.py)
8. [lifecycle_service.py](../../backend/moyuan_web/services/session/lifecycle_service.py)
9. [agent_runtime.py](../../agent/travel_agent/runtime/agent_runtime.py)
10. [runtime_driver.py](../../agent/travel_agent/runtime/runtime_driver.py)
11. [runtime_flow.py](../../agent/travel_agent/graph/runtime_flow.py)
12. [builder.py](../../agent/travel_agent/graph/builder.py)

如果还能再补 3 个：

1. [nodes.py](../../agent/travel_agent/graph/nodes.py)
2. [memory_integration.py](../../agent/travel_agent/graph/memory_integration.py)
3. [TravelPlanToolkit.tsx](../../frontend/src/components/TravelPlanToolkit.tsx)

## 问题 7：哪些术语最容易混淆，必须先分清？

答案：

最容易混的只有下面几组：

| 术语 | 应该怎么记 |
| --- | --- |
| session | 产品会话和消息历史 |
| memory | 长期偏好、摘要、跨轮上下文 |
| checkpoint | 图运行恢复点和 replay 基础 |
| stage | 当前执行阶段 |
| metadata | 运行诊断和结构化补充信息 |
| repository | 业务语义数据访问层 |
| persistence | 文件或 SQL 的底层实现层 |
| direct / react / plan | Agent 的三种策略路径 |
| verify | 执行结果质量检查 |
| self_check | 最终回答前的轻量自检 |

面试里最容易失分的就是把 `session / memory / checkpoint` 混成一套东西。

## 问题 8：这个项目的“当前实现真相源”应该去哪看？

答案：

优先级按下面记：

1. `docs/reference/` 和 `docs/architecture/`
2. `docs/governance/` 中已生效的 ADR / RFC
3. `README.md`
4. `docs/getting-started/`
5. `docs/teaching/`

teaching 的职责是帮助你讲清楚，不是覆盖 reference 和 architecture。

## 问题 9：面试时，最低应该能回答哪些问题？

答案：

至少要能回答下面 12 个：

1. 这个项目为什么不是普通聊天 Demo。
2. 为什么要拆成 `frontend / backend / agent` 三层。
3. 一次聊天请求怎么流经整个系统。
4. 为什么选 SSE。
5. 为什么前端要区分 `streamingMessage` 和最终 `messages`。
6. 为什么 Backend 要走 `route -> service -> repository -> persistence`。
7. 为什么 Backend 不直接调 graph，而是走 `AgentRuntime`。
8. 为什么 Agent 要用状态机。
9. `direct / react / plan` 分别解决什么问题。
10. `verify` 和 `self_check` 的工程意义是什么。
11. session、memory、checkpoint 有什么区别。
12. 这个项目未来最可能先演进哪几个方向。

## 问题 10：如果我只剩 20 分钟，最推荐看什么？

答案：

按这个顺序：

1. [06-interview-highlights-and-system-evolution.md](06-interview-highlights-and-system-evolution.md) 的 30 秒 / 2 分钟讲法
2. [06-interview-highlights-and-system-evolution.md](06-interview-highlights-and-system-evolution.md) 的代码锚点速查卡
3. [07-thinking-questions-homework-and-answers.md](07-thinking-questions-homework-and-answers.md) 的高频题库

如果再多 10 分钟：

1. 补看 [02-chat-mainline-and-frontend.md](02-chat-mainline-and-frontend.md) 的黄金主链
2. 补看 [03-backend-api-session-and-persistence.md](03-backend-api-session-and-persistence.md) 的四层分工
3. 补看 [04-agent-core-tools-memory-checkpoint.md](04-agent-core-tools-memory-checkpoint.md) 的状态机和 `verify`

## 问题 11：这篇文档最后最想帮我记住什么？

答案：

只记住两件事就够了：

1. 这个项目的核心不是“模型会说话”，而是“系统怎样把旅行决策工程化”。
2. 读 teaching 的正确顺序永远是：
   主链 -> 分层 -> 状态机 -> 验证与恢复 -> 质量门禁 -> 面试讲法。
