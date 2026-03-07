# Agent P0 Hardening Roadmap

本文件定义 Agent 在 P0 阶段（优先级最高）的完善范围、验收标准和交付顺序。

## Scope

P0 目标聚焦 5 个方向：

1. 工具能力体系化
2. 事实检索与实时性
3. 结果评估闭环
4. 安全与约束
5. 错误恢复能力

## Current Baseline

当前仓库已具备部分基础能力：

- 编排层已有 `intent -> plan -> execute -> answer` 流程。
- 工具执行层已有超时、重试、并行执行、熔断器。
- 但缺少统一参数校验、标准指标汇总、安全输入拦截、数据新鲜度/来源标注约束。

## P0 Deliverables

### 1) Tool Governance

目标：工具调用“可控、可观测、可失败恢复”。

交付项：

- 工具调用前统一参数校验（Schema 级别）。
- 工具调用参数日志脱敏（token/password/secret）。
- 工具执行汇总指标（成功率、超时率、平均耗时、按工具聚合）。

验收标准：

- 缺失必填参数时，不会触发工具实际调用，返回结构化错误码。
- 每次执行结束后状态里存在 `execution_summary`。
- 指标能区分 `success/failed/blocked/timeout`。

### 2) Freshness & Source Attribution

目标：回答中明确“信息来源和时效性”，降低幻觉。

交付项：

- 引入外部数据源接口层（天气/航班/签证/交通），保留 provider 标签。
- 工具结果结构统一增加 `source`, `fetched_at`, `ttl_seconds`。
- 回答节点默认在结果中展示来源与抓取时间。

验收标准：

- 涉及实时信息的问题，答复至少包含 1 条来源和时间戳。
- 超过 TTL 的缓存数据默认标记为 stale，不直接当作最终结论。

### 3) Evaluation Loop

目标：可以量化 Agent 质量并驱动迭代。

交付项：

- 增加离线评测样本（典型旅行问答场景）。
- 产出关键指标：任务成功率、工具成功率、平均轮次、平均时延、失败原因 TopN。
- 建立回归脚本，PR 可运行基础评测。

验收标准：

- 每次评测能产出结构化报告（JSON 或 Markdown）。
- 能比较本次与基线版本的指标变化。

### 4) Safety & Policy

目标：防止越权、注入、敏感信息泄漏。

交付项：

- 工具入参注入模式检测（如“忽略之前指令/泄露系统提示词”）。
- 工具白名单和最小权限策略。
- 日志敏感字段脱敏策略与错误审计字段标准化。

验收标准：

- 注入样例会被拦截，并返回安全错误码。
- 审计日志里不会出现明文 secret/token。

### 5) Recovery & Degradation

目标：失败可恢复，不因单点失败导致整轮不可用。

交付项：

- 按错误码的降级策略（超时 -> 使用缓存/模板建议；源失败 -> 返回可执行替代方案）。
- 多源 fallback（主源失败自动切备源）。
- 用户可感知的失败说明（包含建议下一步）。

验收标准：

- 外部源不可用时，Agent 仍返回可执行答复，不是空响应。
- 错误码与降级路径可在执行统计中追踪。

## Milestone Plan (4 Weeks)

1. Week 1: Tool Governance + Safety 基线落地（参数校验、脱敏、注入拦截、执行汇总）。
2. Week 2: 外部数据源适配层与来源/时效字段统一。
3. Week 3: 评测集与评测脚本，接入 CI 报告。
4. Week 4: 多源降级与失败恢复策略打通，补齐集成测试。

## This Iteration (Already Started)

本轮已实现（代码已落地）：

- 工具调用前参数校验。
- 入参安全模式拦截。
- 调用参数日志脱敏与超长截断。
- `execution_summary` 聚合指标输出。
- 工具结果统一补充 `source/fetched_at/ttl_seconds` 元数据。
- 工具失败时产出 `fallback_suggestion` 降级建议。
- `get_weather` 已接入 provider 元数据透传（`travel_api -> travel_tools -> graph`）。
- `query_attractions` 与 `query_hotels` 已接入 provider 元数据透传。
- `get_weather` 已支持 primary/fallback provider 自动切换，并输出 `fallback_used` 元数据。
- `query_attractions` 与 `query_hotels` 已支持 primary/fallback provider 自动切换。
- `search_cities` 已支持 primary/fallback provider 自动切换并透传 `_meta`。
- `execution_summary` 已新增 `fallback_steps` 指标用于统计备源切换次数。
