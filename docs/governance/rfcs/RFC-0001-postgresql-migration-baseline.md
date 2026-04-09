# RFC-0001 PostgreSQL Migration Baseline

## Status

Status: draft

## Problem

- 当前持久化能力由 `sessions.json`、`share_links.json`、`agent_memory.json` 和 `langgraph_checkpoints.sqlite3` 组成。
- 这套方案适合单机开发和本地演示，但不适合多实例、长期演进和正式数据库治理。
- 当前还没有 schema version、migration、backfill、数据库回滚和环境切换基线。

## Proposal

- 引入 PostgreSQL 作为后续主持久化方向，优先承接：
  - session 元信息
  - session messages
  - share links
  - 可独立查询的 memory session 摘要
- Phase 1 暂不强行迁移 LangGraph checkpoint。
  - checkpoint 先继续保留现有 SQLite 实现
  - 等 session/message/share 主路径稳定后，再决定 checkpoint 是否单独迁移
- 引入显式 migration 基线：
  - `alembic` 管理 schema version
  - `psycopg` 或同级 PostgreSQL driver
  - SQLAlchemy 2.x 作为 migration 和 repository 映射层
- 数据模型基线建议：
  - `sessions`
  - `session_messages`
  - `share_links`
  - `memory_sessions`
  - `schema_migrations` 由 migration 工具维护
- 关键字段建议：
  - `sessions.id / created_at / last_active_at / name / model_id`
  - `session_messages.session_id / role / content / diagnostics_json / created_at / sequence`
  - `share_links.share_id / title / content / html_content / delivery_bundle_json / created_at`
  - `memory_sessions.session_id / summary / profile_json / updated_at`
- 索引基线建议：
  - `sessions(last_active_at desc)`
  - `session_messages(session_id, sequence)`
  - `share_links(created_at desc)`
- 配置基线建议：
  - `MOYUAN_DB_BACKEND=file|postgres`
  - `MOYUAN_POSTGRES_DSN`
  - `MOYUAN_DB_POOL_MIN`
  - `MOYUAN_DB_POOL_MAX`
- 切换策略建议：
  - 先保留 file backend
  - 新增 postgres backend
  - 提供一次性 import/backfill 脚本
  - 通过环境变量切换默认 repository 实现

## Rollout

1. 先补文档、依赖和 migration 空骨架。
2. 定义 PostgreSQL repository interface 和首版 schema。
3. 提供从 `sessions.json / share_links.json` 导入 PostgreSQL 的脚本。
4. 先让开发环境可选切换到 PostgreSQL。
5. 补针对 PostgreSQL repository 的 unit/integration 测试。
6. 再决定是否迁移 checkpoint。

验证计划：

- migration 可从空库成功初始化
- import/backfill 可重复执行且不会产生脏重复
- `session / message / share` 查询结果与 file backend 一致
- 回滚时可退回 file backend

回退方案：

- PostgreSQL backend 不稳定时，直接切回 `MOYUAN_DB_BACKEND=file`
- 在正式切换前保留 runtime backup 和导入前快照

## Risks

- 引入 SQLAlchemy/Alembic 会增加新的依赖和维护面。
- `session + memory + checkpoint` 仍然可能在过渡阶段存在双轨状态。
- 如果过早迁移 checkpoint，复杂度会显著上升。
- 需要明确哪些 JSON 字段保留为 `jsonb`，哪些应拆成结构化列。
- 需要决定是否在 Phase 1 同时处理分布式限流与缓存。
