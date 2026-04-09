# Project Structure

## 顶层入口与根目录规范

维护时优先记这张“常用目录”表：

| 目录 / 文件 | 作用 |
| --- | --- |
| `.github/` | GitHub workflows、仓库治理入口与平台识别文件。 |
| `agent/` | LangGraph Agent、runtime seam、supervisor、skills、tools。 |
| `backend/` | FastAPI route、service、repository、persistence、observability。 |
| `frontend/` | Next.js 前端页面、feature workspace、API client。 |
| `extend/` | 观测可视化等扩展能力。 |
| `deploy/` | Compose、Dockerfile、migration、安全扫描等发版资产。 |
| `docs/` | 当前架构、reference、testing、governance 文档中心。 |
| `tests/` | 本地 smoke、runtime、contract snapshot、运维脚本回归。 |
| `scripts/` | `scripts/dev.py` 统一入口，以及 runtime / release / snapshot / quality 脚本。 |
| `data/` | 运行时数据目录。 |

其余顶层目录 / 文件按需再看：

| 目录 / 文件 | 作用 |
| --- | --- |
| `logs/` | 本地日志。 |
| `pyproject.toml` | 根目录 `pytest / mypy / Ruff` 统一工具配置。 |
| `requirements-dev.txt` | 本地开发与静态检查依赖。 |
| `requirements.txt` | 运行时依赖与安全审计输入。 |

当前根目录精炼原则：

- 只保留仓库入口、运行入口、构建入口和依赖入口
- Python 工具链配置统一收口到根级 `pyproject.toml`
- migration 专属配置下沉到 `deploy/migrations/`
- GitHub 平台识别文件统一放到 `.github/`
- 安全扫描配置统一放到 `deploy/security/`
- `.venv` 保留在项目根目录，工具缓存统一收口到 `.cache/`

根目录关键文件：

| 位置 | 主要职责 |
| --- | --- |
| [`.editorconfig`](../../.editorconfig) | 统一编码、换行和缩进。 |
| [`.gitattributes`](../../.gitattributes) | 统一文本归一化和二进制识别。 |
| [`pyproject.toml`](../../pyproject.toml) | 收口 `pytest / mypy / Ruff` 配置和 `.cache/` 目录。 |
| [`.github/`](../../.github) | 承接 `CONTRIBUTING`、`SECURITY`、`dependabot`、`ci.yml`、`release.yml`。 |
| [`scripts/dev.py`](../../scripts/dev.py) | 统一本地命令入口，收口测试、lint、runtime maintenance、snapshots、quality gate、support bundle、compose 校验等任务。 |

优先命令：

```bash
python scripts/dev.py help
python scripts/dev.py backend-dev
python scripts/dev.py frontend-dev
python scripts/dev.py backend-test --pytest-slice unit
python scripts/dev.py runtime-maintenance
```

## 关键目录说明

### `agent/`

负责旅行 Agent 的推理执行链路。

维护时优先按这张表定位：

| 关注面 | 最短入口 | 职责 |
| --- | --- | --- |
| 运行时主链 | `travel_agent/runtime/`、`runtime_driver.py`、`runtime_sources.py`、`runtime_event_emitters.py` | 收口 Web/API 入口、source adapter、event emitter、默认 checkpointer 选择。 |
| 图执行 | `travel_agent/graph/` | 图构建、节点、执行入口、checkpoint。 |
| 编排与扩展 | `travel_agent/supervisor/`、`travel_agent/subagents/`、`travel_agent/skills/`、`travel_agent/contracts/` | supervisor request、subagent dispatch、skills registry 和上层 typed contract。 |
| 状态与产物 | `travel_agent/memory/`、`travel_agent/artifacts/` | 记忆协作、画像合并、结构化 itinerary artifact。 |
| 外部依赖 | `travel_agent/tools/`、`travel_agent/llm/` | tool provider 适配、LLM 适配。 |

### `backend/`

负责 Backend API 路由、服务层、repository 层、SQL persistence 层，以及 startup validation、middleware、observability。

维护时优先按这张表定位：

| 关注面 | 最短入口 | 职责 |
| --- | --- | --- |
| 启动与装配 | [`backend/moyuan_web/main.py`](../../backend/moyuan_web/main.py)、[`backend/moyuan_web/startup_checks.py`](../../backend/moyuan_web/startup_checks.py) | App 装配、startup validation、依赖检查。 |
| HTTP / SSE 出口 | [`backend/moyuan_web/routes/`](../../backend/moyuan_web/routes)、[`backend/moyuan_web/services/`](../../backend/moyuan_web/services) | 请求校验、业务编排、SSE 事件输出。 |
| 持久化 | [`backend/moyuan_web/repositories/`](../../backend/moyuan_web/repositories)、[`backend/moyuan_web/repositories/file_session_repository.py`](../../backend/moyuan_web/repositories/file_session_repository.py)、`backend/moyuan_web/persistence/` | repository 抽象、`file | postgres` 切换、SQLAlchemy metadata 与 schema bootstrap。 |
| 观测与中间件 | [`backend/moyuan_web/observability.py`](../../backend/moyuan_web/observability.py)、`middleware/` | 健康指标、Prometheus 暴露、请求日志、限流和超时控制。 |

### `frontend/`

负责所有用户可见的交互界面。

维护时优先按这张表定位：

| 关注面 | 最短入口 | 职责 |
| --- | --- | --- |
| 页面壳层 | [`frontend/src/app/`](../../frontend/src/app)、[`frontend/src/components/`](../../frontend/src/components) | 页面装配、顶层 feature 连接。 |
| 聊天主链 | [`frontend/src/components/chat-area/`](../../frontend/src/components/chat-area)、[`frontend/src/context/`](../../frontend/src/context) | streaming、artifact runtime、input policy、session hydration。 |
| 呈现与工具区 | [`frontend/src/components/message-list/`](../../frontend/src/components/message-list)、[`frontend/src/components/travel-plan-toolkit/`](../../frontend/src/components/travel-plan-toolkit)、[`frontend/src/components/city-explorer/`](../../frontend/src/components/city-explorer) | Markdown 渲染、诊断展示、artifact-first itinerary、city compare/shortlist/detail。 |
| API client 与通用工具 | [`frontend/src/services/api/`](../../frontend/src/services/api)、[`frontend/src/utils/`](../../frontend/src/utils)、[`deploy/docker/frontend.Dockerfile`](../../deploy/docker/frontend.Dockerfile) | chat / city / map / session / share / artifact client，工具函数和前端镜像构建。 |

### `docs/governance/`

负责统一管理 `ADR / RFC / Design Review` 记录。

维护时优先按这张表定位：

| 关注面 | 最短入口 | 作用 |
| --- | --- | --- |
| 治理入口 | [`docs/governance/README.md`](../governance/README.md)、[`docs/governance/skills-market-onboarding.md`](../governance/skills-market-onboarding.md) | ADR / RFC / DR 流程与 skills market 规则。 |
| 模板 | [`docs/governance/adr/ADR-0000-template.md`](../governance/adr/ADR-0000-template.md)、[`docs/governance/rfcs/RFC-0000-template.md`](../governance/rfcs/RFC-0000-template.md)、[`docs/governance/design-reviews/DR-0000-template.md`](../governance/design-reviews/DR-0000-template.md) | 新记录统一按模板落盘。 |
| 审计门禁 | [`scripts/decision_record_audit.py`](../../scripts/decision_record_audit.py)、[`scripts/skills_market_audit.py`](../../scripts/skills_market_audit.py)、[`scripts/runtime_contract_audit.py`](../../scripts/runtime_contract_audit.py) | 结构完整性、skills 四件套、runtime seam typed contract 门禁；都已接入 `python scripts/dev.py infra-check` 和 CI。 |
| 运行态报告合同 | [`scripts/runtime_ops_contracts.py`](../../scripts/runtime_ops_contracts.py)、[`scripts/export_runtime_doctor_snapshot.py`](../../scripts/export_runtime_doctor_snapshot.py) | runtime_doctor、support bundle、release manifest、scorecard 共用 typed report contract。 |

### `backend/config/`

负责配置模板和配置解析。

最常用入口只有 3 个：

| 入口 | 作用 |
| --- | --- |
| [`backend/config/__init__.py`](../../backend/config/__init__.py) | 统一配置解析入口。 |
| [`backend/config/server_config.yaml.example`](../../backend/config/server_config.yaml.example) | Web/API 运行参数模板。 |
| [`backend/config/llm_config.yaml.example`](../../backend/config/llm_config.yaml.example) | LLM/provider 配置模板。 |

### `tests/`

以后端与本地 smoke 为主，同时覆盖契约、运行维护脚本、观测资产和质量门禁。

维护时优先按这张表定位：

| 场景 | 最短入口 | 作用 |
| --- | --- | --- |
| API / 本地 smoke | [`tests/test_api_smoke_local.py`](../../tests/test_api_smoke_local.py)、[`tests/test_chat_stream_local.py`](../../tests/test_chat_stream_local.py) | 本地接口、SSE、主链回归。 |
| Agent 主链 | [`tests/test_agent_runtime_phase1_unit.py`](../../tests/test_agent_runtime_phase1_unit.py)、[`tests/test_agent_subagent_phase2_unit.py`](../../tests/test_agent_subagent_phase2_unit.py) | runtime seam、subagent orchestration。 |
| 运行维护脚本 | [`tests/test_runtime_data_lifecycle_unit.py`](../../tests/test_runtime_data_lifecycle_unit.py)、[`tests/test_export_support_bundle_script_unit.py`](../../tests/test_export_support_bundle_script_unit.py) | backup / restore / prune / doctor / support bundle。 |
| 合同快照 | [`tests/test_export_openapi_snapshot_script_unit.py`](../../tests/test_export_openapi_snapshot_script_unit.py)、[`tests/test_export_sse_contract_snapshot_script_unit.py`](../../tests/test_export_sse_contract_snapshot_script_unit.py)、[`tests/test_export_runtime_doctor_snapshot_script_unit.py`](../../tests/test_export_runtime_doctor_snapshot_script_unit.py)、[`tests/test_export_frontend_chat_runtime_golden_fixture_script_unit.py`](../../tests/test_export_frontend_chat_runtime_golden_fixture_script_unit.py) | OpenAPI、SSE、runtime doctor、frontend chat runtime snapshot。 |
| pytest bootstrap | [`tests/conftest.py`](../../tests/conftest.py) | 统一 fixtures、CI guard、repo root / `backend/` 导入 bootstrap。 |

### `docs/`

项目文档中心，维护时优先看这张表：

| 区域 | 作用 | 最常用入口 |
| --- | --- | --- |
| `getting-started/` | 本地启动、开发工作流 | `development-workflow.md` |
| `architecture/` | 当前系统结构、数据与基础设施 | [`infrastructure-foundations.md`](../architecture/infrastructure-foundations.md) |
| `reference/` | 维护者速查、API/config/project structure | [`backend-maintainer-playbook.md`](backend-maintainer-playbook.md) |
| `testing/` | 测试入口、快照和质量门禁 | [`testing-guide.md`](../testing/testing-guide.md) |
| `benchmarks/` / `assets/` / `teaching/` | 报告、静态资源、教学材料 | 按需查阅，不作为当前实现真相源。 |

### `scripts/`

辅助脚本与质量门禁工具。

维护时优先按这张表定位：

| 场景 | 最短入口 | 作用 |
| --- | --- | --- |
| 统一入口 | [`scripts/dev.py`](../../scripts/dev.py) | 本地测试、lint、runtime maintenance、snapshots、quality gate、support bundle、compose 校验。 |
| 运行维护 | `runtime_backup.py`、`runtime_restore.py`、`runtime_prune.py`、`runtime_doctor.py`、`agent_replay.py` | backup / restore / prune / doctor / replay。 |
| 发布与报告 | `export_release_manifest.py`、`release_harness_scorecard.py`、`export_support_bundle.py` | release manifest、scorecard、support bundle。 |
| 合同与快照 | `export_openapi_snapshot.py`、`export_sse_contract_snapshot.py`、`export_runtime_doctor_snapshot.py`、`export_frontend_chat_runtime_golden_fixture.py` | 各类 contract snapshot 与前端 replay fixture。 |
| 导入初始化 | [`scripts/bootstrap_paths.py`](../../scripts/bootstrap_paths.py) | 统一 repo root / `backend/` 导入 bootstrap，避免脚本各自写 `sys.path` 注入。 |

### `extend/` + `deploy/`

扩展能力与发版资产目录，维护时优先按这张表定位：

| 区域 | 最短入口 | 作用 |
| --- | --- | --- |
| observability | [`extend/observability/README.md`](../../extend/observability/README.md)、[`extend/observability/grafana-dashboard.json`](../../extend/observability/grafana-dashboard.json)、[`extend/observability/prometheus-alerts.yml`](../../extend/observability/prometheus-alerts.yml)、[`extend/observability/prometheus.yml`](../../extend/observability/prometheus.yml)、[`extend/observability/grafana-provisioning/`](../../extend/observability/grafana-provisioning) | 仪表盘、Prometheus 抓取和告警资产。 |
| deploy assets | [`deploy/compose/compose.yaml`](../../deploy/compose/compose.yaml)、[`deploy/docker/backend.Dockerfile`](../../deploy/docker/backend.Dockerfile)、[`deploy/docker/frontend.Dockerfile`](../../deploy/docker/frontend.Dockerfile)、[`deploy/migrations/`](../../deploy/migrations) | Compose、镜像构建与 schema migration。 |
| security | [`deploy/security/README.md`](../../deploy/security/README.md)、[`deploy/security/gitleaks.toml`](../../deploy/security/gitleaks.toml) | secret scan 规则与安全扫描说明。 |

## 当前最常用的代码入口

前端主链入口：

| 场景 | 最短入口 |
| --- | --- |
| 聊天壳层 | [`ChatArea.tsx`](../../frontend/src/components/ChatArea.tsx)、[`chat-area/`](../../frontend/src/components/chat-area) |
| 消息渲染 | [`MessageList.tsx`](../../frontend/src/components/MessageList.tsx)、[`message-list/`](../../frontend/src/components/message-list) |
| itinerary / city UI | [`TravelPlanToolkit.tsx`](../../frontend/src/components/TravelPlanToolkit.tsx)、[`travel-plan-toolkit/`](../../frontend/src/components/travel-plan-toolkit)、[`CityExplorer.tsx`](../../frontend/src/components/CityExplorer.tsx)、[`city-explorer/`](../../frontend/src/components/city-explorer) |
| API client | [`services/api/`](../../frontend/src/services/api) |

后端主链入口：

| 场景 | 最短入口 |
| --- | --- |
| chat / health / artifact route | [`routes/chat.py`](../../backend/moyuan_web/routes/chat.py)、[`routes/health.py`](../../backend/moyuan_web/routes/health.py)、[`routes/artifact.py`](../../backend/moyuan_web/routes/artifact.py) |
| 核心服务 | [`services/chat_service.py`](../../backend/moyuan_web/services/chat_service.py)、[`services/artifact_service.py`](../../backend/moyuan_web/services/artifact_service.py)、[`services/share_service.py`](../../backend/moyuan_web/services/share_service.py) |
| 启动与观测 | [`observability.py`](../../backend/moyuan_web/observability.py)、[`startup_checks.py`](../../backend/moyuan_web/startup_checks.py) |

Agent 主链入口：

| 场景 | 最短入口 |
| --- | --- |
| runtime seam | [`runtime/agent_runtime.py`](../../agent/travel_agent/runtime/agent_runtime.py)、[`runtime/runtime_driver.py`](../../agent/travel_agent/runtime/runtime_driver.py)、[`runtime_sources.py`](../../agent/travel_agent/runtime_sources.py)、[`runtime_event_emitters.py`](../../agent/travel_agent/runtime_event_emitters.py) |
| graph 执行 | [`graph/runtime_flow.py`](../../agent/travel_agent/graph/runtime_flow.py)、[`graph/builder.py`](../../agent/travel_agent/graph/builder.py)、[`graph/nodes.py`](../../agent/travel_agent/graph/nodes.py)、[`graph/memory_integration.py`](../../agent/travel_agent/graph/memory_integration.py) |

Agent 扩展入口：

| 场景 | 最短入口 |
| --- | --- |
| 编排与注册 | [`supervisor/`](../../agent/travel_agent/supervisor)、[`subagents/`](../../agent/travel_agent/subagents)、[`skills/registry.py`](../../agent/travel_agent/skills/registry.py)、[`contracts/`](../../agent/travel_agent/contracts) |
| 产物、工具与状态 | [`artifacts/models.py`](../../agent/travel_agent/artifacts/models.py)、[`tools/travel_tools.py`](../../agent/travel_agent/tools/travel_tools.py)、[`memory/`](../../agent/travel_agent/memory) |

## 修改时的联动建议

前端改动：

| 改什么 | 一起看什么 |
| --- | --- |
| UI / 交互 | `frontend/src/components/*`、`frontend/src/services/api/*`、`frontend/src/utils/travelPlan.ts`、对应后端接口与类型。 |

后端改动：

| 改什么 | 一起看什么 |
| --- | --- |
| API / startup / observability | `backend/moyuan_web/main.py`、`error_handlers.py`、`middleware/__init__.py`、`api/error_codes.py`、`api/schemas/error.py`、`routes/*`、`services/*`、`backend/config/__init__.py`、`tests/test_api_smoke_local.py`、`tests/test_api_error_contract_local.py`、`tests/test_chat_stream_local.py`、`docs/reference/api-reference.md`、`docs/reference/error-code-reference.md`、`docs/testing/testing-guide.md`。 |

Agent 改动：

| 改什么 | 一起看什么 |
| --- | --- |
| Agent 架构 / supervisor / skills / artifact | `agent/travel_agent/runtime/*`、`supervisor/*`、`subagents/*`、`skills/*`、`artifacts/*`、`graph/*`、`backend/moyuan_web/services/chat_service.py`、`tests/test_agent_runtime_phase1_unit.py`、`tests/test_agent_subagent_phase2_unit.py`、`docs/architecture/system-architecture.md`。 |

仓库治理改动：

| 改什么 | 一起看什么 |
| --- | --- |
| 仓库规范 / 命令入口 / Compose | `/.editorconfig`、`/.gitattributes`、`/.github/CONTRIBUTING.md`、`/.github/SECURITY.md`、`/scripts/dev.py`、`/deploy/compose/compose.yaml`、`/deploy/security/gitleaks.toml`、`/.github/workflows/ci.yml`、`docs/getting-started/development-workflow.md`、`docs/architecture/infrastructure-foundations.md`。 |

## 命名与结构约定

- Python 文件使用 `snake_case.py`
- React 组件使用 `PascalCase.tsx`
- 文档文件使用 `kebab-case.md`
- 运行时数据统一放在 `data/`
- benchmark / replay 产物统一放在 `docs/benchmarks/`
- 截图等静态资源统一放在 `docs/assets/`

## 当前高频协作链

前端协作链：

| 场景 | 最短入口 | 通常一起看 |
| --- | --- | --- |
| 聊天 UI | `frontend/src/components/chat-area/`、`useChatRuntime.ts`、`frontend/src/services/api/chatClient.ts`、`chatStreamParser.ts` | `MessageList.tsx`、`TravelPlanToolkit.tsx` |
| session hydration | `frontend/src/context/useSessionHistoryState.ts`、`frontend/src/context/useModelBootstrapState.ts` | `frontend/src/services/api/artifactClient.ts`、`tests/test_api_smoke_local.py` |
| artifact / share | `frontend/src/components/travel-plan-toolkit/`、`frontend/src/services/api/artifactClient.ts`、`frontend/src/services/api/shareClient.ts` | `backend/moyuan_web/routes/artifact.py`、`backend/moyuan_web/services/share_service.py`、`docs/reference/api-reference.md` |
| city explorer | `frontend/src/components/city-explorer/`、`frontend/src/services/api/cityClient.ts` | `backend/moyuan_web/routes/city.py`、`tests/test_api_smoke_local.py` |

后端-Agent 协作链：

| 场景 | 最短入口 | 通常一起看 |
| --- | --- | --- |
| 聊天请求执行 | `backend/moyuan_web/routes/chat.py`、`backend/moyuan_web/services/chat_service.py`、`agent/travel_agent/runtime/agent_runtime.py`、`agent/travel_agent/runtime/runtime_driver.py` | `agent/travel_agent/graph/runtime_flow.py`、`agent/travel_agent/graph/builder.py`、`agent/travel_agent/graph/nodes.py` |
| session 持久化恢复 | `backend/moyuan_web/routes/session.py`、`backend/moyuan_web/services/chat_service.py`、`backend/moyuan_web/repositories/` | `frontend/src/context/useSessionHistoryState.ts`、`frontend/src/services/api/artifactClient.ts`、`tests/test_api_smoke_local.py` |
| tool / artifact 交付 | `agent/travel_agent/tools/travel_tools.py`、`agent/travel_agent/artifacts/`、`backend/moyuan_web/services/share_service.py` | `docs/architecture/system-architecture.md`、`docs/reference/api-reference.md` |
