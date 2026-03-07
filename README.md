# ShuaiTravelAgent

ShuaiTravelAgent 是一个端到端 AI 旅行助手系统，覆盖多轮会话、工具调用、行程规划、预算评估与流式输出，采用三层架构：

- `frontend`: Next.js 16 + React 19 + TypeScript + antd
- `web`: FastAPI（SSE 流式 API）
- `agent`: LangChain + LangGraph（Planner + Tool Executor + Memory + Checkpoint）

## 项目能力总览

### 1. 旅行问答与规划能力
- 城市推荐（`search_cities`）
- 景点查询（`query_attractions`）
- 酒店查询（`query_hotels`）
- 预算估算（`calculate_budget`）
- 行程规划（`plan_itinerary`）
- 旅行建议（`get_travel_tips`）
- 天气查询（`get_weather`）

### 2. 三种对话模式
- `direct`: 直接回答（低延迟）
- `react`: Agent 推理 + 工具执行
- `plan`: 先输出可审计 `plan_preview`（plan_id + steps + explanation），再执行并生成答案

### 3. 实时流式体验（SSE）
- 支持 `reasoning_start/reasoning_chunk/reasoning_end`
- 支持 `plan_preview`、`tool_start/tool_end`
- 支持 token 级 `chunk`
- 末尾输出 `metadata`（tools_used、answer_length、plan_id、execution_stats）和 `done`

### 4. Agent 编排与执行优化
- LangGraph 状态机：`intent -> router -> plan -> execute -> answer`
- Planner 可解释：`plan_id`、`plan_explanation`、`depends_on`
- 工具执行增强：
  - 依赖拓扑调度（支持无依赖步骤并行）
  - 动态 SLA 超时（按工具类型）
  - 退避重试（exponential backoff）
  - 熔断保护（circuit breaker）
  - 结构化错误码（如 `TOOL_TIMEOUT`、`TOOL_EXECUTION_ERROR`、`CIRCUIT_OPEN`）
- 执行统计：每步耗时、状态、重试次数、错误码

### 5. Memory 与会话一致性
- 会话级记忆（最近消息 + 会话摘要 + 长期偏好画像）
- 偏好画像结构化存储（schema v2）：
  - `budget_hint`、`days_hint`、`people_hint`、`season_hint`
  - `interests`、`avoid_preferences`
- 画像冲突合并策略：
  - Source 优先级：`explicit > recent_inferred > inferred`
  - 同优先级下按置信度与最近更新时间覆盖
- `Session delete/clear` 会同步清理 memory，避免残留
- 流式中断时做补偿写入（assistant 侧 `INTERRUPTED` 标记）

### 6. Checkpoint 持久化与恢复
- LangGraph checkpoint 默认持久化到 SQLite（非进程内存）
- 按 `session_id -> thread_id` 绑定 checkpoint thread
- 支持进程重启后的多轮会话恢复
- 增量落盘（非全量快照）+ 周期性 compaction（保留最近 N 条）

## 系统架构

```text
Browser
  -> FastAPI /api/chat/stream (SSE)
    -> ChatService
      -> LangGraph TravelAgent
        -> Planner / Executor / Tools / LLM
      -> Session Repository (sessions.json)
      -> Agent Memory (agent_memory.json)
      -> LangGraph Checkpoint (langgraph_checkpoints.sqlite3)
```

## 核心目录

```text
ShuaiTravelAgent/
├── agent/                 # Agent 核心（LangGraph 编排、memory、checkpoint、tools）
│   └── src/graph/
│       ├── state.py
│       ├── nodes.py
│       ├── builder.py
│       ├── memory_integration.py
│       └── persistent_checkpointer.py
├── web/                   # FastAPI API 层（routes/services/repositories/storage）
├── frontend/              # Next.js 前端
├── tests/                 # 单测 + 集成测试
├── config/                # server / llm 配置
└── docs/                  # 架构、API、配置、测试说明
```

## 默认地址与端口

- Frontend: `http://localhost:33001`
- Web API: `http://localhost:38000`
- API 文档: `http://localhost:38000/rapidoc`
- 健康检查: `http://localhost:38000/api/health`

## 快速开始

1. 创建并激活 Python 3.13 环境

```bash
uv python install 3.13
uv venv .venv --python 3.13
.\.venv\Scripts\activate
```

2. 安装依赖

```bash
uv pip install -r requirements.txt
cd frontend && npm install
```

3. 准备 LLM 配置

```bash
copy config\\llm_config.yaml.example config\\llm_config.yaml
```

4. 启动

```bash
start_all.bat
```

或分别启动：

```bash
start_api.bat
start_frontend.bat
```

## 关键 API

### Chat
- `POST /api/chat/stream`
- 请求体：

```json
{
  "message": "帮我做一个北京三日行程，2人预算5000元",
  "session_id": "optional",
  "mode": "direct|react|plan"
}
```

### Session
- `POST /api/session/new`
- `GET /api/sessions`
- `DELETE /api/session/{session_id}`
- `PUT /api/session/{session_id}/name`
- `PUT /api/session/{session_id}/model`
- `GET /api/session/{session_id}/model`
- `POST /api/clear/{session_id}`

### Other
- `GET /api/models`
- `GET /api/models/{model_id}`
- `GET /api/health`
- `GET /api/ready`
- `GET /api/live`

## 运行时数据文件

- `data/sessions/sessions.json`: 会话数据
- `data/agent_memory.json`: Agent memory（摘要 + profile）
- `data/langgraph_checkpoints.sqlite3`: LangGraph checkpoint

## 关键环境变量

- `SHUAI_WEB_PORT`: API 启动端口覆盖
- `CORS_ORIGINS`: CORS 白名单覆盖
- `AGENT_CHECKPOINT_DB`: checkpoint SQLite 文件路径覆盖

## 测试

项目包含 API、流式、memory、checkpoint 恢复与执行优化测试。示例：

```bash
.\.venv\Scripts\python.exe -m pytest -q
```

## 文档导航

- [docs/README.md](docs/README.md)
- [docs/architecture/system-architecture.md](docs/architecture/system-architecture.md)
- [docs/architecture/data-storage.md](docs/architecture/data-storage.md)
- [docs/reference/api-reference.md](docs/reference/api-reference.md)
- [docs/reference/configuration-reference.md](docs/reference/configuration-reference.md)
- [docs/testing/testing-guide.md](docs/testing/testing-guide.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
