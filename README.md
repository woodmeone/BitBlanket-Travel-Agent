# ShuaiTravelAgent

ShuaiTravelAgent 是一个端到端 AI 旅行助手系统，提供前端对话体验、FastAPI Web API、LangGraph Agent 推理执行链路。

## 1. 技术栈与端口

- 前端：Next.js 16 + React 19 + TypeScript + antd
- Web API：FastAPI
- Agent：LangChain 1.x + LangGraph 1.x
- 默认模型：MiniMax M2.5（Anthropic 兼容接口）

- Frontend: `http://localhost:33001`
- API: `http://localhost:38000`
- API Docs: `http://localhost:38000/rapidoc`
- Health: `http://localhost:38000/api/health`

## 2. 系统核心能力

### 2.1 对话能力

- 三种对话模式：`direct`（直答）、`react`（推理+工具）、`plan`（先出计划再执行）
- SSE 实时流式输出：支持思考过程、工具事件、答案分片、执行元数据
- 多会话管理：新建、重命名、删除、清空、按会话切换模型

### 2.2 旅行工具能力

- 城市推荐：`search_cities`
- 景点查询：`query_attractions`
- 酒店查询：`query_hotels`
- 预算估算：`calculate_budget`
- 行程规划：`plan_itinerary`
- 旅行建议：`get_travel_tips`
- 天气查询：`get_weather`

### 2.3 工程级保障

- 执行控制：并发上限、超时、重试、熔断、预算限制
- 数据时效：支持 stale 检测与刷新策略
- 安全防护：工具参数校验、提示词注入拦截、敏感参数脱敏
- 可观测性：`/api/health/tools` + `intent` 聚合 SLO 指标
- 持久化恢复：LangGraph checkpoint（SQLite）+ 会话与记忆文件落盘

## 3. 架构设计（模块与调用链）

```text
Browser
  -> FastAPI /api/chat/stream (SSE)
    -> ChatService
      -> LangGraph TravelAgent
         -> intent -> strategy -> plan -> execute -> verify -> answer -> self_check
      -> SessionRepository (sessions.json)
      -> AgentMemoryManager (agent_memory.json)
      -> PersistentSqliteSaver (langgraph_checkpoints.sqlite3)
```

### 3.1 前端模块设计（`frontend/src`）

- `app/page.tsx`：整体布局（侧边栏 + 主聊天区）
- `components/Sidebar.tsx`：会话管理、模型切换、历史会话列表
- `components/ChatArea.tsx`：输入发送、流式接收、停止生成、模式切换
- `components/MessageList.tsx`：消息渲染、推理/诊断信息展示
- `context/AppContext.tsx`：全局状态（会话、模型、消息、流式状态）
- `services/api.ts`：REST + SSE 客户端，含重连、超时、中断控制

### 3.2 Web API 模块设计（`web/shuai_web`）

- `routes/chat.py`：`/api/chat/stream`，SSE 入口
- `services/chat_service.py`：聊天编排核心（模式路由、SSE 事件输出、持久化）
- `routes/session.py` + `services/session_service.py`：会话生命周期管理
- `routes/model.py`：模型列表与模型详情
- `routes/city.py` + `services/city_service.py`：城市/景点数据查询
- `routes/health.py`：健康、工具健康、意图聚合指标

### 3.3 Agent 模块设计（`agent/travel_agent`）

- `graph/builder.py`：LangGraph 构建与流式事件桥接
- `graph/nodes.py`：意图识别、策略路由、计划生成、执行与验证逻辑
- `graph/runtime_config.py`：运行时控制开关与阈值
- `graph/memory_integration.py`：会话记忆、摘要、偏好画像与冲突澄清
- `graph/persistent_checkpointer.py`：SQLite checkpoint 增量持久化 + 压缩
- `tools/travel_tools.py` + `tools/travel_api.py`：工具定义与 provider 元数据透传

## 4. API 与事件协议

### 4.1 核心接口

- Chat: `POST /api/chat/stream`
- Session:
  - `POST /api/session/new`
  - `GET /api/sessions`
  - `DELETE /api/session/{session_id}`
  - `PUT /api/session/{session_id}/name`
  - `PUT /api/session/{session_id}/model`
  - `GET /api/session/{session_id}/model`
  - `POST /api/clear/{session_id}`
  - `POST /api/clear?session_id=...`
- Health:
  - `GET /api/health`
  - `GET /api/health/llm`
  - `GET /api/health/tools`
  - `GET /api/health/tools/intents`
  - `GET /api/ready`
  - `GET /api/live`
- Model: `GET /api/models`, `GET /api/models/{model_id}`
- City: `GET /api/cities`, `GET /api/cities/{city_id}`, `GET /api/cities/{city_id}/attractions`, `GET /api/regions`, `GET /api/tags`

### 4.2 `/api/chat/stream` 请求示例

```json
{
  "message": "请给我一个上海两日游建议",
  "session_id": "optional-session-id",
  "mode": "direct"
}
```

`mode` 可选值：`direct | react | plan`

### 4.3 SSE 事件类型

- `session_id`
- `reasoning_start`
- `reasoning_chunk`
- `reasoning_end`
- `plan_preview`（仅 `plan` 常见）
- `stage`
- `tool_start`
- `tool_end`
- `answer_start`
- `chunk`
- `metadata`
- `error`
- `done`

`metadata` 关键字段：

- `tools_used`
- `answer_length`
- `reasoning_length`
- `plan_id`
- `execution_stats`
- `verification_passed`
- `stale_result_count`
- `fallback_steps`

## 5. 快速启动与操作手册

### 5.1 环境准备

1. Python 3.13+
2. Node.js 20+
3. 已配置可用 LLM Key（参考 `.env.example` 与 `config/llm_config.yaml`）

### 5.2 安装依赖

```bash
uv python install 3.13
uv venv .venv --python 3.13
.\.venv\Scripts\activate
uv pip install -r requirements.txt

cd frontend
npm install
cd ..
```

### 5.3 配置

```bash
copy config\llm_config.yaml.example config\llm_config.yaml
```

根据实际 provider 填写 `api_key` 与 `api_base`。

### 5.4 启动

终端 1（启动 API）：

```bash
.\.venv\Scripts\python.exe -m uvicorn shuai_web.main:app --host 0.0.0.0 --port 38000 --app-dir web
```

终端 2（启动前端）：

```bash
cd frontend
npm run dev
```

### 5.5 常见操作流程

1. 打开 `http://localhost:33001`
2. 点击“新建会话”
3. 选择模型（左侧 AI 模型下拉）
4. 选择聊天模式（Direct / ReAct / Plan）
5. 输入需求并发送
6. 观察流式输出（思考、工具、答案）
7. 必要时点击“停止”中断生成
8. 使用“清空对话”清理当前会话消息

### 5.6 关键 API 操作示例

创建会话：

```bash
curl -X POST http://localhost:38000/api/session/new
```

设置会话模型（注意字段是 `model_id`）：

```bash
curl -X PUT http://localhost:38000/api/session/<session_id>/model ^
  -H "Content-Type: application/json" ^
  -d "{\"model_id\":\"gpt-4o-mini\"}"
```

触发流式聊天：

```bash
curl -N -X POST http://localhost:38000/api/chat/stream ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"请推荐上海周末行程\",\"mode\":\"plan\"}"
```

## 6. 本次全量前后端功能验证（2026-03-08）

### 6.1 自动化测试结果

执行时间：2026-03-08（本地环境）

- 后端全量：
  - 命令：`.\.venv\Scripts\python.exe -m pytest`
  - 结果：`102 passed`（72.35s）
- 前端类型检查：
  - 命令：`npm run lint`
  - 结果：通过（`tsc --noEmit`）
- 前端单测：
  - 命令：`npm run test:run`
  - 结果：`2 files / 4 tests passed`

### 6.2 运行态联调结果

- REST 接口冒烟：
  - `/api/health`：200
  - `/api/health/llm`：200
  - `/api/health/tools`：200
  - `/api/models`：200
  - `/api/cities?region=华东`：200
  - `session` 新建/重命名/读取模型/清空/删除：通过
- SSE 三模式联调（`/api/chat/stream`）：

| 模式 | content-type | answer_start | chunk | done | 结果 |
|---|---|---|---|---|---|
| direct | `text/event-stream` | 是 | 是（60） | 是 | 通过 |
| react | `text/event-stream` | 是 | 是（51） | 是 | 通过 |
| plan | `text/event-stream` | 是 | 是（81） | 是 | 通过（含 `plan_preview`） |

- 前端页面联调（Playwright）：
  - 访问 `http://localhost:33001` 成功
  - 页面标题：`小帅旅游助手 - 智能AI旅游推荐系统`
  - 发送真实问题并收到助手响应：通过
  - 控制台错误：0（`favicon.ico` 已修复）

### 6.3 验证中确认的接口细节

- `PUT /api/session/{session_id}/model` 兼容 `model_id` 与 `model` 两种字段
- 建议优先使用 `model_id`（标准字段）

## 7. 数据与持久化设计

- `data/sessions/sessions.json`：会话与消息数据
- `data/agent_memory.json`：会话摘要、用户偏好画像、冲突待澄清
- `data/langgraph_checkpoints.sqlite3`：LangGraph checkpoint（重启可恢复）
- `data/runtime_failure_clusters.jsonl`：运行失败聚类日志

## 8. 关键配置项

### 8.1 服务配置

- 文件：`config/server_config.yaml`
- 关键项：`web.host`、`web.port`、`web.cors_origins`、`frontend.port`

### 8.2 LLM 配置

- 文件：`config/llm_config.yaml`
- 关键项：`default_model`、`models.<model_id>.provider/api_base/api_key/model`

### 8.3 环境变量（常用）

- `SHUAI_WEB_PORT`
- `CORS_ORIGINS`
- `AGENT_CHECKPOINT_DB`
- `AGENT_MAX_PARALLELISM`
- `AGENT_TOOL_TIMEOUT_SECONDS`
- `AGENT_TOOL_MAX_RETRIES`
- `AGENT_CIRCUIT_BREAKER_THRESHOLD`
- `AGENT_MAX_PLAN_STEPS`
- `AGENT_HEALTH_WINDOW_MINUTES`

## 9. 项目结构

```text
ShuaiTravelAgent/
├── agent/                  # Agent 图执行、记忆、checkpoint、工具
├── web/                    # FastAPI routes/services/repositories/storage
├── frontend/               # Next.js 前端
├── tests/                  # 后端/集成测试
├── config/                 # server + llm 配置
├── data/                   # 运行时数据
├── scripts/                # benchmark/replay/quality gate 等脚本
└── docs/                   # 详细文档
```

## 10. 故障排查

- API 无法访问：先检查 `http://localhost:38000/api/health`
- 前端空白或请求失败：检查 `NEXT_PUBLIC_API_BASE` 是否指向 `http://localhost:38000`
- 流式无输出：检查浏览器网络里 `/api/chat/stream` 是否返回 `text/event-stream`
- 模型调用失败：检查 `config/llm_config.yaml` 的 `api_key` 和 provider 配置

## 11. 文档索引

- [docs/README.md](docs/README.md)
- [docs/reference/api-reference.md](docs/reference/api-reference.md)
- [docs/reference/configuration-reference.md](docs/reference/configuration-reference.md)
- [docs/architecture/system-architecture.md](docs/architecture/system-architecture.md)
- [docs/testing/testing-guide.md](docs/testing/testing-guide.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
