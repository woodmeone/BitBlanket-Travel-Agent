# 02. 聊天主链路与前端面试问答

这一篇只讲前端最值得面试时讲清楚的问题，不再按课程推进。

## 问题 1：一次聊天请求在前端到底是怎么发起并落到 UI 上的？

答案：

最稳的讲法是按真实主链说：

```text
page.tsx
  -> ChatArea.tsx
  -> useChatRuntime.ts
  -> chatClient.ts
  -> /api/chat/stream
  -> chatStreamParser.ts
  -> MessageList.tsx
  -> TravelPlanToolkit.tsx
```

更完整一点：

1. [page.tsx](../../frontend/src/app/page.tsx) 负责页面级装配。
2. [ChatArea.tsx](../../frontend/src/components/ChatArea.tsx) 是 chat workspace 的薄壳层。
3. [useChatRuntime.ts](../../frontend/src/components/chat-area/useChatRuntime.ts) 负责发请求、维护流式状态、合并 artifact、写最终消息。
4. [chatClient.ts](../../frontend/src/services/api/chatClient.ts) 负责建立 SSE 请求、超时、中断、重连。
5. [chatStreamParser.ts](../../frontend/src/services/api/chatStreamParser.ts) 负责把事件按通道拆开。
6. [MessageList.tsx](../../frontend/src/components/MessageList.tsx) 负责消息展示、推理折叠、诊断面板。
7. [TravelPlanToolkit.tsx](../../frontend/src/components/TravelPlanToolkit.tsx) 负责把最终结果继续加工成预算、对比、冲突、分享等产品能力。

## 问题 2：为什么这个项目前端要选 SSE，而不是一次性 JSON？

答案：

因为前端需要消费的不只是最终答案，还包括一串中间事件。

当前主链里前端会消费：

1. `session_id`
2. `stage`
3. `reasoning_start / reasoning_chunk / reasoning_end`
4. `tool_start / tool_end`
5. `plan_preview`
6. `subagent_start / subagent_end`
7. `artifact_patch`
8. `metadata`
9. `done`

所以这里不是“等接口回一个 JSON，再整体渲染”的场景，而是“服务端持续推送过程事件和最终内容”的场景。

代码锚点：

- [chatClient.ts](../../frontend/src/services/api/chatClient.ts)
- [chatStreamParser.ts](../../frontend/src/services/api/chatStreamParser.ts)
- [test_chat_stream_local.py](../../tests/test_chat_stream_local.py)

## 问题 3：为什么不是 WebSocket？

答案：

因为当前链路的核心需求是“服务端单向持续推送”。

SSE 在这个项目里的优势是：

1. 实现简单，直接基于 HTTP。
2. 对代理和现有 Web 设施更友好。
3. 已经足够覆盖 `stage / tool / metadata / answer` 这类事件流。

WebSocket 只有在下面场景变成主需求时才更值得上：

1. 前端持续反向发送控制指令。
2. 多人实时协同编辑同一个旅行方案。
3. 同一会话里有更复杂的双向长连接协议。

## 问题 4：`useChatRuntime.ts` 为什么是前端最核心的文件？

答案：

因为它几乎是“前端运行时总控”。

它主要做 8 件事：

1. 处理输入和发送动作。
2. 在没有 session 时先创建 session。
3. 发起 SSE 请求。
4. 消费 `stage / chunk / metadata / plan_preview / artifact_patch / done`。
5. 维护 `streamingMessage`、`streamingReasoning`、`planPreview`、`artifactState`、`runtimeLogs`。
6. 组织 stop、complete、fail 的状态收口。
7. 处理 session hydration 和 share/session 切换恢复。
8. 把最终消息和 diagnostics 落回正式消息列表。

代码锚点：

- [useChatRuntime.ts](../../frontend/src/components/chat-area/useChatRuntime.ts)
- [useStreamBuffer.ts](../../frontend/src/components/chat-area/useStreamBuffer.ts)
- [useArtifactRuntimeState.ts](../../frontend/src/components/chat-area/useArtifactRuntimeState.ts)
- [useChatRunState.ts](../../frontend/src/components/chat-area/useChatRunState.ts)
- [useChatSessionHydration.ts](../../frontend/src/components/chat-area/useChatSessionHydration.ts)

## 问题 5：为什么前端要区分 `streamingMessage` 和最终 `messages`？

答案：

因为两者生命周期根本不同。

`streamingMessage` 的特点：

1. 还在持续增长。
2. 内容可能还不完整。
3. 可能会被 stop、error、done 中断或覆盖。
4. 主要服务“当前流式体验”。

最终 `messages` 的特点：

1. 是已经完成或明确收口的持久态消息。
2. 会和 diagnostics、artifact、reasoning 摘要一起挂到 assistant message 上。
3. 会参与 session 恢复、历史列表和后续 continue/refine。

如果两者混在一起，最容易出现的问题是：

1. UI 抖动。
2. 中断后留下半条正式消息。
3. `metadata` 和 `artifact` 无法在正确时机合并。

## 问题 6：为什么前端还要单独维护 `streamingReasoning`、`planPreview`、`artifactState`、`metadata`？

答案：

因为这些都不是“正文字符串”的一部分。

最推荐的讲法是：

- `streamingReasoning`
  服务于过程可见性。
- `planPreview`
  服务于计划模式下的结构化预览。
- `artifactState`
  服务于 artifact patch 的增量合并和结构化结果消费。
- `metadata`
  服务于 diagnostics、`run_id`、验证结果、工具统计等调试信息。

这说明前端在这个项目里不是单纯的“文本渲染层”，而是运行态解释层和结构化消费层。

## 问题 7：`chatClient.ts` 和 `chatStreamParser.ts` 各自到底在解决什么问题？

答案：

### `chatClient.ts`

它解决的是“连接”问题：

1. 如何发起请求。
2. 如何设置超时。
3. 如何处理中断。
4. 如何做有限重连。
5. 如何把 `X-Request-ID / X-Trace-ID` 带给后端。

### `chatStreamParser.ts`

它解决的是“协议解析”问题：

1. 如何按行解析 SSE 数据。
2. 如何区分事件类型。
3. 如何把 `session_id / stage / reasoning / plan_preview / artifact_patch / metadata / done` 分发到独立回调。
4. 如何把 malformed chunk 忽略掉，而不是让整个前端崩掉。

代码锚点：

- [chatClient.ts](../../frontend/src/services/api/chatClient.ts)
- [chatStreamParser.ts](../../frontend/src/services/api/chatStreamParser.ts)

## 问题 8：为什么 `ChatArea.tsx` 现在反而变“薄”了？

答案：

因为当前实现已经把运行态逻辑下沉到 hooks 和协作器里了。

[ChatArea.tsx](../../frontend/src/components/ChatArea.tsx) 现在更像一个装配入口：

1. 组织 tab。
2. 连接 `ChatConversationView`、`CityExplorer`、`SystemStatusPanel`。
3. 连接 `ChatComposer`。
4. 从 `useChatRuntime` 拿状态和动作。

真正的“前端运行时复杂度”已经下沉到：

1. [useChatRuntime.ts](../../frontend/src/components/chat-area/useChatRuntime.ts)
2. [useStreamBuffer.ts](../../frontend/src/components/chat-area/useStreamBuffer.ts)
3. [useArtifactRuntimeState.ts](../../frontend/src/components/chat-area/useArtifactRuntimeState.ts)
4. [useChatRunState.ts](../../frontend/src/components/chat-area/useChatRunState.ts)
5. [useChatSessionHydration.ts](../../frontend/src/components/chat-area/useChatSessionHydration.ts)

这是一种典型的“视图装配”和“运行时逻辑”分离。

## 问题 9：`MessageList.tsx` 为什么不是简单的消息渲染器？

答案：

因为它不只是把字符串打印出来。

当前它至少承接了 4 件更工程化的事情：

1. Markdown 和表格展示。
2. `<think>` 或 reasoning 信息的折叠与分区。
3. diagnostics 的消息级展示。
4. 和 `TravelPlanToolkit` 的配合，让最终 assistant message 变成“文本 + 结构化结果 + 诊断”的组合体。

所以这层可以讲成：

前端不只是“显示结果”，而是在“解释结果”。

## 问题 10：`TravelPlanToolkit.tsx` 为什么是这个项目前端最值得讲的一层？

答案：

因为它最能证明这不是一个普通聊天页面。

它的价值不在“卡片好不好看”，而在：

1. 把大模型的文本结果继续加工成可操作的旅行结果。
2. 优先消费结构化 artifact，而不是脆弱地二次解析长文本。
3. 支持预算、对比、冲突、候选池、路线预览、导出、分享、继续 refine。

当前更贴近代码的说法是：

- [TravelPlanToolkit.tsx](../../frontend/src/components/TravelPlanToolkit.tsx) 主要负责装配。
- 动作编排已经下沉到 [useTravelPlanToolkitActions.ts](../../frontend/src/components/travel-plan-toolkit/useTravelPlanToolkitActions.ts)。
- 结构化结果和 delivery bundle 相关逻辑下沉到 `travel-plan-toolkit/shared/`。

这说明前端已经从“展示层”变成了“结果产品化层”。

## 问题 11：什么叫这个项目当前前端是 `artifact-first`？

答案：

意思是前端优先消费结构化 artifact，而不是把长文本当唯一真相源。

最值得记住的 3 个点：

1. [chatStreamParser.ts](../../frontend/src/services/api/chatStreamParser.ts) 会显式拆出 `artifact_patch`、`plan_preview.artifact`、`metadata.artifact`、`done.artifact`。
2. [useChatRuntime.ts](../../frontend/src/components/chat-area/useChatRuntime.ts) 会在一次 run 内持续 merge artifact patch。
3. [TravelPlanToolkit.tsx](../../frontend/src/components/TravelPlanToolkit.tsx) 优先消费 artifact，再回退到文本解析。

面试里可以直接把这点讲成：

这个前端不是“正文驱动”，而是“结构化结果驱动”。

## 问题 12：如果前端这层出了问题，最推荐按什么顺序排查？

答案：

最推荐按下面顺序：

1. 先看有没有收到 SSE 响应。
2. 再看 `chatStreamParser.ts` 是否正确解析事件。
3. 再看 `useChatRuntime.ts` 是否把事件写进了正确状态。
4. 再看 `MessageList.tsx` 或 `TravelPlanToolkit.tsx` 是否正确消费状态。
5. 最后再看样式、布局、交互细节。

按现象细分：

- 没有阶段提示：
  先查 `stage` 事件。
- 没有正文增长：
  先查 `chunk` 和 stream buffer。
- 没有推理展示：
  先查 `reasoning_*`。
- 最终消息没落盘：
  先查 `onComplete` 和最终合并逻辑。
- Toolkit 没识别结构化结果：
  先查 `artifact`、`artifact_patch` 和 `metadata.artifact`。

## 问题 13：前端这层在面试里最容易被追问什么？

答案：

最常见的就是这 6 个：

1. 为什么选 SSE，不是 JSON / WebSocket。
2. 为什么 `useChatRuntime.ts` 这么重。
3. 为什么 `streamingMessage` 和 `messages` 要分开。
4. 为什么前端还要单独维护 `artifactState`。
5. 为什么 `TravelPlanToolkit` 不是可有可无的 UI。
6. 如果要支持多条并发流，该怎么改状态模型。

## 问题 14：如果让我用前端视角 1 分钟讲这个项目，我该怎么讲？

答案：

可以直接这么讲：

“前端这层最有价值的不是页面本身，而是把 AI 运行过程和结果都产品化了。它通过 `useChatRuntime`、`chatClient`、`chatStreamParser` 消费 `/api/chat/stream` 的 SSE 事件，把 `stage / reasoning / tool / metadata / artifact` 拆成不同状态通道，再用 `MessageList` 和 `TravelPlanToolkit` 把文本结果、过程诊断和结构化旅行方案一起交给用户。这里最关键的工程点是 SSE 协议消费、临时流式态和正式消息态分离，以及 artifact-first 的结构化结果渲染。”

## 问题 15：如果我只剩 10 分钟准备前端面试，这一篇最该回看什么？

答案：

按这个顺序看：

1. 本篇的问题 1、2、5、10、11。
2. [useChatRuntime.ts](../../frontend/src/components/chat-area/useChatRuntime.ts)
3. [chatClient.ts](../../frontend/src/services/api/chatClient.ts)
4. [chatStreamParser.ts](../../frontend/src/services/api/chatStreamParser.ts)
5. [TravelPlanToolkit.tsx](../../frontend/src/components/TravelPlanToolkit.tsx)

这 5 处足够支撑大多数前端和全栈面试里的追问。
