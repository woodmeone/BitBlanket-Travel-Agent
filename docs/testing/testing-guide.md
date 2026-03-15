# Testing Guide

## 测试分层

### 1. 后端 pytest markers

当前 marker 定义在：

- [`pytest.ini`](/D:/projects/shuai/ShuaiTravelAgent/pytest.ini)
- [`tests/conftest.py`](/D:/projects/shuai/ShuaiTravelAgent/tests/conftest.py)

主要分层：

- `unit`
  - 纯逻辑与模块级测试
- `integration`
  - 跨层行为测试
- `local`
  - 本地 ASGI smoke / 本地资源依赖测试
- `external_api`
  - 依赖外部 provider 或在线服务
- `quality`
  - 与质量门禁或评估脚本相关

### 2. 前端测试

目录：[`frontend/`](/D:/projects/shuai/ShuaiTravelAgent/frontend)

运行命令：

```bash
cd frontend
npm run lint
npm run test:run
npm run build
```

说明：

- `lint` 实际执行 `tsc --noEmit`
- `build` 用于发现类型、SSR、rewrite、导入链和编码问题
- 这次基础设施变更后，`build` 对 `next.config.js` 和 API rewrite 尤其重要

### 3. Agent 质量脚本

常用脚本：

```bash
python scripts/agent_benchmark.py --output-dir docs/benchmarks
python scripts/agent_benchmark_trend.py --current docs/benchmarks/agent_benchmark_latest.json --baseline docs/benchmarks/agent_benchmark_baseline.json --output docs/benchmarks/agent_benchmark_trend_latest.md
python scripts/agent_golden_eval.py --dataset tests/golden/agent_react_golden.json --report docs/benchmarks/agent_golden_eval_latest.json --min-pass-rate 0.0
python scripts/agent_quality_gate.py --golden-report docs/benchmarks/agent_golden_eval_latest.json --benchmark-report docs/benchmarks/agent_benchmark_latest.json --baseline-benchmark-report docs/benchmarks/agent_benchmark_baseline.json
```

这些脚本主要用于：

- benchmark 回归
- golden set 稳定性评估
- benchmark 趋势对比
- CI/CD 质量门禁

### 4. 契约快照脚本

当前已经补上 OpenAPI 快照导出：

```bash
python scripts/export_openapi_snapshot.py
python scripts/export_sse_contract_snapshot.py
```

默认产物：

- [`docs/reference/openapi.snapshot.json`](/D:/projects/shuai/ShuaiTravelAgent/docs/reference/openapi.snapshot.json)
- [`docs/reference/sse-contract.snapshot.json`](/D:/projects/shuai/ShuaiTravelAgent/docs/reference/sse-contract.snapshot.json)

它适合在这些场景使用：

- 改 health / ready / session / share / city / model / map 接口后
- 改请求/响应字段后
- 改 OpenAPI 暴露结构后

## 推荐的本地回归顺序

### 日常前端改动

```bash
cd frontend
npm run lint
npm run test:run
npm run build
```

### 改 API / Agent / startup / health 后

```bash
python -m pytest tests -m "unit and not local and not external_api" -q
python -m pytest tests -m "local and not external_api" -q
python scripts/docstring_audit.py --strict
cd frontend
npm run lint
npm run build
```

### 发版前建议

```bash
python -m pytest tests -m "unit and not local and not external_api" -q
python -m pytest tests -m "local and not external_api" -q
python scripts/docstring_audit.py --strict
cd frontend
npm run lint
npm run test:run
npm run build
cd ..
python scripts/agent_benchmark.py --output-dir docs/benchmarks
python scripts/agent_golden_eval.py --dataset tests/golden/agent_react_golden.json --report docs/benchmarks/agent_golden_eval_latest.json --min-pass-rate 0.0
python scripts/agent_quality_gate.py --golden-report docs/benchmarks/agent_golden_eval_latest.json --benchmark-report docs/benchmarks/agent_benchmark_latest.json --baseline-benchmark-report docs/benchmarks/agent_benchmark_baseline.json
```

## 本轮基础设施相关重点测试

### readiness / metrics / request tracing

重点文件：

- [`tests/test_api_smoke_local.py`](/D:/projects/shuai/ShuaiTravelAgent/tests/test_api_smoke_local.py)
- [`tests/test_chat_stream_local.py`](/D:/projects/shuai/ShuaiTravelAgent/tests/test_chat_stream_local.py)

这些测试当前重点保护：

- `/api/health`
- `/api/ready`
- `/api/live`
- `/api/metrics`
- `/api/chat/stream`
- `X-Request-ID / X-Trace-ID`
- SSE payload 中的 `request_id / trace_id`

### 这轮最小验证动作

```bash
python -m pytest tests/test_api_smoke_local.py tests/test_chat_stream_local.py -q
python -m pytest tests/test_runtime_data_lifecycle_unit.py tests/test_export_openapi_snapshot_script_unit.py tests/test_export_sse_contract_snapshot_script_unit.py tests/test_runtime_doctor_unit.py tests/test_share_service_unit.py -q
```

## CI 当前怎么跑

CI 配置见 [`.github/workflows/ci.yml`](/D:/projects/shuai/ShuaiTravelAgent/.github/workflows/ci.yml)。

当前主要步骤：

1. 安装 Python / Node 依赖
2. 复制 `config/llm_config.yaml.example` 和 `config/server_config.yaml.example`
3. 跑后端 unit
4. 跑后端 local smoke
5. 跑 `docstring_audit.py --strict`
6. 跑 benchmark / golden eval / trend / quality gate
7. 上传 quality artifacts
8. 跑前端 lint / test / build
9. 把结果写入 GitHub Step Summary

## CI 产物与排查路径

当前会上传这些 artifact：

- `docs/benchmarks/agent_benchmark_latest.json`
- `docs/benchmarks/agent_benchmark_latest.md`
- `docs/benchmarks/agent_benchmark_trend_latest.md`
- `docs/benchmarks/agent_golden_eval_latest.json`

如果 CI 失败，建议优先按这个顺序看：

1. 是 unit 失败还是 local smoke 失败
2. `/api/ready` 相关断言是否失败
3. `docstring_audit.py --strict` 是否拦住了新文件
4. benchmark / golden / quality gate 是否出现退化
5. GitHub Step Summary 是否已经给出了具体失败层

## 注释质量检查

项目提供 [`scripts/docstring_audit.py`](/D:/projects/shuai/ShuaiTravelAgent/scripts/docstring_audit.py) 用于审计 Python 注释覆盖率：

```bash
python scripts/docstring_audit.py
python scripts/docstring_audit.py --strict
```

说明：

1. 默认扫描 `agent/`、`web/`、`scripts/`
2. `--strict` 模式下，只要存在缺失 docstring 会返回非零退出码
3. 现在它已经接入 CI，不再只是“本地建议”

## Replay / 故障回放

用于复现某个 session 的执行路径并导出报告。

### 执行真实 replay

```bash
python scripts/agent_replay.py --session-id <session_id> --db data/langgraph_checkpoints.sqlite3
```

### 只导出 checkpoint 快照

```bash
python scripts/agent_replay.py --session-id <session_id> --db data/langgraph_checkpoints.sqlite3 --dry-run
```

默认输出目录：`docs/benchmarks/`

## CI 常见失败点

### 1. 编码问题

典型表现：

- `invalid utf-8 sequence`
- 构建时读取源码失败

建议：

- 统一用 UTF-8 保存
- 避免通过有编码污染的终端直接写中文源码
- 改动后至少跑一次 `npm run build`

### 2. readiness / 配置问题

优先检查：

- `config/llm_config.yaml` 是否存在
- `config/server_config.yaml` 是否存在
- `/api/ready` 失败的是哪一个 check
- `SHUAI_FAIL_FAST_STARTUP_VALIDATION` 是否导致 CI 启动直接失败

### 3. SSE / 流式测试不稳定

优先检查：

- `/api/chat/stream` 是否正常返回 `text/event-stream`
- 响应头里是否有 `X-Request-ID / X-Trace-ID`
- SSE payload 是否带 `request_id / trace_id`
- 模型配置或工具 provider 是否超时

### 4. Golden eval / 正则错误

优先检查：

- 新增文案是否影响断言
- 正则是否有未转义字符
- 聚合字段和测试预期是否一致

## 浏览器联调建议

如果需要做真实界面验证，建议至少覆盖：

- 首页是否正常打开
- `/api/chat/stream` 是否能拿到 `text/event-stream`
- 前端日志里是否能看到 request / trace id
- 城市探索是否能加载
- 导出图片和分享按钮是否能触发
- 路线预览与重排按钮是否工作
