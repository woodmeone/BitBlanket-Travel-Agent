# 03. Backend API、Session 与持久化面试问答

这一篇只讲 `backend/` 最值得面试时讲清楚的问题。

## 问题 1：这个项目里的 Backend API 到底在解决什么问题？

答案：

Backend 不是一个“帮前端转发模型”的薄代理，而是协议层、编排层和持久化边界层。

它主要负责 4 件事：

1. 用 FastAPI 对外暴露稳定的 HTTP / SSE 契约。
2. 组织聊天主链、session 生命周期和错误合同。
3. 把 Agent 运行结果规范化成前端能消费的事件流。
4. 把会话数据收口到 `repository + persistence backend` 这一层。

代码锚点：

- [chat.py](../../backend/moyuan_web/routes/chat.py)
- [chat_service.py](../../backend/moyuan_web/services/chat_service.py)
- [session.py](../../backend/moyuan_web/routes/session.py)

## 问题 2：为什么这层要坚持 `route -> service -> repository -> persistence`？

答案：

因为这 4 层回答的是 4 个不同问题：

| 分层 | 它回答什么问题 |
| --- | --- |
| route | HTTP 请求怎么进来、怎么校验、怎么返回 |
| service | 这次业务流程怎么编排 |
| repository | 业务对象怎样被读写 |
| persistence | 文件或数据库怎样真正存储 |

如果把这几层混在一起，最常见的后果就是：

1. route 层越来越胖。
2. 更换存储实现时牵一发而动全身。
3. session、chat、share、artifact 这些边界会越来越乱。

## 问题 3：聊天主链到 Backend 后，第一站是什么？

答案：

第一站是 [chat.py](../../backend/moyuan_web/routes/chat.py) 的 `stream_chat`。

它做的事很克制：

1. 接收 [ChatRequest](../../backend/moyuan_web/api/schemas/chat.py)。
2. 从 [service_resolver.py](../../backend/moyuan_web/routes/service_resolver.py) 取 `ChatService`。
3. 从 `fastapi_request.state` 里拿 `request_id / trace_id`。
4. 返回 `StreamingResponse`，并把 media type 定成 `text/event-stream`。

这正好体现 route 层原则:

route 负责协议入口，不负责业务编排。

## 问题 4：为什么 route 层应该尽量薄？

答案：

因为一旦把聊天编排、session 处理、memory、副作用都塞进 route，后面会同时失去三件事：

1. 可测试性。
2. 可复用性。
3. 可维护性。

当前实现里 route 层基本只做：

1. 解析参数。
2. 解析依赖。
3. 统一错误返回。
4. 返回标准响应对象。

业务复杂度都下沉到 service。

代码锚点：

- [chat.py](../../backend/moyuan_web/routes/chat.py)
- [session.py](../../backend/moyuan_web/routes/session.py)
- [service_resolver.py](../../backend/moyuan_web/routes/service_resolver.py)

## 问题 5：`service_resolver.py` 和 `bootstrap_services.py` 各自的角色是什么？

答案：

- [service_resolver.py](../../backend/moyuan_web/routes/service_resolver.py)
  解决的是“route 层怎么拿到服务实例”。
- [bootstrap_services.py](../../backend/moyuan_web/bootstrap_services.py)
  解决的是“这些服务实例怎样被注册、构造和复用”。

最应该记住的是：

1. route 不直接 `new ChatService()`。
2. 服务的注册入口在 `register_default_services(...)`。
3. `provide_session_repository()` 会根据配置切 `file / postgres`。

这说明当前项目已经不是“随手 import 一个类来用”的阶段，而是有明确依赖装配面。

## 问题 6：`ChatService` 为什么是 Backend 里最核心的服务？

答案：

因为它是聊天编排总入口。

[chat_service.py](../../backend/moyuan_web/services/chat_service.py) 当前主要负责：

1. 延迟初始化 LLM、tools、memory manager、`AgentRuntime`。
2. 校验 mode。
3. 衔接 session 与消息持久化。
4. 调 Agent 并把内部运行事件转成标准流式事件。
5. 记录健康窗口、失败率、fallback 率等诊断数据。

面试里最稳的说法是：

`ChatService` 不拥有全部业务细节，但它拥有“把聊天跑完整”的编排责任。

## 问题 7：为什么 `ChatService` 和 `SessionService` 不能合成一个服务？

答案：

因为它们的关注点不同。

- `ChatService`
  负责一次聊天运行的编排。
- [SessionService](../../backend/moyuan_web/services/session_service.py)
  负责 session 生命周期 facade。
- [SessionLifecycleService](../../backend/moyuan_web/services/session/lifecycle_service.py)
  负责 CRUD、清理和 memory 副作用。

如果把它们硬合在一起，会出现两个问题：

1. 聊天主链和会话管理耦合过深。
2. session 相关接口会被流式逻辑污染。

## 问题 8：session 在当前实现里不只是“消息列表”，还包括什么？

答案：

至少还包括：

1. `session_id`
2. `created_at`
3. `last_active`
4. `message_count`
5. `name`
6. `model_id`
7. `user_preferences`

这一点在 [file_session_repository.py](../../backend/moyuan_web/repositories/file_session_repository.py) 和 [session_repository_postgres.py](../../backend/moyuan_web/repositories/session_repository_postgres.py) 里都很清楚。

所以面试里不要把 session 讲成“只是一个 messages 数组”。

## 问题 9：`SessionLifecycleService` 最值得讲的实现点是什么？

答案：

它把 CRUD 和 memory 副作用绑在了一起，但又没有把 memory 逻辑硬写死。

当前实现里最值得讲的点有 3 个：

1. `create_session(...)` 会带默认模型和默认名称。
2. `clear_chat(...)` 不只清 repository，还会尽量清 memory manager。
3. `_get_memory_manager()` 是 lazy resolve，避免轻操作引入重依赖。

代码锚点：

- [lifecycle_service.py](../../backend/moyuan_web/services/session/lifecycle_service.py)

## 问题 10：repository 和 persistence 的边界，当前代码是怎么体现的？

答案：

当前代码里 repository 已经直接承接大部分业务语义，而 persistence 更偏底层数据库构造和 schema。

最直观的例子：

1. [FileSessionRepository](../../backend/moyuan_web/repositories/file_session_repository.py)
   负责 session 的创建、更新、排序、过期清理，同时也负责文件原子写。
2. [PostgresSessionRepository](../../backend/moyuan_web/repositories/session_repository_postgres.py)
   负责 session 语义读写，但底层 engine 和 schema 依赖 [database.py](../../backend/moyuan_web/persistence/database.py)。

所以当前项目的真实情况更准确的讲法是：

repository 已经包含了一部分 persistence 适配责任，但底层 SQL backend 的构造仍然收口在 `backend/moyuan_web/persistence/`。

## 问题 11：文件存储版本最值得讲什么？

答案：

最值得讲的是它不是“随便写个 JSON 文件”。

[file_session_repository.py](../../backend/moyuan_web/repositories/file_session_repository.py) 里至少做了这些工程保护：

1. `_atomic_write_json(...)`
   用 temp file + `os.replace` 做原子写。
2. `.bak` 备份文件。
3. `_load_from_file()`
   主文件坏了会尝试从备份恢复。
4. `list_all(...)`
   会按 `last_active` 排序，并过滤空会话。
5. `cleanup_expired(...)`
   支持按时间清理过期 session。

这说明 file baseline 不是玩具实现，而是本地开发和轻量部署的兼容基线。

## 问题 12：Postgres 版本最值得讲什么？

答案：

最值得讲的是它不是简单把 JSON 搬进数据库，而是已经把 session 元信息和消息明细分开了。

[session_repository_postgres.py](../../backend/moyuan_web/repositories/session_repository_postgres.py) 里可以看到：

1. `sessions_table` 保存 session 元信息。
2. `session_messages_table` 保存按 `sequence` 排序的消息明细。
3. `_replace_messages_sync(...)` 会重建消息行。
4. `ensure_schema(...)` 保证 SQL 基线表存在。

这说明 postgres baseline 是为了更稳定的多环境持久化，不只是为了“看起来更高级”。

## 问题 13：为什么“加一个字段”在这层通常是跨层改动？

答案：

因为一个新字段通常会同时影响：

1. route 的请求或响应 schema。
2. service 的编排逻辑。
3. repository 的读写。
4. file / postgres 两套持久化实现。
5. 前端对这个字段的消费。
6. 测试断言。

所以面试里可以直接说：

在这种分层系统里，“新增字段”本质上是契约改动，不是局部 `dict` 改动。

## 问题 14：`request_id / trace_id / run_id` 三者在 Backend 里怎么区分？

答案：

最稳的讲法是按时间和边界区分：

| 字段 | 作用 |
| --- | --- |
| `request_id` | 这次 HTTP 请求的请求级标识 |
| `trace_id` | 跨日志和跨链路的追踪标识 |
| `run_id` | 这次 Agent 运行的执行标识 |

当前实现里：

1. route 从 `fastapi_request.state` 拿 `request_id / trace_id`。
2. stream run 自己生成 `run_id`。
3. 这些标识会进入 SSE `session_id / metadata / done` 事件。

代码锚点：

- [chat.py](../../backend/moyuan_web/routes/chat.py)
- [stream_mixin.py](../../backend/moyuan_web/services/chat/stream_mixin.py)
- [test_chat_stream_local.py](../../tests/test_chat_stream_local.py)

## 问题 15：为什么聊天接口要返回 SSE，而不是普通 JSON？

答案：

因为 Backend 输出的不是一份最终结果，而是一串运行过程。

[stream_mixin.py](../../backend/moyuan_web/services/chat/stream_mixin.py) 里能看到当前至少会发出：

1. `session_id`
2. `reasoning_start / reasoning_chunk / reasoning_end`
3. `stage`
4. `tool_start / tool_end`
5. `plan_preview`
6. `subagent_start / subagent_end`
7. `artifact_patch`
8. `metadata`
9. `done`

所以这层的真实职责是“把内部运行态规范化成公共事件协议”。

## 问题 16：plan 模式在 Backend 里是怎么体现的？

答案：

`plan` 模式不是只换一个 prompt，而是会先走 plan preview 协调。

在 [stream_mixin.py](../../backend/moyuan_web/services/chat/stream_mixin.py) 里：

1. `mode == "plan"` 时会先调用 `_normalize_plan_preview_events(...)`。
2. 这个逻辑由 [plan_preview_coordinator.py](../../backend/moyuan_web/services/chat/plan_preview_coordinator.py) 负责。
3. plan preview 会输出 `plan_id`、`intent`、`validation_status`、`steps`、`artifact` 等结构化信息。

这正好支撑前端的 `artifact-first` 和 `TravelPlanToolkit`。

## 问题 17：如果我要从 Backend 视角排查一次聊天问题，推荐顺序是什么？

答案：

最稳的顺序是：

1. 先确认 route 是否成功返回 `text/event-stream`。
2. 再看 `ChatService` 是否正常初始化。
3. 再看 `stream_mixin.py` 是否把内部事件规范化出来。
4. 再看 repository 是否正确持久化了消息和 session。
5. 最后再看 Agent 本体是否给出了异常或空结果。

不要一上来就怀疑 prompt。

## 问题 18：如果让我用 1 分钟讲清楚 Backend 这层，我该怎么讲？

答案：

我会这样讲：

这个项目的 Backend 不是模型代理层，而是协议与编排层。路由层只负责 HTTP / SSE 入口和错误合同，`ChatService` 负责把 session、memory、AgentRuntime 和 SSE 事件编排起来，`SessionService` 负责会话生命周期，底层通过 `FileSessionRepository` 和 `PostgresSessionRepository` 提供双持久化基线。这样做的好处是前端拿到的是稳定事件流，Agent 拿到的是清晰边界，而存储实现又能独立演进。
