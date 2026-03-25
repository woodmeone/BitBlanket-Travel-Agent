# Agent 对话链路 4 周执行排期（2026-03-09 至 2026-04-05）

## 1. 文档定位

- 类型：How-to（执行方案）
- 目标读者：后端/前端/测试负责人、Tech Lead
- 目标：把现有 Agent 对话链路优化项拆成可执行的 4 周任务，直接映射到文件和接口
- 范围：`agent + web + frontend + scripts + tests + docs`，不包含新的业务域功能

## 2. 当前基线（来自代码现状）

- 主链路：`intent -> strategy -> plan -> execute -> verify -> answer -> self_check`
- SSE 入口：`POST /api/chat/stream`
- 诊断入口：`GET /api/health/tools`
- 基准脚本：`scripts/agent_benchmark.py`、`scripts/agent_golden_eval.py`
- 已有问题信号：`docs/benchmarks/agent_benchmark_latest.json` 中存在 `TOOL_NOT_FOUND`，且历史报告出现 `avg_duration_ms=0`

## 3. 4 周总目标（量化）

- `TOOL_NOT_FOUND` 在 benchmark/golden 中降为 `0`
- 高风险问答（预算/政策/价格）证据化覆盖率 `>= 98%`
- fallback 后可执行回答率 `>= 99%`
- Golden pass rate `>= 0.97`
- `/api/health/tools` 可直接输出 SLO 状态和按意图聚合统计

## 4. 周排期与任务清单

## Week 1（2026-03-09 ~ 2026-03-15）：稳定性与可观测性打底

| ID | 任务 | 文件级改造 | 接口/脚本级改造 | 验收标准 |
|---|---|---|---|---|
| W1-1 | 计划阶段工具注册预检（防 `TOOL_NOT_FOUND`） | `agent/travel_agent/graph/nodes.py`（`plan_node`、执行前校验函数）、`agent/travel_agent/graph/state.py`（新增校验结果字段） | `POST /api/chat/stream` 的 `plan_preview` 增加 `validation_status`/`validation_errors`（仅 plan 模式） | 计划阶段即拦截未注册工具；执行阶段不再出现 `TOOL_NOT_FOUND` |
| W1-2 | 修正 benchmark 时延口径 | `scripts/agent_benchmark.py`、`tests/test_agent_benchmark_script_unit.py` | `agent_benchmark_latest.json/md` 增加并统一使用 `elapsed_ms`、`avg_elapsed_ms` | 报告不再出现全量 `avg_duration_ms=0` 的失真 |
| W1-3 | 增强工具健康诊断（SLO 结构化输出） | `web/moyuan_web/services/chat_service.py`（聚合 run 指标）、`web/moyuan_web/routes/health.py`（响应模型扩展） | `GET /api/health/tools` 增加 `slo`、`intent_aggregate`、`window_minutes` | 健康接口可直接看超时率/失败率/fallback 率是否越线 |
| W1-4 | 失败回放工具 v1（基于 checkpoint） | 新增 `scripts/agent_replay.py`；必要时补 `agent/travel_agent/graph/persistent_checkpointer.py` 读取能力 | CLI：`python scripts/agent_replay.py --session-id ... --db ...` | 线上失败会话可本地复现并输出 replay 报告 |
| W1-5 | 补齐稳定性回归测试 | `tests/test_agent_p0_guardrails_unit.py`、`tests/test_chat_stream_local.py`、新增 `tests/test_agent_replay_script_unit.py` | `pytest tests -q` | 新增用例覆盖：计划预检、健康聚合、回放脚本 |

**Week 1 交付件**
- 代码与测试通过
- 更新文档：`docs/reference/api-reference.md`（`plan_preview` 新字段）、`docs/testing/testing-guide.md`（replay 命令）

---

## Week 2（2026-03-16 ~ 2026-03-22）：验证闭环与时效治理

| ID | 任务 | 文件级改造 | 接口/脚本级改造 | 验收标准 |
|---|---|---|---|---|
| W2-1 | 关键工具 stale 自动刷新（weather/hotels） | `agent/travel_agent/graph/nodes.py`（`verify_node/execute_node` 刷新策略）、`agent/travel_agent/tools/travel_api.py`（支持 bypass cache）、`agent/travel_agent/tools/travel_tools.py`（透传 refresh 参数） | tool `_meta` 增加 `refresh_attempted`、`refresh_success` | stale 数据优先刷新；无法刷新时输出明确降级说明 |
| W2-2 | 答案证据化模板强化 | `agent/travel_agent/graph/prompt_templates.py`、`agent/travel_agent/graph/nodes.py`（`answer_node` 证据段渲染） | `POST /api/chat/stream` 最终回答要求显式包含 `source/fetched_at`（高风险场景强制） | 抽样问答中高风险场景证据覆盖率 >= 98% |
| W2-3 | 安全策略分级与配置化 | `agent/travel_agent/graph/nodes.py`（注入规则分级）、`agent/travel_agent/graph/runtime_config.py`（新增 guardrail 阈值） | 新增环境变量写入 `docs/reference/configuration-reference.md` | 注入样例拦截率上升，且误杀率可控（通过 golden 子集验证） |
| W2-4 | SSE 元数据补全验证状态 | `web/moyuan_web/services/chat_service.py`（metadata 拼装）、`frontend/src/services/api.ts`（解析元数据）、`frontend/src/types/index.ts`（类型扩展） | SSE `metadata` 增加 `verification_passed`、`stale_result_count`、`fallback_steps` | 前端可展示“是否通过验证”和“是否有过期数据” |
| W2-5 | 回归测试扩展 | `tests/test_travel_provider_metadata_unit.py`、`tests/test_agent_execution_optimization_integration.py`、`frontend/tests/unit/components/MessageList.test.tsx` | `pytest` + `npm run test:run` | stale 刷新路径和元数据展示路径均有自动化覆盖 |

**Week 2 交付件**
- stale 刷新与证据化上线
- 配置文档、API 文档同步更新

---

## Week 3（2026-03-23 ~ 2026-03-29）：评测体系与趋势化运营

| ID | 任务 | 文件级改造 | 接口/脚本级改造 | 验收标准 |
|---|---|---|---|---|
| W3-1 | Golden 数据集扩容（高风险/降级场景） | `tests/golden/agent_react_golden.json`、`scripts/agent_golden_eval.py` | `agent_golden_eval_latest.json` 增加 intent 维度统计 | Golden 覆盖 recommend/attractions/itinerary/budget/policy/fallback |
| W3-2 | Benchmark 场景扩容与趋势对比 | `scripts/agent_benchmark.py`、新增 `scripts/agent_benchmark_trend.py` | 产出 `docs/benchmarks/agent_benchmark_trend_latest.md` | 可比较“当前 vs 基线”成功率、时延、fallback 变化 |
| W3-3 | 意图维度运行统计接口 | `web/moyuan_web/services/chat_service.py`（按 intent 聚合窗口）、`web/moyuan_web/routes/health.py`（新增子路由） | 新增 `GET /api/health/tools/intents` | 可直接查询每种 intent 的成功率/超时率/fallback 率 |
| W3-4 | 前端诊断可视化（轻量） | `frontend/src/components/ChatArea.tsx`、`frontend/src/components/MessageList.tsx`、`frontend/src/context/AppContext.tsx` | 前端展示本轮 `tools_used/fallback_steps/verification_passed` | 用户可感知回答可信度，不再只看到文本 |
| W3-5 | 测试与报告流水线 | `tests/test_agent_benchmark_script_unit.py`、新增 `tests/test_agent_benchmark_trend_script_unit.py` | `python scripts/agent_benchmark.py` + trend 脚本可稳定产报告 | 报告生成纳入可重复流程 |

**Week 3 交付件**
- Golden/Benchmark 形成“基线 + 趋势”双报告
- 新增 intent 聚合诊断接口可用

---

## Week 4（2026-03-30 ~ 2026-04-05）：CI 门禁与发布收口

| ID | 任务 | 文件级改造 | 接口/脚本级改造 | 验收标准 |
|---|---|---|---|---|
| W4-1 | CI 质量门禁升级 | `.github/workflows/ci.yml` | 新增 benchmark/golden/trend 执行与阈值校验 | PR 自动拦截质量退化（pass rate、hallucination、fallback） |
| W4-2 | 运行时配置收口与默认值审计 | `agent/travel_agent/graph/runtime_config.py`、`docs/reference/configuration-reference.md` | 配置项分组：可靠性/时效性/安全/成本 | 配置可灰度启停，避免硬编码 |
| W4-3 | API 与架构文档对齐 | `docs/reference/api-reference.md`、`docs/architecture/system-architecture.md` | 文档补齐新增 SSE 字段、健康子接口、回放脚本 | 文档与实际实现一致，可用于交接 |
| W4-4 | 发布前全量回归 | `tests/`、`frontend/tests/`、`scripts/` | 命令：`pytest tests -q`、`npm run test:run`、`python scripts/agent_golden_eval.py ...` | 通过发布前检查清单，形成周报 |
| W4-5 | 最终评审与留档 | 新增 `docs/benchmarks/agent_iteration_summary_2026-04-05.md` | 汇总 4 周指标变化与未完成项 | 形成下一阶段（Q2）输入清单 |

**Week 4 交付件**
- CI 门禁生效
- 发布文档与指标报告齐备

## 5. 跨周接口变更清单（便于联调）

1. `POST /api/chat/stream`（SSE）
- `plan_preview`：新增 `validation_status`、`validation_errors`（Week 1）
- `metadata`：新增 `verification_passed`、`stale_result_count`、`fallback_steps`（Week 2）

2. `GET /api/health/tools`
- 新增 `slo`、`intent_aggregate`、`window_minutes`（Week 1）

3. `GET /api/health/tools/intents`
- 新增按意图聚合诊断接口（Week 3）

## 6. 每周执行节奏（建议）

1. 周一：拆解任务到 issue（按 W1-1 这类 ID）
2. 周三：中期检查（仅看量化指标，不讨论感受）
3. 周五：跑固定回归命令并固化报告到 `docs/benchmarks/`

## 7. 建议的责任分工（可按人名替换）

- BE-Agent：`agent/travel_agent/graph/*`、`agent/travel_agent/tools/*`、`scripts/*`
- BE-API：`web/moyuan_web/services/*`、`web/moyuan_web/routes/*`
- FE：`frontend/src/components/*`、`frontend/src/services/api.ts`、`frontend/src/types/index.ts`
- QA：`tests/*`、`frontend/tests/*`、CI 门禁脚本

## 8. 完成定义（DoD）

- 功能：对应接口/脚本可运行，且字段契约稳定
- 质量：新增路径有自动化测试
- 文档：`api-reference/configuration-reference/testing-guide` 至少同步一处
- 指标：本周目标指标在报告文件中可核验
