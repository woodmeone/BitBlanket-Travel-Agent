# Project Structure

## 顶层目录

```text
ShuaiTravelAgent/
├── .editorconfig         # 编辑器编码、换行、缩进规范
├── .gitattributes        # Git 文本归一化与二进制文件策略
├── agent/                # LangGraph Agent 逻辑
├── web/                  # FastAPI 服务
├── frontend/             # Next.js 前端
├── config/               # YAML 配置模板与解析
├── docs/                 # 文档中心
├── tests/                # API / 集成 / 质量测试
├── data/                 # 运行时数据
├── logs/                 # 本地日志
├── ops/                  # 观测与运维资产
├── scripts/              # 运行维护、快照、质量脚本
├── dev.ps1               # 本地统一命令入口
├── compose.yaml          # 根目录 Docker Compose
├── Dockerfile.backend    # Web API 镜像构建文件
├── requirements-dev.txt  # 本地开发与静态检查依赖
├── mypy.ini              # mypy 检查范围与规则
└── ruff.toml             # Ruff 检查规则
```

## 根目录规范文件

### `.editorconfig`

统一这些基础行为：

- `UTF-8`
- 默认 `LF`
- Markdown 允许保留行尾空格
- Python 4 空格缩进
- TypeScript / JSON / YAML 2 空格缩进
- PowerShell 使用 `CRLF`

### `.gitattributes`

统一这些 Git 行为：

- 常见文本文件按规则归一化换行
- `ps1/cmd/bat` 保持 `CRLF`
- 图片、PDF、Zip、SQLite 以 binary 处理

### `dev.ps1`

这是本地最推荐的统一入口，负责收口：

- 测试
- `ruff`
- `mypy`
- docstring 审计
- OpenAPI / SSE 快照导出
- release manifest
- support bundle
- compose 渲染校验

优先命令：

```bash
powershell -ExecutionPolicy Bypass -File .\dev.ps1 help
```

## 关键目录说明

### `agent/`

负责旅行 Agent 的推理执行链路。

重点子目录：

- `travel_agent/runtime/`
  - Web/API 层调用的应用级入口，封装 supervisor、skills、artifact 组合
- `travel_agent/supervisor/`
  - Phase 1 兼容层，先用 supervisor 外壳承接当前单图
- `travel_agent/subagents/`
  - Phase 2 最小 subagent 实现与注册表，当前包含 research / planning / verification
- `travel_agent/skills/`
  - skill registry 与领域能力契约映射
- `travel_agent/artifacts/`
  - 结构化行程产物与 artifact builder
- `travel_agent/contracts/`
  - skills 等上层契约模型
- `travel_agent/graph/`
  - 图构建、节点、运行时配置、checkpoint
- `travel_agent/tools/`
  - 工具定义、provider 适配
- `travel_agent/llm/`
  - LLM 适配层

### `web/`

负责 Web API 路由、服务层、仓储层、存储层，以及 startup validation、middleware、observability。

重点路径：

- [`web/shuai_web/main.py`](/D:/projects/shuai/ShuaiTravelAgent/web/shuai_web/main.py)
- [`web/shuai_web/routes/`](/D:/projects/shuai/ShuaiTravelAgent/web/shuai_web/routes)
- [`web/shuai_web/services/`](/D:/projects/shuai/ShuaiTravelAgent/web/shuai_web/services)
- [`web/shuai_web/repositories/`](/D:/projects/shuai/ShuaiTravelAgent/web/shuai_web/repositories)
- [`web/shuai_web/storage/`](/D:/projects/shuai/ShuaiTravelAgent/web/shuai_web/storage)
- [`web/shuai_web/observability.py`](/D:/projects/shuai/ShuaiTravelAgent/web/shuai_web/observability.py)
- [`web/shuai_web/startup_checks.py`](/D:/projects/shuai/ShuaiTravelAgent/web/shuai_web/startup_checks.py)

### `frontend/`

负责所有用户可见的交互界面。

重点路径：

- [`frontend/src/app/`](/D:/projects/shuai/ShuaiTravelAgent/frontend/src/app)
- [`frontend/src/components/`](/D:/projects/shuai/ShuaiTravelAgent/frontend/src/components)
- [`frontend/src/context/`](/D:/projects/shuai/ShuaiTravelAgent/frontend/src/context)
- [`frontend/src/services/api.ts`](/D:/projects/shuai/ShuaiTravelAgent/frontend/src/services/api.ts)
- [`frontend/src/utils/`](/D:/projects/shuai/ShuaiTravelAgent/frontend/src/utils)
- [`frontend/Dockerfile`](/D:/projects/shuai/ShuaiTravelAgent/frontend/Dockerfile)

### `config/`

负责配置模板和配置解析。

关键文件：

- [`config/__init__.py`](/D:/projects/shuai/ShuaiTravelAgent/config/__init__.py)
- [`config/server_config.yaml.example`](/D:/projects/shuai/ShuaiTravelAgent/config/server_config.yaml.example)
- [`config/llm_config.yaml.example`](/D:/projects/shuai/ShuaiTravelAgent/config/llm_config.yaml.example)

### `tests/`

以后端与本地 smoke 为主，同时覆盖契约、运行维护脚本、观测资产和质量门禁。

重点文件：

- [`tests/test_api_smoke_local.py`](/D:/projects/shuai/ShuaiTravelAgent/tests/test_api_smoke_local.py)
- [`tests/test_chat_stream_local.py`](/D:/projects/shuai/ShuaiTravelAgent/tests/test_chat_stream_local.py)
- [`tests/test_agent_runtime_phase1_unit.py`](/D:/projects/shuai/ShuaiTravelAgent/tests/test_agent_runtime_phase1_unit.py)
- [`tests/test_agent_subagent_phase2_unit.py`](/D:/projects/shuai/ShuaiTravelAgent/tests/test_agent_subagent_phase2_unit.py)
- [`tests/test_runtime_data_lifecycle_unit.py`](/D:/projects/shuai/ShuaiTravelAgent/tests/test_runtime_data_lifecycle_unit.py)
- [`tests/test_export_openapi_snapshot_script_unit.py`](/D:/projects/shuai/ShuaiTravelAgent/tests/test_export_openapi_snapshot_script_unit.py)
- [`tests/test_export_sse_contract_snapshot_script_unit.py`](/D:/projects/shuai/ShuaiTravelAgent/tests/test_export_sse_contract_snapshot_script_unit.py)
- [`tests/test_export_support_bundle_script_unit.py`](/D:/projects/shuai/ShuaiTravelAgent/tests/test_export_support_bundle_script_unit.py)

### `docs/`

项目文档中心，分为：

- `getting-started/`
- `product/`
- `architecture/`
- `reference/`
- `testing/`
- `benchmarks/`
- `assets/`
- `teaching/`

维护者最常用：

- [`docs/architecture/infrastructure-foundations.md`](/D:/projects/shuai/ShuaiTravelAgent/docs/architecture/infrastructure-foundations.md)
- [`docs/reference/backend-maintainer-playbook.md`](/D:/projects/shuai/ShuaiTravelAgent/docs/reference/backend-maintainer-playbook.md)
- [`docs/testing/testing-guide.md`](/D:/projects/shuai/ShuaiTravelAgent/docs/testing/testing-guide.md)

### `scripts/`

辅助脚本与质量门禁工具。

当前主要覆盖：

- benchmark / golden eval / quality gate
- runtime backup / restore / prune / doctor
- OpenAPI / SSE contract snapshot export
- release manifest export
- support bundle export
- docstring audit

### `ops/`

基础设施运行资产目录，当前重点是 `observability/`：

- [`ops/observability/README.md`](/D:/projects/shuai/ShuaiTravelAgent/ops/observability/README.md)
- [`ops/observability/grafana-dashboard.json`](/D:/projects/shuai/ShuaiTravelAgent/ops/observability/grafana-dashboard.json)
- [`ops/observability/prometheus-alerts.yml`](/D:/projects/shuai/ShuaiTravelAgent/ops/observability/prometheus-alerts.yml)
- [`ops/observability/prometheus.yml`](/D:/projects/shuai/ShuaiTravelAgent/ops/observability/prometheus.yml)
- [`ops/observability/grafana-provisioning/`](/D:/projects/shuai/ShuaiTravelAgent/ops/observability/grafana-provisioning)

## 当前最常用的代码入口

### 前端

- [`frontend/src/components/ChatArea.tsx`](/D:/projects/shuai/ShuaiTravelAgent/frontend/src/components/ChatArea.tsx)
- [`frontend/src/components/MessageList.tsx`](/D:/projects/shuai/ShuaiTravelAgent/frontend/src/components/MessageList.tsx)
- [`frontend/src/components/TravelPlanToolkit.tsx`](/D:/projects/shuai/ShuaiTravelAgent/frontend/src/components/TravelPlanToolkit.tsx)
- [`frontend/src/components/CityExplorer.tsx`](/D:/projects/shuai/ShuaiTravelAgent/frontend/src/components/CityExplorer.tsx)
- [`frontend/src/services/api.ts`](/D:/projects/shuai/ShuaiTravelAgent/frontend/src/services/api.ts)

### 后端

- [`web/shuai_web/routes/chat.py`](/D:/projects/shuai/ShuaiTravelAgent/web/shuai_web/routes/chat.py)
- [`web/shuai_web/routes/health.py`](/D:/projects/shuai/ShuaiTravelAgent/web/shuai_web/routes/health.py)
- [`web/shuai_web/services/chat_service.py`](/D:/projects/shuai/ShuaiTravelAgent/web/shuai_web/services/chat_service.py)
- [`web/shuai_web/services/share_service.py`](/D:/projects/shuai/ShuaiTravelAgent/web/shuai_web/services/share_service.py)
- [`web/shuai_web/observability.py`](/D:/projects/shuai/ShuaiTravelAgent/web/shuai_web/observability.py)
- [`web/shuai_web/startup_checks.py`](/D:/projects/shuai/ShuaiTravelAgent/web/shuai_web/startup_checks.py)

### Agent

- [`agent/travel_agent/runtime/agent_runtime.py`](/D:/projects/shuai/ShuaiTravelAgent/agent/travel_agent/runtime/agent_runtime.py)
- [`agent/travel_agent/supervisor/builder.py`](/D:/projects/shuai/ShuaiTravelAgent/agent/travel_agent/supervisor/builder.py)
- [`agent/travel_agent/supervisor/nodes.py`](/D:/projects/shuai/ShuaiTravelAgent/agent/travel_agent/supervisor/nodes.py)
- [`agent/travel_agent/subagents/registry.py`](/D:/projects/shuai/ShuaiTravelAgent/agent/travel_agent/subagents/registry.py)
- [`agent/travel_agent/subagents/research.py`](/D:/projects/shuai/ShuaiTravelAgent/agent/travel_agent/subagents/research.py)
- [`agent/travel_agent/subagents/planning.py`](/D:/projects/shuai/ShuaiTravelAgent/agent/travel_agent/subagents/planning.py)
- [`agent/travel_agent/subagents/verification.py`](/D:/projects/shuai/ShuaiTravelAgent/agent/travel_agent/subagents/verification.py)
- [`agent/travel_agent/skills/registry.py`](/D:/projects/shuai/ShuaiTravelAgent/agent/travel_agent/skills/registry.py)
- [`agent/travel_agent/artifacts/models.py`](/D:/projects/shuai/ShuaiTravelAgent/agent/travel_agent/artifacts/models.py)
- [`agent/travel_agent/graph/builder.py`](/D:/projects/shuai/ShuaiTravelAgent/agent/travel_agent/graph/builder.py)
- [`agent/travel_agent/graph/nodes.py`](/D:/projects/shuai/ShuaiTravelAgent/agent/travel_agent/graph/nodes.py)
- [`agent/travel_agent/graph/runtime_config.py`](/D:/projects/shuai/ShuaiTravelAgent/agent/travel_agent/graph/runtime_config.py)
- [`agent/travel_agent/graph/memory_integration.py`](/D:/projects/shuai/ShuaiTravelAgent/agent/travel_agent/graph/memory_integration.py)
- [`agent/travel_agent/tools/travel_tools.py`](/D:/projects/shuai/ShuaiTravelAgent/agent/travel_agent/tools/travel_tools.py)

## 修改时的联动建议

### 改 UI / 交互

通常需要同时关注：

- `frontend/src/components/*`
- `frontend/src/services/api.ts`
- `frontend/src/utils/travelPlan.ts`
- 对应的后端接口与类型

### 改 API / startup / observability

通常需要同时关注：

- `web/shuai_web/main.py`
- `web/shuai_web/middleware/__init__.py`
- `web/shuai_web/routes/*`
- `web/shuai_web/services/*`
- `config/__init__.py`
- `tests/test_api_smoke_local.py`
- `tests/test_chat_stream_local.py`
- `docs/reference/api-reference.md`
- `docs/testing/testing-guide.md`

### 改 Agent 架构 / supervisor / skills / artifact

通常需要同时关注：

- `agent/travel_agent/runtime/*`
- `agent/travel_agent/supervisor/*`
- `agent/travel_agent/subagents/*`
- `agent/travel_agent/skills/*`
- `agent/travel_agent/artifacts/*`
- `agent/travel_agent/graph/*`
- `web/shuai_web/services/chat_service.py`
- `tests/test_agent_runtime_phase1_unit.py`
- `tests/test_agent_subagent_phase2_unit.py`
- `docs/architecture/system-architecture.md`
- `docs/architecture/agent-subagent-skills-architecture-roadmap.md`

### 改仓库规范 / 命令入口 / Compose

通常需要同时关注：

- `/.editorconfig`
- `/.gitattributes`
- `/dev.ps1`
- `/compose.yaml`
- `/.github/workflows/ci.yml`
- `docs/getting-started/development-workflow.md`
- `docs/architecture/infrastructure-foundations.md`

## 命名与结构约定

- Python 文件使用 `snake_case.py`
- React 组件使用 `PascalCase.tsx`
- 文档文件使用 `kebab-case.md`
- 运行时数据统一放在 `data/`
- benchmark / replay 产物统一放在 `docs/benchmarks/`
- 截图等静态资源统一放在 `docs/assets/`
## Phase 3 Frontend Files

The artifact-first UI slice introduced these additional frontend responsibilities:

- [`frontend/src/types/index.ts`](/D:/projects/shuai/ShuaiTravelAgent/frontend/src/types/index.ts)
  - streaming artifact / subagent event contracts
- [`frontend/src/utils/agentArtifacts.ts`](/D:/projects/shuai/ShuaiTravelAgent/frontend/src/utils/agentArtifacts.ts)
  - frontend-side artifact merge helpers
- [`frontend/src/components/ChatArea.tsx`](/D:/projects/shuai/ShuaiTravelAgent/frontend/src/components/ChatArea.tsx)
  - per-run artifact merge + subagent timeline state
- [`frontend/src/components/MessageList.tsx`](/D:/projects/shuai/ShuaiTravelAgent/frontend/src/components/MessageList.tsx)
  - artifact/subagent diagnostics rendering
- [`frontend/src/components/TravelPlanToolkit.tsx`](/D:/projects/shuai/ShuaiTravelAgent/frontend/src/components/TravelPlanToolkit.tsx)
  - structured artifact summary + text fallback itinerary processing
- [`frontend/tests/unit/utils/agentArtifacts.test.ts`](/D:/projects/shuai/ShuaiTravelAgent/frontend/tests/unit/utils/agentArtifacts.test.ts)
  - protects artifact merge semantics
## Session Hydration Additions

- `web/shuai_web/routes/session.py`
  - 新增 `GET /session/{session_id}/messages`，作为前端恢复会话消息的公开入口
- `web/shuai_web/services/chat_service.py`
  - assistant 消息现在会把 `diagnostics.artifact` 与 `diagnostics.subagentEvents` 一并落盘
  - user 消息支持 `display_message` / `model_content` 分离
- `frontend/src/context/AppContext.tsx`
  - 负责 session 切换、刷新恢复和当前 session id 的本地持久化
- `frontend/src/utils/sessionMessages.ts`
  - 负责把后端持久化消息标准化成前端 `Message` 结构
