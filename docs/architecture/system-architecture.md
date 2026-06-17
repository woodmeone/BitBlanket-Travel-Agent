# System Architecture

本文只描述当前已落地的系统结构。涉及阶段计划、历史路线图和已关闭执行稿，请回到 [../README.md](../README.md) 的“路线图与历史归档”区查看，不要把那些文档当成当前实现真相源。

## 总体结构

moyuan-travel-agent 由三层组成：

1. Frontend：Next.js 对话与旅行工具 UI
2. Backend API：FastAPI 路由、服务编排、startup checks、observability
3. Agent：LangGraph 驱动的意图识别、计划、执行、验证链路

```text
Browser
  -> FastAPI /api/chat/stream (SSE)
    -> RequestLogging / RateLimit / Timeout Middleware
      -> ChatService
        -> AgentRuntime
           -> Supervisor runtime graph
           -> Research / Planning / Verification Subagents
              -> intent -> strategy -> plan -> execute -> verify -> answer -> self_check
           -> Skills Registry / Artifact Builders
      -> Session / Memory / Checkpoint Storage
      -> Health / Metrics / Ready endpoints
```

## 分层职责

### Frontend (`frontend/`)

负责把 Agent 的流式能力变成真正可交互的旅行产品界面。

核心职责：

- 对话输入、约束面板、模式切换
- 流式展示 reasoning / stage / tool event / answer
- 为 REST 与 SSE 请求生成 `X-Request-ID / X-Trace-ID`
- 行程结果二次结构化：每日卡片、预算滑杆、对比、冲突检测、导出图片、分享
- 城市探索、候选池、对比池与继续追问入口
- 调用地图预览、分享短链、城市详情等 API

关键文件：

- [`frontend/src/app/page.tsx`](../../frontend/src/app/page.tsx)
- [`frontend/src/components/ChatArea.tsx`](../../frontend/src/components/ChatArea.tsx)
- [`frontend/src/components/MessageList.tsx`](../../frontend/src/components/MessageList.tsx)
- [`frontend/src/components/TravelPlanToolkit.tsx`](../../frontend/src/components/TravelPlanToolkit.tsx)
- [`frontend/src/components/CityExplorer.tsx`](../../frontend/src/components/CityExplorer.tsx)
- [`frontend/src/services/api/chatClient.ts`](../../frontend/src/services/api/chatClient.ts)
- [`frontend/src/services/api/chatStreamParser.ts`](../../frontend/src/services/api/chatStreamParser.ts)
- [`frontend/next.config.js`](../../frontend/next.config.js)

### Backend API (`backend/moyuan_web/`)

负责把前端请求组织成稳定的服务入口，并承接会话、城市、分享、健康状态、metrics 与 startup readiness。

核心职责：

- 暴露 `/api/chat/stream` SSE 接口
- 管理 `session`、`model`、`city`、`map`、`share`、`health`
- 在中间件中注入 `request_id / trace_id`
- 汇总工具健康、intent 聚合与可观测性结果
- 在启动时执行 readiness checks
- 暴露 `/api/ready` 与 `/api/metrics`

关键文件：

- [`backend/moyuan_web/main.py`](../../backend/moyuan_web/main.py)
- [`backend/moyuan_web/middleware/__init__.py`](../../backend/moyuan_web/middleware/__init__.py)
- [`backend/moyuan_web/observability.py`](../../backend/moyuan_web/observability.py)
- [`backend/moyuan_web/startup_checks.py`](../../backend/moyuan_web/startup_checks.py)
- [`backend/moyuan_web/routes/chat.py`](../../backend/moyuan_web/routes/chat.py)
- [`backend/moyuan_web/routes/health.py`](../../backend/moyuan_web/routes/health.py)
- [`backend/moyuan_web/services/chat_service.py`](../../backend/moyuan_web/services/chat_service.py)

### Agent (`agent/travel_agent/`)

负责真正的推理执行逻辑，把用户问题转成工具调用、验证链路和最终答案。

核心职责：

- `AgentRuntime` 作为应用层入口，屏蔽底层 graph 细节
- Supervisor runtime 层收口当前主图，并为后续 subagent 拆分预留边界
- `Research / Planning / Verification` 三个 subagent 已经作为最小实现接入运行时
- Skill Registry 把领域能力与底层 tools 解耦
- Artifact Builders 产出结构化行程结果，减少前端对长文本二次解析的依赖
- 计划生成、工具执行、验证、自检仍暂时运行在当前 LangGraph 主图中
- 会话记忆、摘要、偏好画像与 checkpoint 持久化继续沿用现有机制

关键文件：

- [`agent/travel_agent/runtime/agent_runtime.py`](../../agent/travel_agent/runtime/agent_runtime.py)
- [`agent/travel_agent/supervisor/builder.py`](../../agent/travel_agent/supervisor/builder.py)
- [`agent/travel_agent/supervisor/nodes.py`](../../agent/travel_agent/supervisor/nodes.py)
- [`agent/travel_agent/subagents/registry.py`](../../agent/travel_agent/subagents/registry.py)
- [`agent/travel_agent/subagents/research.py`](../../agent/travel_agent/subagents/research.py)
- [`agent/travel_agent/subagents/planning.py`](../../agent/travel_agent/subagents/planning.py)
- [`agent/travel_agent/subagents/verification.py`](../../agent/travel_agent/subagents/verification.py)
- [`agent/travel_agent/skills/registry.py`](../../agent/travel_agent/skills/registry.py)
- [`agent/travel_agent/artifacts/models.py`](../../agent/travel_agent/artifacts/models.py)
- [`agent/travel_agent/graph/builder.py`](../../agent/travel_agent/graph/builder.py)
- [`agent/travel_agent/graph/nodes.py`](../../agent/travel_agent/graph/nodes.py)
- [`agent/travel_agent/graph/runtime_config.py`](../../agent/travel_agent/graph/runtime_config.py)
- [`agent/travel_agent/graph/memory_integration.py`](../../agent/travel_agent/graph/memory_integration.py)
- [`agent/travel_agent/graph/persistent_checkpointer.py`](../../agent/travel_agent/graph/persistent_checkpointer.py)
- [`agent/travel_agent/tools/travel_tools.py`](../../agent/travel_agent/tools/travel_tools.py)

## 运行时速查

### 对话主链

```text
Browser / ChatArea
  -> chatClient.ts
  -> chatStreamParser.ts
  -> FastAPI middleware
  -> routes/chat.py
  -> ChatService.stream_chat
  -> AgentRuntime
  -> Supervisor runtime graph / subagents / skills / artifacts
  -> Session / Memory / Checkpoint
  -> SSE(metadata / diagnostics / artifact patch)
  -> Frontend render + structured toolkit
```

这条主链里最值得记住的只有 4 点：

- 前端对 REST 和 SSE 都会生成 `request_id / trace_id`。
- 中间件负责绑定上下文、打日志、记 metrics、返回 trace headers。
- `ChatService` 通过 `AgentRuntime` 进入 Agent 应用层，而不是直接调用 graph builder。
- 前端最终消费的不只是文本，还包括 `subagent_*`、`artifact_patch`、`metadata` 这类结构化事件。

### readiness、SSE 与可观测性

| 主题 | 当前实现重点 |
| --- | --- |
| readiness | FastAPI lifespan 会跑 `startup_checks.py`，把 readiness snapshot 写到 `app.state`，并通过 `/api/ready` 与 `moyuan_readiness_state` 暴露。 |
| SSE 事件 | 前端主要消费 `session_id`、`reasoning_*`、`plan_preview`、`stage`、`tool_*`、`subagent_*`、`artifact_patch`、`answer_start`、`chunk`、`metadata`、`error`、`done`。 |
| trace 约定 | SSE payload 会带 `request_id / trace_id`，响应头也会带 `X-Request-ID / X-Trace-ID`。 |
| 结构化日志 | 入口在 [`backend/moyuan_web/observability.py`](../../backend/moyuan_web/observability.py)，重点事件包括 `startup_validation`、`http_request*`、`chat_stream_*`。 |
| Prometheus | 默认关注 `moyuan_http_requests_total`、`moyuan_http_request_duration_seconds`、`moyuan_http_in_flight_requests`、`moyuan_chat_stream_requests_total`、`moyuan_sse_events_total`、`moyuan_readiness_state`，出口是 `GET /api/metrics`。 |

## 持久化与运行数据

默认会落盘以下数据：

- `data/sessions/sessions.json`
- `data/agent_memory.json`
- `data/langgraph_checkpoints.sqlite3`
- `data/runtime_failure_clusters.jsonl`

详细说明见 [data-storage.md](data-storage.md)。

## 部署资产

当前本地与容器启动的核心资产：

- [`deploy/compose/compose.yaml`](../../deploy/compose/compose.yaml)
- [`deploy/docker/backend.Dockerfile`](../../deploy/docker/backend.Dockerfile)
- [`deploy/docker/frontend.Dockerfile`](../../deploy/docker/frontend.Dockerfile)
- [`backend/config/server_config.yaml.example`](../../backend/config/server_config.yaml.example)

## 当前设计重点

### 1. `AgentRuntime` 已成为应用层稳定入口

- `ChatService` 不再直接依赖 `graph.builder` 里的多个函数
- `AgentRuntime` 成为 Backend 层与 Agent 内核之间的稳定入口
- `SupervisorTravelAgentGraph` 和 `SupervisorNodes` 已接管当前 supervisor runtime 主链
- `SkillRegistry` 与 `TripPlanArtifact` 先作为新架构承载层落地

这一步的重点不是把多 Agent 一次性做完，而是先把运行入口、skill registry、artifact payload 和 subagent 注册表变成代码里的真实边界。

### 2. 最小 subagent 与 artifact-first 消费已经接通

当前已经落地：

- `ResearchSubagent`
- `PlanningSubagent`
- `VerificationSubagent`

它们目前仍复用现有 LangGraph 主图和 skills/tool 体系，但已经具备：

- 独立目录和注册表
- 独立技能映射
- 独立 SSE 事件
- 独立 artifact patch 能力

### 3. readiness、observability 与前端结构化消费已收口

项目现在不再只靠 `/api/health` 证明系统可用，而是增加：

- startup validation
- `/api/ready`
- `fail_fast_validation`

- 请求头中的 `X-Request-ID / X-Trace-ID`
- 中间件日志与 `ChatService` 结构化日志
- SSE payload 中的 `request_id / trace_id`
- pytest marker 分层、benchmark、golden eval、quality gate 和 GitHub Step Summary

## 相关文档

- [../architecture/infrastructure-foundations.md](infrastructure-foundations.md)
- [../reference/api-reference.md](../reference/api-reference.md)
- [../reference/project-structure.md](../reference/project-structure.md)
- [../testing/testing-guide.md](../testing/testing-guide.md)

## 前端结构化消费与会话恢复

当前前端已经直接消费应用层结构化 payload，而不是只靠长文本二次解析：

| 前端模块 | 当前职责 |
| --- | --- |
| [`chatClient.ts`](../../frontend/src/services/api/chatClient.ts) | 发送 SSE 请求并维护请求生命周期。 |
| [`chatStreamParser.ts`](../../frontend/src/services/api/chatStreamParser.ts) | 解析 `subagent_*`、`artifact_patch`、`metadata`、`done` 等结构化事件。 |
| [`ChatArea.tsx`](../../frontend/src/components/ChatArea.tsx) | 合并增量 artifact patch，记录 subagent timeline，并把最终 diagnostics 持久化到 assistant message。 |
| [`MessageList.tsx`](../../frontend/src/components/MessageList.tsx) | 渲染 artifact-backed diagnostics 和消息级 subagent trace。 |
| [`TravelPlanToolkit.tsx`](../../frontend/src/components/TravelPlanToolkit.tsx) | 优先消费结构化 artifact metadata，只把文本解析保留为次级 fallback。 |

会话级恢复也已经走结构化路径：

1. `ChatService` 在 assistant 最终消息中持久化 `diagnostics`。
2. `diagnostics` 内包含 `artifact` 与 `subagentEvents`。
3. `GET /api/session/{session_id}/messages` 对前端暴露公开消息视图。
4. `AppContext` 在刷新或切换会话时重新拉取消息。
5. `MessageList` / `TravelPlanToolkit` 直接复用持久化后的结构化结果。

这意味着 `artifact-first` 已经从“仅流式运行时可见”升级成“会话级可恢复状态”。
