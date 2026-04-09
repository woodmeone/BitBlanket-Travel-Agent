# 05. 测试、调试与改动实践面试问答

这一篇只讲真实改动时最值得面试和协作里讲清楚的问题。

## 问题 1：为什么这个项目里的测试不只是“兜底”，还是设计说明书？

答案：

因为测试文件本身就在告诉你系统最怕什么地方退化。

例如：

1. [test_chat_stream_local.py](../../tests/test_chat_stream_local.py)
   保护的是聊天 SSE 契约。
2. [test_api_smoke_local.py](../../tests/test_api_smoke_local.py)
   保护的是关键 API 主路径和健康接口。
3. [test_runtime_data_lifecycle_unit.py](../../tests/test_runtime_data_lifecycle_unit.py)
   保护的是 runtime 备份、恢复、清理和 checkpoint 维护。
4. [agent_quality_gate.py](../../scripts/agent_quality_gate.py)
   保护的是质量阈值和回归趋势。

所以测试在这里既是验证工具，也是架构说明书。

## 问题 2：当前项目的验证版图最稳的讲法是什么？

答案：

最稳的讲法是分 4 层：

1. 路由和流式契约测试。
2. API smoke 和错误合同测试。
3. runtime / memory / checkpoint 的单元与集成测试。
4. benchmark、golden eval、quality gate 这种趋势型质量验证。

这样讲的好处是：

既能体现分层，也能体现“不是所有改动都该跑同一套回归”。

## 问题 3：为什么不能只靠手工点页面验证？

答案：

因为这个系统的关键风险很多都不在页面层。

只点页面，通常看不出来的风险包括：

1. `text/event-stream` 契约坏了。
2. `metadata / done` 边界错了。
3. session 落盘异常。
4. runtime backup / restore / prune 失效。
5. benchmark 成功率退化。
6. hallucination rate 或 fallback steps 变差。

所以面试里可以直接说：

AI 工程项目的质量不能只靠 UI 联调，必须有协议层、运行态和质量趋势三层保护。

## 问题 4：`test_chat_stream_local.py` 最值得讲什么？

答案：

这组测试最值得讲的是它在保护 SSE 契约，而不是某个内部函数。

从当前测试内容看，它至少在保护：

1. `/api/chat/stream` 是否正常返回。
2. `content-type` 是否是 `text/event-stream`。
3. 是否发出了 `session_id`、`reasoning_start`、`answer_start`、`metadata`、`done`。
4. plan 模式是否会输出 `plan_preview`。
5. subagent 事件和 `artifact_patch` 是否会被透出。
6. `run_id / request_id / trace_id` 是否贯通。

代码锚点：

- [test_chat_stream_local.py](../../tests/test_chat_stream_local.py)
- [stream_mixin.py](../../backend/moyuan_web/services/chat/stream_mixin.py)
- [chatStreamParser.ts](../../frontend/src/services/api/chatStreamParser.ts)

## 问题 5：`test_api_smoke_local.py` 最值得讲什么？

答案：

它在保护“关键 API 还活着，并且合同没有明显跑偏”。

当前覆盖的重点包括：

1. model 列表。
2. session 创建、取消息、改模型、clear。
3. health / ready / live / metrics。
4. city 相关接口。
5. 基本 header 和错误合同。

这类测试的价值在于：

它能快速告诉你“系统主路径是不是整体还通着”。

## 问题 6：`test_runtime_data_lifecycle_unit.py` 为什么很值得讲？

答案：

因为很多人只会讲“我有聊天接口测试”，但不会讲“运行态怎么维护和恢复”。

这组测试覆盖了：

1. runtime backup 是否打包正确文件。
2. 自定义 sqlite checkpoint 路径是否能被记录。
3. postgres checkpoint 是否能被正确描述成外部快照。
4. restore 是否能恢复文件。
5. prune 是否能清理旧备份、旧 session、失败记录和 checkpoint。

这说明当前项目已经把运维侧运行数据也当成正式资产在治理。

## 问题 7：`agent_quality_gate.py` 在这个项目里到底在保护什么？

答案：

它保护的不是“代码是否能运行”，而是“行为指标是否还过线”。

[agent_quality_gate.py](../../scripts/agent_quality_gate.py) 当前会检查：

1. golden pass rate 最低值。
2. golden hallucination rate 最高值。
3. benchmark success rate 最低值。
4. benchmark hallucination rate 最高值。
5. benchmark fallback steps 总量。
6. 相对 baseline 的回归幅度。

这正好体现一个成熟观点：

AI 工程的回归，不应该只看单测红绿，还要看行为质量有没有退化。

## 问题 8：为什么这个项目要把 benchmark、golden eval、quality gate 分开？

答案：

因为它们回答的不是同一个问题。

| 验证手段 | 主要回答什么 |
| --- | --- |
| benchmark | 平均表现和整体趋势怎样 |
| golden eval | 关键样本是否还符合预期 |
| quality gate | 这些指标有没有低于发布门槛 |

这三层叠起来，才算比较完整的 AI 质量治理。

## 问题 9：如果我改了前端流式渲染，最小回归应该怎么选？

答案：

最小回归一般至少包括：

1. 前端 `lint`。
2. 前端 `build`。
3. 聊天流式主链手工验证一次。
4. [test_chat_stream_local.py](../../tests/test_chat_stream_local.py)。

如果改动涉及 `artifact_patch / metadata / plan_preview` 消费，还应该补：

1. 相关前端测试或手工对照。
2. 一次 plan 模式验证。

重点不是“跑得越多越好”，而是“回归动作要对准风险”。

## 问题 10：如果我改了 Backend route / service / repository，最小回归应该怎么选？

答案：

最小回归一般至少包括：

1. [test_api_smoke_local.py](../../tests/test_api_smoke_local.py)
2. [test_chat_stream_local.py](../../tests/test_chat_stream_local.py)
3. 相关 session 或 repository 单测
4. 一次真实本地接口 smoke

如果改的是持久化或 session 语义，再补：

1. `clear / list / delete / get messages` 的联动验证。
2. file 和 postgres 两条基线里的受影响路径。

## 问题 11：如果我改了 Agent 路由、执行、验证逻辑，最小回归应该怎么选？

答案：

Agent 侧改动通常风险更高，最小回归一般至少包括：

1. 相关单元 / 集成测试。
2. [test_chat_stream_local.py](../../tests/test_chat_stream_local.py)
3. 与 memory 或 checkpoint 相关的测试。
4. benchmark 或 golden eval 里受影响的一层。
5. 高风险时跑 quality gate。

因为 Agent 改动往往不是“能不能跑”的问题，而是“行为有没有悄悄变坏”。

## 问题 12：为什么 `build` 在这个项目里和 `lint` 一样重要？

答案：

因为前端很多问题并不会在纯 lint 阶段暴露。

例如：

1. SSR 相关问题。
2. 导入链问题。
3. 类型边界问题。
4. 某些只在 build 期暴露的 bundle 或配置问题。

所以前端相关改动只跑 lint，通常不够。

## 问题 13：如果线上现象是“能收到回答，但 `TravelPlanToolkit` 没内容”，我应该怎么排查？

答案：

最稳的排查顺序是：

1. 看 SSE 里有没有 `artifact_patch / metadata.artifact / done.artifact`。
2. 看 [chatStreamParser.ts](../../frontend/src/services/api/chatStreamParser.ts) 是否正确解析。
3. 看 [useChatRuntime.ts](../../frontend/src/components/chat-area/useChatRuntime.ts) 是否 merge 到 `artifactState`。
4. 看 [TravelPlanToolkit.tsx](../../frontend/src/components/TravelPlanToolkit.tsx) 是否优先消费 artifact。
5. 最后再看后端 plan preview 或 done 事件本身是否缺字段。

不要一开始就怀疑 Toolkit UI。

## 问题 14：如果现象是“接口 200，但前端一直 loading”，最推荐怎么排查？

答案：

最推荐顺序是：

1. 确认响应头是不是 `text/event-stream`。
2. 确认是否发出了 `done`。
3. 确认前端 `handleChatStreamLine(...)` 是否正确识别 `done`。
4. 确认 request 是否被 abort 或 reader 卡住。
5. 再看 `useChatRuntime` 有没有正确收口 `isStreaming`。

这种问题多数不是模型问题，而是协议收尾问题。

## 问题 15：如果现象是“session 被清了，但 memory 还影响后续回答”，怎么理解？

答案：

这往往说明你把 session 和 memory 混了。

正确理解是：

1. `clear_chat` 主要清 session 消息。
2. 当前实现也会尽量清 memory manager 的会话消息。
3. 但 memory 设计上本来就比 session 更长寿，具体还要看 memory manager 的持久化和摘要策略。

所以排查时要分别看：

- session repository
- `SessionLifecycleService.clear_chat(...)`
- memory manager 的写入和清理

## 问题 16：为什么“还没定位层级，就直接改代码”是很差的做法？

答案：

因为这个项目是多层协同系统。

如果你没先定位层级，最容易出现三种低效：

1. 在前端修后端问题。
2. 在 Agent 改协议问题。
3. 在 prompt 层修持久化或契约问题。

所以正确顺序永远是：

先定位哪一层坏了，再决定改哪里。

## 问题 17：一次像样的工程改动，最少应该补哪些信息？

答案：

最少应该能写出这 6 行：

1. 改动目标。
2. 影响层。
3. 涉及文件。
4. 风险点。
5. 验证动作。
6. 文档同步。

这 6 行本质上就是你对改动边界是否清楚的证明。

## 问题 18：如果让我用 1 分钟讲清楚这个项目的测试与质量思路，我该怎么讲？

答案：

我会这样讲：

这个项目的测试不是靠一套大而全命令兜底，而是按风险分层。聊天主链和 SSE 契约由 `test_chat_stream_local.py` 保护，关键 API 和错误合同由 `test_api_smoke_local.py` 等 smoke 用例保护，runtime backup/restore/prune 和 checkpoint 维护由 `test_runtime_data_lifecycle_unit.py` 保护，行为质量趋势再由 benchmark、golden eval 和 `agent_quality_gate.py` 保护。这样做的好处是每次改动都能按影响层选最小回归，而不是只靠手工点页面或者无差别跑全量。
