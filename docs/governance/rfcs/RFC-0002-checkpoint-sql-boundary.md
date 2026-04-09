# RFC-0002 Checkpoint SQL Boundary

## Status

Status: draft

## Problem

- 当前 LangGraph checkpoint 仍由 [`PersistentSqliteSaver`](../../../agent/travel_agent/graph/persistent_checkpointer.py) 直接写 `data/langgraph_checkpoints.sqlite3`。
- `session / session_messages / share_links / memory_sessions` 已开始进入 PostgreSQL 基线，但 checkpoint 还停留在本地 SQLite。
- 如果后续直接把 checkpoint 和业务表混在一起改，容易把“会话事实数据”和“运行态恢复数据”揉成一类，导致治理边界失控。
- 当前还没有明确：
  - checkpoint SQL 化后由谁创建 backend
  - 是否和业务表共 schema
  - 哪些 payload 继续保持 blob/json，哪些才值得结构化
  - replay / recovery / compaction / retention 应该由哪一层负责

## Proposal

- 明确 checkpoint 的 SQL 化边界：它是“运行态恢复存储”，不是“业务查询存储”。
- 继续保持三类数据分层：
  - `session / session_messages`
    - 面向 API、会话历史、审计和长期业务查询
  - `memory_sessions`
    - 面向长期偏好、摘要和跨轮上下文注入
  - `checkpoints`
    - 面向 LangGraph 执行恢复、失败回放、debug 和 compaction
- checkpoint SQL 化时不直接并入当前 `sessions` 读路径。
  - API 查询仍以 `session_messages` 和 `memory_sessions` 为准
  - checkpoint 不作为前端/接口读取主数据源
- backend seam 固定收口在 [`create_default_checkpointer`](../../../agent/travel_agent/runtime_sources.py)。
  - 后续只允许在这个 adapter 层决定 `sqlite | postgres`
  - 不让 route / service / repository 直接依赖 checkpoint backend 细节
- PostgreSQL 目标表建议保持专用 checkpoint 命名空间，避免和业务表混用治理语义。
  - 建议表：
    - `agent_checkpoints`
    - `agent_checkpoint_blobs`
    - `agent_checkpoint_writes`
    - `agent_checkpoint_meta`
- Phase 2 初期不追求把 checkpoint 全量结构化。
  - `payload` 先保持 blob/json 风格
  - 优先保留当前 `(thread_id, checkpoint_ns, checkpoint_id)` 主键边界
  - 先解决多实例共享、恢复、回放和 compaction 一致性
- 建议新增独立配置开关，但在正式实现前不提前启用：
  - `AGENT_CHECKPOINT_BACKEND=sqlite|postgres`
  - `AGENT_CHECKPOINT_DSN`
  - `AGENT_CHECKPOINT_MAX_PER_THREAD`
  - `AGENT_CHECKPOINT_COMPACTION_INTERVAL`
- compaction / retention 规则继续由 checkpoint backend 自己负责，不下沉到业务 repository。

## Rollout

1. 先把当前 SQLite saver 的边界固定在 `runtime_sources.create_default_checkpointer()`。
2. 增加 checkpoint backend 抽象，不改现有 replay / runtime 调用面。
3. 新增 PostgreSQL checkpoint saver，表结构先对齐当前 SQLite 四表语义。
4. 先在开发环境支持 `sqlite|postgres` 切换，不默认启用 postgres。
5. replay、recovery、compaction、count 相关测试同时覆盖两种 backend。
6. 只有当 PostgreSQL saver 在多实例/多进程场景稳定后，才考虑把默认 backend 从 sqlite 切到 postgres。

验证计划：

- 同一 `thread_id + checkpoint_ns` 下的 checkpoint 顺序与当前 SQLite 行为一致
- `agent_replay.py` 在 sqlite/postgres backend 下输出一致的 source snapshot
- compaction 后最近 N 个 checkpoint 保留行为一致
- backend 切回 sqlite 时不影响 `session / memory / share` 主路径

回退方案：

- 如果 PostgreSQL checkpoint saver 不稳定，直接切回 `AGENT_CHECKPOINT_BACKEND=sqlite`
- 在切换默认 backend 前保留 `langgraph_checkpoints.sqlite3` 备份与 replay 工具链

## Risks

- checkpoint payload 目前依赖 pickled state，跨版本兼容性天然比业务 JSON 模型差。
- 如果把 checkpoint 过早当作“业务数据源”使用，会重新制造 session/memory/checkpoint 边界混乱。
- PostgreSQL saver 一旦实现不当，可能引入 compaction 锁竞争和高频写放大。
- 多实例共享 checkpoint 后，需要额外校验 thread namespace 隔离、清理策略和回放权限边界。
