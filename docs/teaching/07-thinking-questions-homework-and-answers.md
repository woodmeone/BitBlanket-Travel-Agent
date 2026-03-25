# 07. 思考题、作业与参考答案

这一章是整套教学材料的练习册、答案册和验收册。

它的目标不是让你“背题”，而是把前面几章真正落实成：

- 能说清
- 能画清
- 能写清
- 能改清

为了方便使用，这一章分成三大部分：

- Part A：思考题与作业
- Part B：参考答案与优秀答案要点
- Part C：评分标准、毕业任务与带教检查表

## 1. 使用方式

最推荐的使用方式不是直接看答案，而是按下面顺序走：

1. 先读对应主文档。
2. 先完成本章前半部分题目。
3. 只在自己写完后，再看后半部分答案。
4. 对照评分标准检查自己是否只是“答到了”，还是“答透了”。

## 2. 题型说明

本章统一使用 4 类题型：

- `口头题`：适合复述主链、讲设计、做面试模拟
- `书面题`：适合输出结构化理解
- `画图题`：适合强迫自己把关系画清楚
- `动手题`：适合真正动代码或做验证

同时，每道题会尽量带上：

- 难度
- 预计耗时
- 交付要求

## 3. 提交模板与使用建议

为了让这份练习册真的能拿来验收，而不只是“看完就算”，建议每次提交都至少包含下面 5 项：

1. 题目编号或作业编号
2. 自己的答案或图
3. 引用到的源码文件
4. 自己认为最不确定的地方
5. 自评等级：`L1 / L2 / L3 / L4`

### 3.1 通用提交模板

```text
题目/作业编号：
类型：
完成时间：

我的答案：

引用源码：

我最不确定的点：

我的自评等级：
```

### 3.2 动手题补充模板

如果是动手题或毕业任务，建议再多补下面 6 项：

```text
改动目标：
影响层：
涉及文件：
风险点：
验证动作：
文档同步：
```

### 3.3 使用建议

最推荐的顺序是：

1. 先做题
2. 再对答案
3. 再按评分表打分
4. 最后补一版“更好的答案”

---

## Part A：思考题与作业

### Phase 0：建立地图与运行环境

配套章节：

- [01-total-plan-and-learning-method.md](01-total-plan-and-learning-method.md)

源码绑定：

- 必读文件：
  [README.md](D:/moyuan/moyuan-travel-agent/README.md)、[docs/README.md](D:/moyuan/moyuan-travel-agent/docs/README.md)、[quick-start.md](D:/moyuan/moyuan-travel-agent/docs/getting-started/quick-start.md)、[main.py](D:/moyuan/moyuan-travel-agent/web/moyuan_web/main.py)
- 建议搜索词：
  `33001`、`38000`、`rapidoc`、`health`、`Home`
- 做题提醒：
  Phase 0 的重点不是背端口，而是建立“项目入口、服务入口、文档入口”三张地图。

#### 题 0-1

- 类型：`口头题`
- 难度：`L1`
- 预计耗时：`10 分钟`

问题：

这个项目为什么要拆成 `frontend/`、`web/`、`agent/` 三层，而不是把所有逻辑都塞进一个后端服务里？

#### 题 0-2

- 类型：`书面题`
- 难度：`L1`
- 预计耗时：`10 分钟`

问题：

`README.md`、`docs/README.md`、`docs/reference/project-structure.md` 三份文档分别解决什么问题？

#### 题 0-3

- 类型：`口头题`
- 难度：`L1`
- 预计耗时：`8 分钟`

问题：

如果后端健康检查能打开，但前端页面打不开，你会优先排查哪几类问题？

#### 作业 0-A

- 类型：`画图题`
- 难度：`L1`
- 预计耗时：`20 分钟`

要求：

画一张项目整体分层图，至少包含：

- 前端
- Web API
- Agent
- 存储

#### 作业 0-B

- 类型：`书面题`
- 难度：`L1`
- 预计耗时：`15 分钟`

要求：

整理一份本地启动清单，写明：

- 前端启动
- 后端启动
- 健康检查入口
- API 文档入口

交付要求：

- 明确端口 `33001` 和 `38000`
- 至少引用 `README.md` 和 `docs/README.md`

---

### Phase 1：聊天主链路

配套章节：

- [02-chat-mainline-and-frontend.md](02-chat-mainline-and-frontend.md)

源码绑定：

- 必读文件：
  [page.tsx](D:/moyuan/moyuan-travel-agent/frontend/src/app/page.tsx)、[ChatArea.tsx](D:/moyuan/moyuan-travel-agent/frontend/src/components/ChatArea.tsx)、[api.ts](D:/moyuan/moyuan-travel-agent/frontend/src/services/api.ts)、[chat.py](D:/moyuan/moyuan-travel-agent/web/moyuan_web/routes/chat.py)、[chat_service.py](D:/moyuan/moyuan-travel-agent/web/moyuan_web/services/chat_service.py)、[builder.py](D:/moyuan/moyuan-travel-agent/agent/travel_agent/graph/builder.py)、[MessageList.tsx](D:/moyuan/moyuan-travel-agent/frontend/src/components/MessageList.tsx)、[TravelPlanToolkit.tsx](D:/moyuan/moyuan-travel-agent/frontend/src/components/TravelPlanToolkit.tsx)
- 建议搜索词：
  `handleSend`、`fetchStreamChat`、`stream_chat`、`plan_preview`、`stage`、`metadata`、`onComplete`
- 做题提醒：
  回答 Phase 1 时，最好不要只说“前端发请求、后端回消息”，而要明确说出中间事件怎么流动。

#### 题 1-1

- 类型：`口头题`
- 难度：`L1`
- 预计耗时：`12 分钟`

问题：

为什么这个项目的黄金主链必须从 `page.tsx` 一直看到 `TravelPlanToolkit.tsx`？

#### 题 1-2

- 类型：`书面题`
- 难度：`L2`
- 预计耗时：`12 分钟`

问题：

为什么聊天接口选 SSE，而不是一次性 JSON？

#### 题 1-3

- 类型：`书面题`
- 难度：`L2`
- 预计耗时：`15 分钟`

问题：

`session_id`、`reasoning_chunk`、`stage`、`tool_start`、`plan_preview`、`metadata` 这几类事件分别服务于什么目的？

#### 作业 1-A

- 类型：`画图题`
- 难度：`L2`
- 预计耗时：`30 分钟`

要求：

以“上海周末两日游，预算 1500，地铁可达”为例，画一张完整请求链图。

最低覆盖：

- `page.tsx`
- `ChatArea.tsx`
- `api.ts`
- `chat.py`
- `chat_service.py`
- `builder.py`
- `MessageList.tsx`
- `TravelPlanToolkit.tsx`

#### 作业 1-B

- 类型：`书面题`
- 难度：`L2`
- 预计耗时：`25 分钟`

要求：

做一张 SSE 事件对照表，至少写清：

- 事件名
- 来源层
- 前端用途
- 触发时机

#### 进阶题 1-C

- 类型：`口头题`
- 难度：`L3`
- 预计耗时：`10 分钟`

问题：

解释为什么“流式输出”和“阶段事件”不是一回事。

---

### Phase 2：前端状态流与结果加工

配套章节：

- [02-chat-mainline-and-frontend.md](02-chat-mainline-and-frontend.md)

源码绑定：

- 必读文件：
  [AppContext.tsx](D:/moyuan/moyuan-travel-agent/frontend/src/context/AppContext.tsx)、[ChatArea.tsx](D:/moyuan/moyuan-travel-agent/frontend/src/components/ChatArea.tsx)、[MessageList.tsx](D:/moyuan/moyuan-travel-agent/frontend/src/components/MessageList.tsx)、[TravelPlanToolkit.tsx](D:/moyuan/moyuan-travel-agent/frontend/src/components/TravelPlanToolkit.tsx)、[travelPlan.ts](D:/moyuan/moyuan-travel-agent/frontend/src/utils/travelPlan.ts)
- 建议搜索词：
  `streamingMessage`、`streamingReasoning`、`metadataRef`、`prepareMarkdownContent`、`extractThinkBlocks`、`looksLikeItineraryContent`、`runQuickRefine`
- 做题提醒：
  Phase 2 最容易答浅。一定要把“状态所有权”和“文本被加工成产品结果”这两层都讲出来。

#### 题 2-1

- 类型：`书面题`
- 难度：`L2`
- 预计耗时：`12 分钟`

问题：

`streamingMessage` 和最终 `messages` 为什么不能简单合并？

#### 题 2-2

- 类型：`口头题`
- 难度：`L2`
- 预计耗时：`10 分钟`

问题：

`AppContext.tsx` 更适合承载哪些状态？

#### 题 2-3

- 类型：`书面题`
- 难度：`L2`
- 预计耗时：`10 分钟`

问题：

`TravelPlanToolkit.tsx` 的价值为什么不仅是展示答案？

#### 作业 2-A

- 类型：`画图题`
- 难度：`L2`
- 预计耗时：`25 分钟`

要求：

画一张前端状态流图，至少标出：

- `inputValue`
- `messages`
- `streamingMessage`
- `streamingReasoning`
- `metadata`

#### 作业 2-B

- 类型：`书面题`
- 难度：`L2`
- 预计耗时：`25 分钟`

要求：

追踪一次文本答案如何变成结构化结果，写成步骤清单。

#### 进阶题 2-C

- 类型：`动手题`
- 难度：`L3`
- 预计耗时：`30-60 分钟`

问题：

如果要新增“复制为 Markdown”或“强调显示 run_id”，你最先会改哪些文件？验证方式是什么？

---

### Phase 3：Web API、Session 与存储

配套章节：

- [03-web-api-session-and-storage.md](03-web-api-session-and-storage.md)

源码绑定：

- 必读文件：
  [main.py](D:/moyuan/moyuan-travel-agent/web/moyuan_web/main.py)、[container.py](D:/moyuan/moyuan-travel-agent/web/moyuan_web/dependencies/container.py)、[chat.py](D:/moyuan/moyuan-travel-agent/web/moyuan_web/routes/chat.py)、[chat_service.py](D:/moyuan/moyuan-travel-agent/web/moyuan_web/services/chat_service.py)、[session_service.py](D:/moyuan/moyuan-travel-agent/web/moyuan_web/services/session_service.py)、[session_repository_impl.py](D:/moyuan/moyuan-travel-agent/web/moyuan_web/repositories/session_repository_impl.py)、[session_storage.py](D:/moyuan/moyuan-travel-agent/web/moyuan_web/storage/session_storage.py)
- 建议搜索词：
  `StreamingResponse`、`stream_chat`、`_ensure_session`、`create_session`、`list_sessions`、`cleanup_expired`、`_atomic_write_json`
- 做题提醒：
  Phase 3 回答“为什么会跨层联动”时，最好直接点名 route / service / repository / storage 各自要改什么。

#### 题 3-1

- 类型：`书面题`
- 难度：`L2`
- 预计耗时：`12 分钟`

问题：

为什么 `route -> service -> repository -> storage` 比 route 里直接写所有逻辑更适合长期维护？

#### 题 3-2

- 类型：`口头题`
- 难度：`L2`
- 预计耗时：`8 分钟`

问题：

`ChatService` 和 `SessionService` 的职责差异是什么？

#### 题 3-3

- 类型：`书面题`
- 难度：`L2`
- 预计耗时：`10 分钟`

问题：

为什么给 session 增加一个字段通常不可能只改一处代码？

#### 作业 3-A

- 类型：`画图题`
- 难度：`L2`
- 预计耗时：`25 分钟`

要求：

画一张 session 生命周期图。

#### 作业 3-B

- 类型：`书面题`
- 难度：`L3`
- 预计耗时：`25 分钟`

要求：

假设新增 `last_used_at` 字段，列出会联动的文件清单，并按层分类。

#### 进阶题 3-C

- 类型：`书面题`
- 难度：`L3`
- 预计耗时：`20 分钟`

问题：

如果未来把 session 从 JSON 改成数据库，最希望哪些层变化最小？为什么？

---

### Phase 4：Agent 图、节点、执行与验证

配套章节：

- [04-agent-core-tools-memory-checkpoint.md](04-agent-core-tools-memory-checkpoint.md)

源码绑定：

- 必读文件：
  [state.py](D:/moyuan/moyuan-travel-agent/agent/travel_agent/graph/state.py)、[builder.py](D:/moyuan/moyuan-travel-agent/agent/travel_agent/graph/builder.py)、[nodes.py](D:/moyuan/moyuan-travel-agent/agent/travel_agent/graph/nodes.py)
- 建议搜索词：
  `AgentState`、`create_initial_state`、`routing_decision`、`execute_node`、`verify_node`、`verify_decision`、`should_continue`、`self_check_node`
- 做题提醒：
  Phase 4 不要用抽象语言糊过去。至少要能说出一个条件边和一个回环是怎么落到代码里的。

#### 题 4-1

- 类型：`口头题`
- 难度：`L2`
- 预计耗时：`10 分钟`

问题：

为什么学习 Agent 时一定要先看 `state.py` 和 `builder.py`？

#### 题 4-2

- 类型：`书面题`
- 难度：`L3`
- 预计耗时：`15 分钟`

问题：

`direct`、`react`、`plan` 三种模式分别适合什么场景？

#### 题 4-3

- 类型：`书面题`
- 难度：`L3`
- 预计耗时：`12 分钟`

问题：

为什么 `verify` 可能会回跳到 `execute`？

#### 题 4-4

- 类型：`口头题`
- 难度：`L3`
- 预计耗时：`8 分钟`

问题：

`self_check` 更像是在解决什么工程问题？

#### 作业 4-A

- 类型：`画图题`
- 难度：`L3`
- 预计耗时：`30 分钟`

要求：

画一张 Agent 节点与边关系图。

#### 作业 4-B

- 类型：`书面题`
- 难度：`L3`
- 预计耗时：`35 分钟`

要求：

给主要节点做一个输入 / 输出 / 决策表，至少覆盖：

- `intent`
- `strategy`
- `plan` 或 `react`
- `execute`
- `verify`
- `answer`
- `self_check`

#### 进阶题 4-C

- 类型：`书面题`
- 难度：`L4`
- 预计耗时：`20 分钟`

问题：

如果要新增一个“预算合法性二次校验”节点，你会放在哪个位置？为什么？

---

### Phase 5：Tools、Memory、Checkpoint

配套章节：

- [04-agent-core-tools-memory-checkpoint.md](04-agent-core-tools-memory-checkpoint.md)

源码绑定：

- 必读文件：
  [travel_api.py](D:/moyuan/moyuan-travel-agent/agent/travel_agent/tools/travel_api.py)、[travel_tools.py](D:/moyuan/moyuan-travel-agent/agent/travel_agent/tools/travel_tools.py)、[memory_integration.py](D:/moyuan/moyuan-travel-agent/agent/travel_agent/graph/memory_integration.py)、[persistent_checkpointer.py](D:/moyuan/moyuan-travel-agent/agent/travel_agent/graph/persistent_checkpointer.py)
- 建议搜索词：
  `_meta`、`stale`、`fallback`、`refresh`、`build_context_messages`、`add_message`、`checkpoint`
- 做题提醒：
  这一阶段的表格题最好都把“面向谁”“何时写”“何时读”“何时恢复”四列写出来。

#### 题 5-1

- 类型：`书面题`
- 难度：`L3`
- 预计耗时：`10 分钟`

问题：

工具返回文本和 `_meta` 分别面向谁？

#### 题 5-2

- 类型：`书面题`
- 难度：`L3`
- 预计耗时：`12 分钟`

问题：

`stale`、`fallback_used`、`refresh_success` 对稳定性有什么帮助？

#### 题 5-3

- 类型：`口头题`
- 难度：`L3`
- 预计耗时：`10 分钟`

问题：

memory、checkpoint、session 的核心差异是什么？

#### 作业 5-A

- 类型：`表格题`
- 难度：`L3`
- 预计耗时：`30 分钟`

要求：

做一张工具契约表，至少覆盖 3 个工具。

#### 作业 5-B

- 类型：`表格题`
- 难度：`L3`
- 预计耗时：`25 分钟`

要求：

做一张 memory / checkpoint / session 对照表。

#### 进阶题 5-C

- 类型：`书面题`
- 难度：`L4`
- 预计耗时：`20 分钟`

问题：

如果要新增一个可刷新的外部数据源，你最先要明确哪些契约？

---

### Phase 6：测试、调试与回归

配套章节：

- [05-testing-debugging-and-change-practice.md](05-testing-debugging-and-change-practice.md)

源码绑定：

- 必读文件：
  [test_sse_streaming.py](D:/moyuan/moyuan-travel-agent/tests/test_sse_streaming.py)、[test_api_integration.py](D:/moyuan/moyuan-travel-agent/tests/test_api_integration.py)、[test_agent_memory_unit.py](D:/moyuan/moyuan-travel-agent/tests/test_agent_memory_unit.py)、[test_agent_execution_optimization_integration.py](D:/moyuan/moyuan-travel-agent/tests/test_agent_execution_optimization_integration.py)、[test_agent_p0_guardrails_unit.py](D:/moyuan/moyuan-travel-agent/tests/test_agent_p0_guardrails_unit.py)、[agent_quality_gate.py](D:/moyuan/moyuan-travel-agent/scripts/agent_quality_gate.py)
- 建议搜索词：
  `text/event-stream`、`quality_gate`、`benchmark`、`golden eval`、`replay`、`fallback_steps`
- 做题提醒：
  Phase 6 最容易停留在“跑哪些命令”。更好的答案要解释“这些命令为什么和这次风险匹配”。

#### 题 6-1

- 类型：`书面题`
- 难度：`L2`
- 预计耗时：`10 分钟`

问题：

为什么这个项目里测试既是质量门禁，也是设计说明书？

#### 题 6-2

- 类型：`口头题`
- 难度：`L2`
- 预计耗时：`8 分钟`

问题：

为什么改前端、改 API、改 Agent 时，回归命令不应该完全一样？

#### 题 6-3

- 类型：`书面题`
- 难度：`L3`
- 预计耗时：`15 分钟`

问题：

`unit`、`integration`、`benchmark`、`golden eval` 分别保护什么？

#### 作业 6-A

- 类型：`表格题`
- 难度：`L3`
- 预计耗时：`30 分钟`

要求：

写一份改动风险等级到回归动作的对照表。

#### 作业 6-B

- 类型：`书面题`
- 难度：`L3`
- 预计耗时：`25 分钟`

要求：

从现有测试里挑 3 个文件，反推它们分别在保护什么行为。

#### 进阶题 6-C

- 类型：`书面题`
- 难度：`L4`
- 预计耗时：`15 分钟`

问题：

如果一次改动单测通过但 benchmark 退化，说明了什么？

---

### Phase 7：面试讲解、系统拓展与毕业任务

配套章节：

- [06-interview-highlights-and-system-evolution.md](06-interview-highlights-and-system-evolution.md)

源码绑定：

- 必读文件：
  [ChatArea.tsx](D:/moyuan/moyuan-travel-agent/frontend/src/components/ChatArea.tsx)、[chat_service.py](D:/moyuan/moyuan-travel-agent/web/moyuan_web/services/chat_service.py)、[builder.py](D:/moyuan/moyuan-travel-agent/agent/travel_agent/graph/builder.py)、[nodes.py](D:/moyuan/moyuan-travel-agent/agent/travel_agent/graph/nodes.py)、[session_storage.py](D:/moyuan/moyuan-travel-agent/web/moyuan_web/storage/session_storage.py)、[agent_quality_gate.py](D:/moyuan/moyuan-travel-agent/scripts/agent_quality_gate.py)
- 建议搜索词：
  `verify`、`StreamingResponse`、`streamingMessage`、`_meta`、`checkpoint`、`quality gate`
- 做题提醒：
  Phase 7 的核心不是“讲更多名词”，而是把亮点、取舍、代码锚点和演进路线串成一个完整故事。

#### 题 7-1

- 类型：`口头题`
- 难度：`L3`
- 预计耗时：`10 分钟`

问题：

这个项目最值得讲的三个工程亮点是什么？

#### 题 7-2

- 类型：`书面题`
- 难度：`L3`
- 预计耗时：`15 分钟`

问题：

如果把这个项目作为面试项目经历，最容易被追问的点有哪些？

#### 题 7-3

- 类型：`书面题`
- 难度：`L4`
- 预计耗时：`15 分钟`

问题：

如果让你继续扩展这个项目，你会优先做哪三个方向？

#### 作业 7-A

- 类型：`口头 + 书面`
- 难度：`L3`
- 预计耗时：`30 分钟`

要求：

写一份 5 分钟项目讲解提纲，并能口头讲一遍。

#### 作业 7-B

- 类型：`设计题`
- 难度：`L4`
- 预计耗时：`45 分钟`

要求：

设计一个跨至少两层的小改动方案，并写清：

- 影响范围
- 验证方式
- 风险点
- 文档同步计划

#### 进阶题 7-C

- 类型：`设计题`
- 难度：`L4`
- 预计耗时：`45-60 分钟`

问题：

设计一个“新人毕业任务”，同时考察前端、Web API、Agent 三层理解。

#### 综合实战案例 7-D

- 类型：`动手 + 书面`
- 难度：`L3-L4`
- 预计耗时：`0.5-1 天`

题目：

给 session 列表新增一个更友好的 `last_active_label` 字段，并完成：

- Web API 输出
- 前端展示
- 回归验证
- 文档同步

最低交付要求：

1. 写一页改动设计说明。
2. 写一份回归矩阵。
3. 指出至少 3 个涉及文件。
4. 写明需要同步哪篇教学文档。

优秀完成标准：

1. 能解释为什么这是“中风险跨层改动”。
2. 能说明该字段更适合后端生成还是前端格式化，并给出取舍。
3. 能把这次改动讲成一个完整的小型工程案例。

---

## Part B：参考答案与优秀答案要点

### Phase 0 参考答案

1. 三层拆分的核心原因是职责分离。前端负责交互和结果呈现，Web 层负责协议与服务编排，Agent 层负责决策、执行和验证。这样更适合演进和定位问题。
2. `README.md` 解决项目总览，`docs/README.md` 解决文档导航，`project-structure.md` 解决目录职责。三者面向不同粒度和受众。
3. 先查前端是否正常启动、端口是否正确、环境变量是否配置、构建是否成功、浏览器控制台是否报错、接口是否被正确请求。

优秀答案要点：

- 不只讲“分层”，还讲清分层后的收益和代价。
- 能区分“项目总入口”和“开发文档总入口”。

### Phase 1 参考答案

1. 因为用户真正感知的不是“后端返回了答案”，而是从输入、流式事件到最终结构化结果的完整体验。不到 `TravelPlanToolkit.tsx`，链路还没到产品形态。
2. SSE 更适合单向持续推送 token 和中间事件，一次性 JSON 不适合当前流式体验。
3. `session_id` 用于绑定会话和运行标识，`reasoning_chunk` 用于展示推理过程，`stage` 用于过程提示，`tool_start` 用于工具可见性，`plan_preview` 用于提前展示计划，`metadata` 用于诊断和附加上下文。

优秀答案要点：

- 能区分“内容事件”“过程事件”“诊断事件”。
- 能解释为什么当前阶段 SSE 比 WebSocket 更合适。

### Phase 2 参考答案

1. `streamingMessage` 是临时态，`messages` 是最终态。两者生命周期不同，合并后会让完成、失败、取消和展示逻辑混乱。
2. `AppContext.tsx` 更适合放跨组件共享、会话级、页面级影响较大的状态。
3. `TravelPlanToolkit.tsx` 把文本答案进一步变成结构化和可交互的产品结果。

优秀答案要点：

- 能说明状态所有权。
- 能说明“消息渲染”和“结果产品化”不是同一个问题。

### Phase 3 参考答案

1. route 更适合做协议层工作，service 负责业务编排，repository 抽象业务数据访问，storage 负责底层读写。这样更易维护和替换存储方式。
2. `ChatService` 关注聊天流式编排和 Agent 协调，`SessionService` 关注会话元数据和生命周期管理。
3. 因为字段常常会穿过请求响应、业务逻辑、持久化、前端消费和测试断言多个层级。

优秀答案要点：

- 不只会列层次，还能解释每层“该做什么”和“不该做什么”。

### Phase 4 参考答案

1. `state.py` 决定状态字段，`builder.py` 决定图结构，`nodes.py` 才是具体实现。顺序反了就容易迷失在细节里。
2. `direct` 适合直接回答，`react` 适合边推理边用工具，`plan` 适合复杂约束和多步骤任务。
3. 因为验证失败时合理动作通常是补执行、补证据，而不是直接出答案。
4. `self_check` 更像输出质量保护和工程兜底。

优秀答案要点：

- 能讲清“状态机”不只是节点多，而是有条件边和回环。

### Phase 5 参考答案

1. 文本结果更偏给模型和用户看，`_meta` 更偏给系统做结构化展示、验证、刷新和调试。
2. 它们帮助系统识别数据是否可靠、是否走过兜底、是否刷新成功，从而减少错误传播。
3. session 解决会话与消息，memory 解决长期偏好和摘要，checkpoint 解决图运行恢复。

优秀答案要点：

- 能从“写入时机”和“恢复目的”区分三者。

### Phase 6 参考答案

1. 因为测试本身就在定义系统不应退化成什么样。它不只是防 crash，也在保护事件协议、存储语义和 Agent 质量。
2. 因为不同改动触发的风险不同，前端更关心构建和渲染，API 更关心契约，Agent 更关心行为质量和策略稳定性。
3. unit 保护局部逻辑，integration 保护协作，benchmark 保护趋势，golden eval 保护关键样本行为。

优秀答案要点：

- 能从风险类型出发选回归，而不是所有改动都跑一套命令。

### Phase 7 参考答案

1. 最值得讲的工程亮点通常包括：SSE 中间事件、三层分层、Agent 状态机与验证、结果产品化、稳定性与质量控制。
2. 最容易被追问的是：为什么要分层、为什么选 SSE、为什么 Agent 要做成状态机、memory 与 checkpoint 有什么区别。
3. 优先扩展方向通常包括：数据库化存储、多模型与成本控制、更强观测和回放、更强工具与缓存、产品化结果编辑能力。

优秀答案要点：

- 不只讲“做了什么”，还讲“为什么这么设计”和“如何继续演进”。

### 综合实战案例 7-D 参考完成框架

一个合格答案至少应包含：

1. 背景：session 列表当前只有原始时间字段，用户不够直观。
2. 目标：增加更友好的最近活跃展示，不破坏排序和兼容性。
3. 影响层：至少涉及 Web 输出层、前端展示层和文档层。
4. 风险：时区、旧数据兼容、字段命名一致性、排序语义。
5. 验证：`pytest`、前端 `lint/build`、手工检查 session 列表展示。
6. 文档同步：至少同步 [03-web-api-session-and-storage.md](03-web-api-session-and-storage.md)、[05-testing-debugging-and-change-practice.md](05-testing-debugging-and-change-practice.md) 或本章中的对应练习说明。

优秀答案要点：

- 能解释“为什么有些格式化应该放前端，有些应该放后端”。
- 能明确说明 repository / storage 是否需要改动，而不是默认层层都改。
- 能补一句如果未来国际化或多时区，要怎样演进这次设计。

---

## Part C：评分标准、毕业任务与带教检查表

### 1. 四级评分标准

#### L1：跟读通过

表现：

- 能复述主链和三层结构
- 能定位关键入口文件

#### L2：上手通过

表现：

- 能画图
- 能列联动文件
- 能做低风险小改动

#### L3：工程通过

表现：

- 能讲清设计取舍
- 能做中风险改动
- 能选择正确回归

#### L4：维护者通过

表现：

- 能讲系统演进
- 能做跨层改动
- 能设计风险控制与文档同步

### 1.1 更细的评分维度

建议从下面 5 个维度评分，每项可打 `1-4` 分：

| 维度 | 1 分 | 2 分 | 3 分 | 4 分 |
| --- | --- | --- | --- | --- |
| 主链理解 | 只能说出零散文件 | 能大致复述链路 | 能说清事件与状态 | 能结合代码讲取舍 |
| 分层理解 | 容易混层 | 能区分主要层 | 能解释边界与联动 | 能说明迁移与演进 |
| 表达质量 | 口语化、跳跃 | 有结构但不稳 | 结构清楚、有重点 | 兼顾实现、风险和取舍 |
| 改动意识 | 只会描述功能 | 能列部分影响 | 能写验证计划 | 能控制风险并同步文档 |
| 面试深度 | 只能答表层问题 | 能答常规问题 | 能答追问 | 能展开演进和反例 |

### 1.2 常见失分点

最常见的失分不是“不会”，而是下面这些：

1. 只背名词，不绑定真实文件和真实链路。
2. 只讲结果，不讲中间事件和状态变化。
3. 把 `session`、`memory`、`checkpoint` 混成一件事。
4. 只说“这样更好维护”，但说不出为什么更好维护。
5. 作业里只写改动目标，不写风险和验证。
6. 面试题只给结论，不给对比和取舍。

### 1.3 及格答案与优秀答案的差异

可以用下面这张对照表快速判断自己的答案层级：

| 类型 | 及格答案通常长这样 | 优秀答案通常会多什么 |
| --- | --- | --- |
| 主链题 | 能按顺序说出链路 | 会说明每层为什么这么拆 |
| 分层题 | 能区分 route / service / storage | 会说明 repository 的价值和迁移边界 |
| Agent 题 | 能说出节点顺序 | 会说明回环、验证、证据链和可靠性设计 |
| 测试题 | 能列出跑哪些命令 | 会说明为什么这些命令和这次风险匹配 |
| 面试题 | 能给出标准答法 | 会给出反例、取舍和未来演进 |

### 2. 毕业任务模板

一份合格的毕业任务至少包含：

1. 背景
2. 目标
3. 影响层级
4. 涉及文件
5. 风险点
6. 验证矩阵
7. 文档同步
8. 若继续扩展，下一步怎么做

### 2.1 推荐交付结构

建议最终提交时固定成下面 8 段，这样最便于带教者和 reviewer 快速看懂：

1. 背景与目标
2. 当前现象或问题
3. 设计思路
4. 影响层级与文件列表
5. 风险点
6. 验证矩阵
7. 文档同步
8. 后续可扩展点

### 2.2 毕业任务提交模板

```text
毕业任务标题：

背景与目标：

当前现象/问题：

设计思路：

影响层级：

涉及文件：

风险点：

验证矩阵：

文档同步：

后续可扩展点：
```

### 3. 带教者检查表

如果你是带教者，最推荐检查下面这 8 件事：

1. 对方能否画出聊天主链
2. 对方能否区分 `messages` 和 `streamingMessage`
3. 对方能否解释 Web 分层
4. 对方能否解释 Agent 状态机和 `verify`
5. 对方能否区分 session、memory、checkpoint
6. 对方能否按风险选回归
7. 对方能否做一次跨两层的小改动
8. 对方能否把项目讲成一个有取舍的工程案例

### 4. 一个最小毕业任务示例

推荐题目：

给 session 或城市卡增加一个小字段，并把它从：

- Web API
- 前端展示
- 测试验证
- 文档更新

完整打通。

为什么推荐这个题目：

- 跨至少两层
- 风险中等
- 不会一上来就把最复杂的 Agent 改挂
- 能训练联动意识和文档同步意识

## 结尾提醒

这一章不是为了让你背标准答案，而是为了帮你形成一个非常关键的工程能力：

当别人问你“这个系统为什么这样设计、哪里最难、如果扩展怎么办”时，你能回到真实代码和真实链路里，把答案讲得清清楚楚。
