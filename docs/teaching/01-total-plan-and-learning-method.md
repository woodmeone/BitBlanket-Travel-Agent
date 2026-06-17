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
7. [chat\_service.py](../../backend/moyuan_web/services/chat_service.py)
8. [lifecycle\_service.py](../../backend/moyuan_web/services/session/lifecycle_service.py)
9. [agent\_runtime.py](../../agent/travel_agent/runtime/agent_runtime.py)
10. [runtime\_driver.py](../../agent/travel_agent/runtime/runtime_driver.py)
11. [runtime\_flow.py](../../agent/travel_agent/graph/runtime_flow.py)
12. [builder.py](../../agent/travel_agent/graph/builder.py)

如果还能再补 3 个：

1. [nodes.py](../../agent/travel_agent/graph/nodes.py)
2. [memory\_integration.py](../../agent/travel_agent/graph/memory_integration.py)
3. [TravelPlanToolkit.tsx](../../frontend/src/components/TravelPlanToolkit.tsx)

## 问题 7：哪些术语最容易混淆，必须先分清？

答案：

最容易混的只有下面几组：

| 术语                    | 应该怎么记             |
| --------------------- | ----------------- |
| session               | 产品会话和消息历史         |
| memory                | 长期偏好、摘要、跨轮上下文     |
| checkpoint            | 图运行恢复点和 replay 基础 |
| stage                 | 当前执行阶段            |
| metadata              | 运行诊断和结构化补充信息      |
| repository            | 业务语义数据访问层         |
| persistence           | 文件或 SQL 的底层实现层    |
| direct / react / plan | Agent 的三种策略路径     |
| verify                | 执行结果质量检查          |
| self\_check           | 最终回答前的轻量自检        |

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

1. 这个项目的核心不是"模型会说话"，而是"系统怎样把旅行决策工程化"。
2. 读 teaching 的正确顺序永远是：
   主链 -> 分层 -> 状态机 -> 验证与恢复 -> 质量门禁 -> 面试讲法。

***

## 附录：核心概念详解

这一部分专门解释文档中出现的关键技术概念，适合初次接触 AI 工程项目的读者。

### A. 什么是 SSE？

**SSE（Server-Sent Events）** 是一种服务器向客户端单向推送数据的技术。

**核心特点**：

1. 基于 HTTP 协议，不需要额外握手。
2. 服务器可以持续向客户端推送数据流。
3. 客户端只能接收，不能反向发送。
4. 内置自动重连机制。

**对比 WebSocket**：

| 特性   | SSE           | WebSocket   |
| ---- | ------------- | ----------- |
| 方向   | 单向（服务器→客户端）   | 双向          |
| 协议   | HTTP          | 独立协议 ws\:// |
| 重连   | 自动            | 需手动实现       |
| 适用场景 | 实时通知、日志流、进度推送 | 聊天室、游戏、协作编辑 |

**本项目为什么用 SSE**：

因为 Agent 执行过程需要持续推送阶段事件（stage、tool、reasoning、answer），但不需要客户端反向控制，SSE 已经够用且实现更简单。

代码锚点：

- [chatClient.ts](../../frontend/src/services/api/chatClient.ts)：前端发起 SSE 请求
- [chat.py](../../backend/moyuan_web/routes/chat.py)：后端 SSE 响应入口

### B. TravelPlanToolkit 是什么？

**TravelPlanToolkit** 是前端的一个核心组件，把 AI 返回的旅行建议从"一段长文本"变成"可操作的工具台"。

**功能包括**：

1. 每日行程卡片（Itinerary）：把长文本拆成按天展示的结构化卡片。
2. 预算滑杆调整：省钱 / 均衡 / 舒适三档切换。
3. 多方案对比：并排比较不同旅行方案。
4. 冲突检测：自动发现时间冲突、路程过长、闭馆风险。
5. 出发提醒 Checklist：出发前需要准备的事项清单。
6. 导出图片、分享链接：把结果变成可分享的交付物。

**为什么重要**：

它最能证明这不是普通聊天页——前端不只是展示文本，而是把结果继续做成可操作的产品功能。

代码锚点：

- [TravelPlanToolkit.tsx](../../frontend/src/components/TravelPlanToolkit.tsx)
- [useTravelPlanToolkitActions.ts](../../frontend/src/components/travel-plan-toolkit/useTravelPlanToolkitActions.ts)

### C. 什么是状态机？

**状态机（State Machine）** 是一种描述系统在不同状态之间转换的模型。

**核心要素**：

1. **状态（State）**：系统当前处于什么阶段。
2. **转换（Transition）**：从状态 A 到状态 B 的条件。
3. **事件（Event）**：触发转换的输入。

**举例：电梯状态机**：

```text
[停止] --按下按钮--> [上行] --到达楼层--> [停止]
[停止] --按下按钮--> [下行] --到达楼层--> [停止]
[停止] --故障--> [维修]
```

**举例：本项目 Agent 状态机**：

```text
intent --> strategy --> plan --> execute --> verify --> answer --> self_check
                        ↑_________验证失败回跳_________↓
```

**本项目为什么用状态机**：

Agent 执行流程有明显的分叉和回环：先判断问题类型，再决定走哪条路径，执行后可能验证失败需要回跳重试。这类流程如果用线性代码（if/else 串）表达，很快就会变得难以维护。

代码锚点：

- [builder.py](../../agent/travel_agent/graph/builder.py)：图构建，定义状态和边
- [nodes.py](../../agent/travel_agent/graph/nodes.py)：每个状态节点的执行逻辑

### D. memory、checkpoint、benchmark、golden eval、quality gate 解释

| 术语               | 概念                  | 举例说明                                            |
| ---------------- | ------------------- | ----------------------------------------------- |
| **memory**       | 长期记忆，跨会话保留的上下文      | 用户说过"不喜欢爬山"，下次对话自动记住并避开爬山景点                     |
| **checkpoint**   | 执行恢复点，记录 Agent 运行状态 | 用户中途停止对话，下次可以从断点继续执行，不用从头开始                     |
| **benchmark**    | 性能基准测试，衡量 Agent 表现  | 测试 100 个旅行问题，统计成功率 85%、平均响应时间 12s               |
| **golden eval**  | 黄金标准评估，用人工标准答案对比    | 问题"北京三日游预算 2000"，对比人工写的标准答案，计算相似度               |
| **quality gate** | 质量门禁，发布前的检查门槛       | 成功率 < 80% 或 hallucination rate > 15% 时，不允许发布新版本 |

**为什么要有这些机制**：

普通 Demo 只看"能不能跑"，工程化项目要看"行为是否稳定、是否可度量、是否可回放"。

代码锚点：

- [memory\_integration.py](../../agent/travel_agent/graph/memory_integration.py)
- [persistent\_checkpointer.py](../../agent/travel_agent/graph/persistent_checkpointer.py)
- [agent\_benchmark.py](../../scripts/agent_benchmark.py)
- [agent\_golden\_eval.py](../../scripts/agent_golden_eval.py)
- [agent\_quality\_gate.py](../../scripts/agent_quality_gate.py)

### E. 什么是 ReAct？智能体工作模式都有什么？

**ReAct** = Reasoning + Acting，一种让 Agent "边思考边行动" 的模式。

**工作流程示例**：

```text
Thought: 用户想去上海周末游，我需要先查天气
Action: call_weather_tool("上海", "周末")
Observation: 上海明天晴，25°C，适合户外
Thought: 天气不错，可以推荐户外景点
Action: call_attraction_tool("上海", "户外")
Observation: 外滩、豫园、迪士尼...
Thought: 用户预算 1500，迪士尼门票较贵，优先推荐外滩和豫园
Answer: 推荐外滩+豫园一日游，预算约 500 元...
```

**智能体常见工作模式**：（还有一个智能体协作的工作模式，这个就是另一种情况了）

| 模式                   | 特点         | 适用场景                     |
| -------------------- | ---------- | ------------------------ |
| **Direct**           | 直接回答，不调用工具 | 简单问题如"什么是 SSE"、"北京有哪些景点" |
| **ReAct**            | 思考→行动→观察循环 | 需要查实时数据的复杂问题             |
| **Plan-and-Execute** | 先规划再执行     | 多步骤任务如"帮我规划 5 天旅行路线"     |
| **Reflexion**        | 执行后反思改进    | 需要高质量输出的任务，如写代码、写报告      |

**本项目的三种模式**：

1. `direct`：简单问题直接回答，不进入执行链路。
2. `react`：边思考边执行，适合需要实时数据的问题。
3. `plan`：先产出结构化计划预览（plan\_preview），用户确认后再执行。

代码锚点：

- [runtime\_flow.py](../../agent/travel_agent/graph/runtime_flow.py)：模式路由逻辑
- [nodes.py](../../agent/travel_agent/graph/nodes.py)：各模式执行节点

### F. 这个项目的 API 调用在哪里？

**API 调用链路**：

| 层级       | 文件                                                                     | 作用                       |
| -------- | ---------------------------------------------------------------------- | ------------------------ |
| 前端       | [chatClient.ts](../../frontend/src/services/api/chatClient.ts)         | 发起 SSE 请求到后端             |
| 后端路由     | [chat.py](../../backend/moyuan_web/routes/chat.py)                     | 接收 `/api/chat/stream` 请求 |
| 后端服务     | [chat\_service.py](../../backend/moyuan_web/services/chat_service.py)  | 编排调用 Agent Runtime       |
| Agent 入口 | [agent\_runtime.py](../../agent/travel_agent/runtime/agent_runtime.py) | 调用 LLM API（通过 LangChain） |

**LLM 配置文件**：

- [llm\_config.yaml](../../backend/config/llm_config.yaml)：配置 api\_key、api\_base、model

**为什么可以直接使用**：

项目已经预配置了 LLM 接口（MiniMax M2.5，Anthropic 兼容协议）。如果聊天功能无法正常工作，通常需要检查：

1. `llm_config.yaml` 中是否有有效的 `api_key`
2. `api_base` 是否指向正确的模型服务地址
3. 模型名称是否正确

### G. 为什么要专门搞个 API 端口？

**前后端分离架构**：

```text
前端 (localhost:33001, Next.js)  <--HTTP/SSE-->  后端 (localhost:38000, FastAPI)
```

**为什么不能合并成一个端口**：

1. **技术栈不同**：前端用 Node.js/Next.js，后端用 Python/FastAPI，运行时完全不同。
2. **职责分离**：前端管 UI 渲染和交互，后端管业务逻辑和数据，分开更清晰。
3. **开发效率**：前端热更新（改代码立即生效），后端独立重启，互不干扰。
4. **部署灵活**：可以分开部署到不同服务器，前端放 CDN，后端放云服务器。
5. **扩展性**：一个后端 API 可以给多个前端共用（Web、App、小程序）。

**实际请求流程**：

```text
浏览器访问 http://localhost:33001（前端页面）
前端页面发起请求 http://localhost:38000/api/chat/stream（后端 API）
后端调用 LLM API（模型服务，如 MiniMax）
后端通过 SSE 把结果流式推回前端
前端渲染结果到页面
```

**端口分配**：

| 服务         | 端口            | 说明            |
| ---------- | ------------- | ------------- |
| 前端         | 33001         | Next.js 开发服务器 |
| 后端 API     | 38000         | FastAPI 服务    |
| API 文档     | 38000/rapidoc | RapiDoc 接口文档  |
| Prometheus | 39090         | 可观测性（可选）      |
| Grafana    | 33002         | 可观测性仪表盘（可选）   |

